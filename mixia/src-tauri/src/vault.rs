use std::collections::HashSet;
use std::ffi::OsStr;
use std::fs::{self, File};
use std::io::{BufReader, BufWriter, Cursor, Write};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use base64::{engine::general_purpose::STANDARD as B64, Engine};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use zeroize::Zeroizing;

use crate::crypto::{self, KEY_LEN};
use crate::error::{VaultError, VaultResult};

const HEADER_FILE: &str = "vault.json";
const INDEX_FILE: &str = "index.enc";
const BLOBS_DIR: &str = "blobs";
const THUMBS_DIR: &str = "thumbs";

/// 保险库在根目录下自己写出来的条目。
pub const INTERNAL_ENTRIES: &[&str] = &[HEADER_FILE, INDEX_FILE, BLOBS_DIR, THUMBS_DIR];

/// 判断一个候选源文件是不是保险库自己写出来的东西。
///
/// 只按根目录下的第一层名字匹配，因此把库建在照片文件夹里时，用户自己的
/// 照片仍然可以正常导入；被排除的只有 `vault.json`、`index.enc`、`blobs/`、
/// `thumbs/` —— 那些是密文，再加密一层只会得到无法使用的套娃。
pub fn is_internal_path(vault_root: &Path, path: &Path) -> bool {
    let Ok(rel) = path.strip_prefix(vault_root) else {
        return false;
    };
    let Some(first) = rel.components().next() else {
        // rel 为空：path 就是保险库根目录本身，它的内容按各自路径单独判断
        return false;
    };
    INTERNAL_ENTRIES
        .iter()
        .any(|name| first.as_os_str() == OsStr::new(name))
}

const HEADER_MAGIC: &str = "MIXIA01";
const INDEX_MAGIC: &[u8; 8] = b"MIXIDX01";
const FORMAT_VERSION: u32 = 1;
const MK_AAD: &[u8] = b"mixia-mk-v1";
const INDEX_AAD: &[u8] = b"mixia-index-v1";
const MIN_PASSWORD_CHARS: usize = 8;
const THUMB_SOURCE_LIMIT: u64 = 40 * 1024 * 1024;

pub const KDF_M_COST: u32 = 65_536;
pub const KDF_T_COST: u32 = 3;
pub const KDF_P_COST: u32 = 4;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VaultHeader {
    pub magic: String,
    pub version: u32,
    pub created_at: u64,
    pub kdf: KdfParams,
    pub wrap: Sealed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KdfParams {
    pub name: String,
    pub m_cost: u32,
    pub t_cost: u32,
    pub p_cost: u32,
    pub salt: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Sealed {
    pub data: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Item {
    pub id: String,
    pub name: String,
    /// 导入时的相对路径（`/` 分隔，含文件名）。旧库没有这个字段，读出为 None。
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub path: Option<String>,
    pub size: u64,
    pub mime: String,
    pub kind: String,
    pub added_at: u64,
    pub chunks: u32,
    pub has_thumb: bool,
    pub key: Sealed,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Manifest {
    pub version: u32,
    pub items: Vec<Item>,
}

impl Default for Manifest {
    fn default() -> Self {
        Self {
            version: FORMAT_VERSION,
            items: Vec::new(),
        }
    }
}

pub struct Vault {
    pub path: PathBuf,
    pub header: VaultHeader,
    mk: Zeroizing<[u8; KEY_LEN]>,
    pub manifest: Manifest,
}

#[derive(Debug)]
pub struct VerifyIssue {
    pub id: String,
    pub name: String,
    pub reason: String,
}

impl Vault {
    pub fn create(dir: &Path, password: &str) -> VaultResult<Self> {
        validate_password(password)?;
        if dir.exists() && !dir.is_dir() {
            return Err(VaultError::InvalidInput("所选路径不是文件夹".into()));
        }
        fs::create_dir_all(dir)?;
        if dir.join(HEADER_FILE).exists() {
            return Err(VaultError::AlreadyExists);
        }
        fs::create_dir_all(dir.join(BLOBS_DIR))?;
        fs::create_dir_all(dir.join(THUMBS_DIR))?;

        let salt = crypto::random_array::<16>();
        let kek = crypto::derive_kek(password, &salt, KDF_M_COST, KDF_T_COST, KDF_P_COST)?;
        let mk = Zeroizing::new(crypto::random_array::<KEY_LEN>());
        let wrapped = crypto::seal(&*kek, &*mk, MK_AAD)?;

        let header = VaultHeader {
            magic: HEADER_MAGIC.to_string(),
            version: FORMAT_VERSION,
            created_at: now(),
            kdf: KdfParams {
                name: "argon2id".to_string(),
                m_cost: KDF_M_COST,
                t_cost: KDF_T_COST,
                p_cost: KDF_P_COST,
                salt: encode_b64(&salt),
            },
            wrap: Sealed {
                data: encode_b64(&wrapped),
            },
        };

        let vault = Self {
            path: dir.to_path_buf(),
            header,
            mk,
            manifest: Manifest::default(),
        };

        // 先写索引再写头部：中途失败时不会留下一个“存在但打不开”的保险库
        vault.save_index()?;
        vault.write_header()?;
        Ok(vault)
    }

    pub fn open(dir: &Path, password: &str) -> VaultResult<Self> {
        let header = Self::inspect(dir)?;
        if header.kdf.name != "argon2id" {
            return Err(VaultError::Invalid(format!(
                "不支持的密钥派生算法：{}",
                header.kdf.name
            )));
        }
        let salt = decode_b64(&header.kdf.salt)?;
        let wrapped = decode_b64(&header.wrap.data)?;
        let kek = crypto::derive_kek(
            password,
            &salt,
            header.kdf.m_cost,
            header.kdf.t_cost,
            header.kdf.p_cost,
        )?;
        let mk_bytes = crypto::open(&*kek, &wrapped, MK_AAD).map_err(|_| VaultError::BadPassword)?;
        if mk_bytes.len() != KEY_LEN {
            return Err(VaultError::Invalid("主密钥长度异常".into()));
        }
        let mut mk = Zeroizing::new([0u8; KEY_LEN]);
        mk.copy_from_slice(&mk_bytes);

        let manifest = read_index(dir, &mk)?;
        Ok(Self {
            path: dir.to_path_buf(),
            header,
            mk,
            manifest,
        })
    }

    pub fn inspect(dir: &Path) -> VaultResult<VaultHeader> {
        let raw = fs::read(dir.join(HEADER_FILE)).map_err(|e| match e.kind() {
            std::io::ErrorKind::NotFound => {
                VaultError::Invalid("该文件夹中没有保险库".to_string())
            }
            _ => VaultError::Io(e),
        })?;
        let header: VaultHeader = serde_json::from_slice(&raw)
            .map_err(|e| VaultError::Invalid(format!("保险库头部无法解析：{e}")))?;
        if header.magic != HEADER_MAGIC {
            return Err(VaultError::Invalid("不是秘匣保险库".into()));
        }
        if header.version != FORMAT_VERSION {
            return Err(VaultError::Invalid(format!(
                "不支持的保险库版本：{}",
                header.version
            )));
        }
        Ok(header)
    }

    pub fn save_index(&self) -> VaultResult<()> {
        let json = Zeroizing::new(serde_json::to_vec(&self.manifest)?);
        let sealed = crypto::seal(&*self.mk, &json, INDEX_AAD)?;
        let mut data = Vec::with_capacity(INDEX_MAGIC.len() + sealed.len());
        data.extend_from_slice(INDEX_MAGIC);
        data.extend_from_slice(&sealed);
        write_atomic(&self.path.join(INDEX_FILE), &data)
    }

    pub fn import_file(&mut self, src: &Path) -> VaultResult<Item> {
        self.import_file_with_rel(src, None)
    }

    /// `rel` 是导入时相对所选根目录的路径，用于在库里还原文件夹结构。
    /// 传 None 时退化成只用文件名；不可信的 rel（含 `..`、绝对路径等）同样退化。
    pub fn import_file_with_rel(&mut self, src: &Path, rel: Option<&str>) -> VaultResult<Item> {
        let meta = fs::metadata(src)?;
        if !meta.is_file() {
            return Err(VaultError::InvalidInput("只能导入文件".into()));
        }
        let name = src
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .filter(|n| !n.is_empty())
            .ok_or_else(|| VaultError::InvalidInput("文件名无法识别".into()))?;
        let path = rel
            .and_then(sanitize_rel)
            .filter(|rel_path| rel_path != &name);
        let ext = src
            .extension()
            .map(|e| e.to_string_lossy().to_ascii_lowercase())
            .unwrap_or_default();
        let mime = mime_guess::from_path(src)
            .first_or_octet_stream()
            .essence_str()
            .to_string();
        let kind = classify(&mime, &ext).to_string();

        let id = Uuid::new_v4().to_string();
        let file_key = Zeroizing::new(crypto::random_array::<KEY_LEN>());
        let wrapped = crypto::seal(&*self.mk, &*file_key, &crypto::key_aad(&id))?;
        let blob_aad = crypto::item_aad(&id, "blob");

        let blob_path = self.blob_path(&id);
        let tmp_path = self.blobs_dir().join(format!(".{id}.part"));
        let encrypted = (|| -> VaultResult<(u64, u32)> {
            let reader = BufReader::with_capacity(256 * 1024, File::open(src)?);
            let file = File::create(&tmp_path)?;
            let mut writer = BufWriter::with_capacity(256 * 1024, file);
            let result = crypto::encrypt_blob(reader, &mut writer, &*file_key, &blob_aad)?;
            writer.flush()?;
            let file = writer.into_inner().map_err(|e| {
                std::io::Error::new(std::io::ErrorKind::Other, e.to_string())
            })?;
            file.sync_all()?;
            Ok(result)
        })();

        let (size, chunks) = match encrypted {
            Ok(value) => value,
            Err(e) => {
                let _ = fs::remove_file(&tmp_path);
                return Err(e);
            }
        };
        if let Err(e) = fs::rename(&tmp_path, &blob_path) {
            let _ = fs::remove_file(&tmp_path);
            return Err(e.into());
        }

        let mut has_thumb = false;
        if kind == "image" && size <= THUMB_SOURCE_LIMIT {
            if let Ok(thumb) = make_thumbnail(src) {
                let sealed = crypto::seal(&*self.mk, &thumb, &crypto::thumb_aad(&id))?;
                if write_atomic(&self.thumb_path(&id), &sealed).is_ok() {
                    has_thumb = true;
                }
            }
        }

        let item = Item {
            id,
            name,
            path,
            size,
            mime,
            kind,
            added_at: now(),
            chunks,
            has_thumb,
            key: Sealed {
                data: encode_b64(&wrapped),
            },
        };
        self.manifest.items.push(item.clone());
        Ok(item)
    }

    pub fn export_to(&self, id: &str, dest: &Path) -> VaultResult<()> {
        let item = self.find(id)?.clone();
        let file_key = self.unwrap_key(&item)?;
        let parent = dest
            .parent()
            .filter(|p| !p.as_os_str().is_empty())
            .unwrap_or_else(|| Path::new("."));
        let tmp = parent.join(format!(".mixia-{}.part", short_id(&item.id)));

        let decrypted = (|| -> VaultResult<u64> {
            let reader = BufReader::with_capacity(256 * 1024, File::open(self.blob_path(id))?);
            let file = File::create(&tmp)?;
            let mut writer = BufWriter::with_capacity(256 * 1024, file);
            let total = crypto::decrypt_blob(
                reader,
                &mut writer,
                &*file_key,
                &crypto::item_aad(id, "blob"),
                item.chunks,
            )?;
            writer.flush()?;
            let file = writer.into_inner().map_err(|e| {
                std::io::Error::new(std::io::ErrorKind::Other, e.to_string())
            })?;
            file.sync_all()?;
            Ok(total)
        })();

        let total = match decrypted {
            Ok(value) => value,
            Err(e) => {
                let _ = fs::remove_file(&tmp);
                return Err(e);
            }
        };
        if total != item.size {
            let _ = fs::remove_file(&tmp);
            return Err(VaultError::Invalid("解密后的大小与索引不一致".into()));
        }
        if let Err(e) = fs::rename(&tmp, dest) {
            let _ = fs::remove_file(&tmp);
            return Err(e.into());
        }
        Ok(())
    }

    pub fn decrypt_to_temp(&self, id: &str, temp_dir: &Path) -> VaultResult<PathBuf> {
        let item = self.find(id)?.clone();
        fs::create_dir_all(temp_dir)?;
        let dest = temp_dir.join(format!(
            "{}-{}",
            short_id(&item.id),
            sanitize_filename(&item.name)
        ));
        if dest.exists() {
            let _ = fs::remove_file(&dest);
        }
        self.export_to(id, &dest)?;
        Ok(dest)
    }

    pub fn thumb(&self, id: &str) -> VaultResult<Option<Vec<u8>>> {
        let item = self.find(id)?;
        if !item.has_thumb {
            return Ok(None);
        }
        let raw = match fs::read(self.thumb_path(id)) {
            Ok(data) => data,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
            Err(e) => return Err(e.into()),
        };
        let plain = crypto::open(&*self.mk, &raw, &crypto::thumb_aad(id))
            .map_err(|_| VaultError::Invalid("缩略图校验失败".into()))?;
        Ok(Some(plain.to_vec()))
    }

    pub fn delete(&mut self, id: &str) -> VaultResult<()> {
        let before = self.manifest.items.len();
        self.manifest.items.retain(|item| item.id != id);
        if self.manifest.items.len() == before {
            return Err(VaultError::ItemNotFound);
        }
        let _ = fs::remove_file(self.blob_path(id));
        let _ = fs::remove_file(self.thumb_path(id));
        Ok(())
    }

    pub fn rename(&mut self, id: &str, new_name: &str) -> VaultResult<()> {
        let name = new_name.trim();
        if name.is_empty() {
            return Err(VaultError::InvalidInput("名称不能为空".into()));
        }
        if name.chars().count() > 200 {
            return Err(VaultError::InvalidInput("名称过长".into()));
        }
        if name == "." || name == ".." || name.contains('/') || name.contains('\\') {
            return Err(VaultError::InvalidInput("名称不能包含路径分隔符".into()));
        }
        if name.chars().any(|c| c.is_control()) {
            return Err(VaultError::InvalidInput("名称不能包含控制字符".into()));
        }
        let item = self
            .manifest
            .items
            .iter_mut()
            .find(|item| item.id == id)
            .ok_or(VaultError::ItemNotFound)?;
        item.name = name.to_string();
        if let Some(rel) = item.path.as_deref() {
            item.path = Some(match rel.rsplit_once('/') {
                Some((dir, _)) => format!("{dir}/{name}"),
                None => name.to_string(),
            });
        }
        Ok(())
    }

    pub fn change_password(&mut self, new_password: &str) -> VaultResult<()> {
        validate_password(new_password)?;
        let salt = crypto::random_array::<16>();
        let kek = crypto::derive_kek(
            new_password,
            &salt,
            self.header.kdf.m_cost,
            self.header.kdf.t_cost,
            self.header.kdf.p_cost,
        )?;
        let wrapped = crypto::seal(&*kek, &*self.mk, MK_AAD)?;
        self.header.kdf.salt = encode_b64(&salt);
        self.header.wrap = Sealed {
            data: encode_b64(&wrapped),
        };
        self.write_header()
    }

    pub fn item_name(&self, id: &str) -> VaultResult<String> {
        Ok(self.find(id)?.name.clone())
    }

    /// 导出时还原用的相对路径：优先用索引记录的 `path`，没有就退化成 `name`。
    /// 无论哪个来源都再过一遍清洗，绝不允许跳出导出目录。
    pub fn item_rel_path(item: &Item) -> PathBuf {
        item.path
            .as_deref()
            .and_then(sanitize_rel)
            .or_else(|| sanitize_rel(&item.name))
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from(sanitize_filename(&item.name)))
    }

    /// 逐个把密文块解密到空设备，校验认证标签与长度。不写出任何明文。
    pub fn verify(&self) -> Vec<VerifyIssue> {
        let mut issues = Vec::new();
        for item in &self.manifest.items {
            if let Err(err) = self.verify_item(item) {
                issues.push(VerifyIssue {
                    id: item.id.clone(),
                    name: item.name.clone(),
                    reason: err.to_string(),
                });
            }
        }
        issues
    }

    /// 校验单个条目：整条 blob 解密到空设备 + 长度比对 + 缩略图认证。不写出任何明文。
    pub fn verify_item(&self, item: &Item) -> VaultResult<()> {
        let file_key = self.unwrap_key(item)?;
        let reader = BufReader::with_capacity(256 * 1024, File::open(self.blob_path(&item.id))?);
        let total = crypto::decrypt_blob(
            reader,
            std::io::sink(),
            &*file_key,
            &crypto::item_aad(&item.id, "blob"),
            item.chunks,
        )?;
        if total != item.size {
            return Err(VaultError::Invalid("大小与索引不一致".into()));
        }
        if !item.has_thumb {
            return Ok(());
        }
        let raw = fs::read(self.thumb_path(&item.id))?;
        crypto::open(&*self.mk, &raw, &crypto::thumb_aad(&item.id))
            .map(|_| ())
            .map_err(|_| VaultError::Invalid("缩略图校验失败".into()))
    }

    pub fn cleanup_orphans(&self) -> VaultResult<usize> {
        let ids: HashSet<&str> = self
            .manifest
            .items
            .iter()
            .map(|item| item.id.as_str())
            .collect();
        let mut removed = 0usize;

        for (dir, is_thumb) in [(self.blobs_dir(), false), (self.path.join(THUMBS_DIR), true)] {
            let Ok(entries) = fs::read_dir(&dir) else {
                continue;
            };
            for entry in entries.flatten() {
                let path = entry.path();
                let Some(name) = path.file_name().map(|n| n.to_string_lossy().into_owned())
                else {
                    continue;
                };
                if name.starts_with('.') && name.ends_with(".part") {
                    if fs::remove_file(&path).is_ok() {
                        removed += 1;
                    }
                    continue;
                }
                let Some(id) = name.strip_suffix(".bin") else {
                    continue;
                };
                let orphan = if is_thumb {
                    !self
                        .manifest
                        .items
                        .iter()
                        .any(|item| item.id == id && item.has_thumb)
                } else {
                    !ids.contains(id)
                };
                if orphan && fs::remove_file(&path).is_ok() {
                    removed += 1;
                }
            }
        }
        Ok(removed)
    }

    fn write_header(&self) -> VaultResult<()> {
        let data = serde_json::to_vec_pretty(&self.header)?;
        write_atomic(&self.path.join(HEADER_FILE), &data)
    }

    pub fn find(&self, id: &str) -> VaultResult<&Item> {
        self.manifest
            .items
            .iter()
            .find(|item| item.id == id)
            .ok_or(VaultError::ItemNotFound)
    }

    fn unwrap_key(&self, item: &Item) -> VaultResult<Zeroizing<[u8; KEY_LEN]>> {
        let sealed = decode_b64(&item.key.data)?;
        let raw = crypto::open(&*self.mk, &sealed, &crypto::key_aad(&item.id))?;
        if raw.len() != KEY_LEN {
            return Err(VaultError::Invalid("文件密钥长度异常".into()));
        }
        let mut key = Zeroizing::new([0u8; KEY_LEN]);
        key.copy_from_slice(&raw);
        Ok(key)
    }

    fn blobs_dir(&self) -> PathBuf {
        self.path.join(BLOBS_DIR)
    }

    fn blob_path(&self, id: &str) -> PathBuf {
        self.blobs_dir().join(format!("{id}.bin"))
    }

    fn thumb_path(&self, id: &str) -> PathBuf {
        self.path.join(THUMBS_DIR).join(format!("{id}.bin"))
    }
}

fn read_index(dir: &Path, mk: &[u8; KEY_LEN]) -> VaultResult<Manifest> {
    let raw = fs::read(dir.join(INDEX_FILE)).map_err(|e| match e.kind() {
        std::io::ErrorKind::NotFound => VaultError::Invalid("索引文件缺失".to_string()),
        _ => VaultError::Io(e),
    })?;
    if raw.len() < INDEX_MAGIC.len() || &raw[..INDEX_MAGIC.len()] != INDEX_MAGIC {
        return Err(VaultError::Invalid("索引文件头无效".into()));
    }
    let plain = crypto::open(mk, &raw[INDEX_MAGIC.len()..], INDEX_AAD)
        .map_err(|_| VaultError::Invalid("索引校验失败，保险库可能被篡改".into()))?;
    let manifest: Manifest = serde_json::from_slice(&plain)?;
    if manifest.version != FORMAT_VERSION {
        return Err(VaultError::Invalid("不支持的索引版本".into()));
    }
    Ok(manifest)
}

fn validate_password(password: &str) -> VaultResult<()> {
    if password.chars().count() < MIN_PASSWORD_CHARS {
        return Err(VaultError::InvalidInput(format!(
            "密码至少需要 {MIN_PASSWORD_CHARS} 位"
        )));
    }
    if password.chars().count() > 1024 {
        return Err(VaultError::InvalidInput("密码过长".into()));
    }
    Ok(())
}

fn classify(mime: &str, ext: &str) -> &'static str {
    const IMAGE_EXT: &[&str] = &[
        "jpg", "jpeg", "png", "gif", "webp", "bmp", "tif", "tiff", "heic", "heif", "avif", "svg",
    ];
    const VIDEO_EXT: &[&str] = &[
        "mp4", "mkv", "mov", "avi", "webm", "m4v", "wmv", "flv", "mpg", "mpeg", "ts", "3gp",
    ];
    const AUDIO_EXT: &[&str] = &[
        "mp3", "flac", "wav", "aac", "m4a", "ogg", "opus", "wma",
    ];
    const DOC_EXT: &[&str] = &[
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "md", "rtf", "odt", "ods",
        "odp", "csv", "epub", "html", "htm", "json", "xml", "yaml", "yml",
    ];

    if mime.starts_with("image/") || IMAGE_EXT.contains(&ext) {
        "image"
    } else if mime.starts_with("video/") || VIDEO_EXT.contains(&ext) {
        "video"
    } else if mime.starts_with("audio/") || AUDIO_EXT.contains(&ext) {
        "audio"
    } else if DOC_EXT.contains(&ext) {
        "document"
    } else {
        "other"
    }
}

fn make_thumbnail(path: &Path) -> VaultResult<Vec<u8>> {
    let reader = image::ImageReader::open(path)
        .map_err(VaultError::Io)?
        .with_guessed_format()
        .map_err(VaultError::Io)?;
    let img = reader.decode().map_err(image_error)?;
    let thumb = img.thumbnail(480, 480).to_rgb8();
    let mut out = Vec::new();
    {
        let mut cursor = Cursor::new(&mut out);
        image::DynamicImage::ImageRgb8(thumb)
            .write_to(&mut cursor, image::ImageFormat::Jpeg)
            .map_err(image_error)?;
    }
    Ok(out)
}

fn image_error(err: image::ImageError) -> VaultError {
    VaultError::Invalid(format!("图片处理失败：{err}"))
}

/// 把导入时记录的相对路径清洗成「只能往下走」的形式。
/// 返回 None 表示这段路径不可信（绝对路径、盘符、UNC、`..`、空段、控制字符），
/// 调用方应当退化成只用文件名。
fn sanitize_rel(raw: &str) -> Option<String> {
    let unified = raw.replace('\\', "/");
    if unified.starts_with('/') || unified.contains(':') {
        return None;
    }
    let mut parts: Vec<&str> = Vec::new();
    for part in unified.split('/') {
        if part.is_empty() || part == "." || part == ".." {
            return None;
        }
        if part.chars().any(|c| c.is_control() || c == ':') {
            return None;
        }
        parts.push(part);
    }
    if parts.is_empty() {
        return None;
    }
    Some(parts.join("/"))
}

fn sanitize_filename(name: &str) -> String {
    let cleaned: String = name
        .chars()
        .map(|c| match c {
            '<' | '>' | ':' | '"' | '/' | '\\' | '|' | '?' | '*' => '_',
            c if c.is_control() => '_',
            c => c,
        })
        .collect();
    let trimmed = cleaned.trim().trim_matches('.').trim();
    if trimmed.is_empty() {
        "file".to_string()
    } else {
        trimmed.chars().take(120).collect()
    }
}

fn short_id(id: &str) -> &str {
    &id[..id.len().min(8)]
}

fn write_atomic(path: &Path, data: &[u8]) -> VaultResult<()> {
    let tmp = tmp_sibling(path);
    {
        let mut file = File::create(&tmp)?;
        file.write_all(data)?;
        file.sync_all()?;
    }
    if let Err(e) = fs::rename(&tmp, path) {
        let _ = fs::remove_file(&tmp);
        return Err(e.into());
    }
    Ok(())
}

fn tmp_sibling(path: &Path) -> PathBuf {
    let name = path
        .file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or_else(|| "tmp".to_string());
    path.with_file_name(format!(".{name}.tmp"))
}

fn encode_b64(data: &[u8]) -> String {
    B64.encode(data)
}

fn decode_b64(data: &str) -> VaultResult<Vec<u8>> {
    B64.decode(data)
        .map_err(|e| VaultError::Invalid(format!("Base64 解析失败：{e}")))
}

fn now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn sample_file(dir: &Path, name: &str, size: usize) -> PathBuf {
        let path = dir.join(name);
        let data: Vec<u8> = (0..size).map(|i| (i % 251) as u8).collect();
        fs::write(&path, data).unwrap();
        path
    }

    #[test]
    fn roundtrip_import_export_and_wrong_password() {
        let tmp = TempDir::new().unwrap();
        let vault_dir = tmp.path().join("vault");
        let mut vault = Vault::create(&vault_dir, "correct horse battery").unwrap();

        let src = sample_file(tmp.path(), "photo.bin", crypto::CHUNK_SIZE * 2 + 123);
        let item = vault.import_file(&src).unwrap();
        assert_eq!(item.size, (crypto::CHUNK_SIZE * 2 + 123) as u64);
        vault.save_index().unwrap();

        let dest = tmp.path().join("out.bin");
        vault.export_to(&item.id, &dest).unwrap();
        assert_eq!(fs::read(&src).unwrap(), fs::read(&dest).unwrap());

        drop(vault);
        assert!(Vault::open(&vault_dir, "wrong password").is_err());

        let reopened = Vault::open(&vault_dir, "correct horse battery").unwrap();
        assert_eq!(reopened.manifest.items.len(), 1);
        assert_eq!(reopened.manifest.items[0].name, "photo.bin");
    }

    #[test]
    fn empty_and_exact_multiple_files() {
        let tmp = TempDir::new().unwrap();
        let vault_dir = tmp.path().join("vault");
        let mut vault = Vault::create(&vault_dir, "passphrase 123").unwrap();

        let empty = sample_file(tmp.path(), "empty.bin", 0);
        let empty_item = vault.import_file(&empty).unwrap();
        assert_eq!(empty_item.chunks, 1);

        let exact = sample_file(tmp.path(), "exact.bin", crypto::CHUNK_SIZE * 2);
        let exact_item = vault.import_file(&exact).unwrap();
        assert_eq!(exact_item.chunks, 3);

        vault.save_index().unwrap();
        for (src, id) in [(empty, empty_item.id), (exact, exact_item.id)] {
            let dest = tmp.path().join(format!("{}.out", id));
            vault.export_to(&id, &dest).unwrap();
            assert_eq!(fs::read(&src).unwrap(), fs::read(&dest).unwrap());
        }
    }

    #[test]
    fn tampered_blob_is_rejected() {
        let tmp = TempDir::new().unwrap();
        let vault_dir = tmp.path().join("vault");
        let mut vault = Vault::create(&vault_dir, "passphrase 123").unwrap();
        let src = sample_file(tmp.path(), "doc.bin", 8192);
        let item = vault.import_file(&src).unwrap();
        vault.save_index().unwrap();

        let blob = vault_dir.join(BLOBS_DIR).join(format!("{}.bin", item.id));
        let mut bytes = fs::read(&blob).unwrap();
        let last = bytes.len() - 2;
        bytes[last] ^= 0x55;
        fs::write(&blob, bytes).unwrap();

        assert!(vault.export_to(&item.id, &tmp.path().join("bad.out")).is_err());
    }

    #[test]
    fn tampered_index_is_rejected() {
        let tmp = TempDir::new().unwrap();
        let vault_dir = tmp.path().join("vault");
        let vault = Vault::create(&vault_dir, "passphrase 123").unwrap();
        drop(vault);

        let index = vault_dir.join(INDEX_FILE);
        let mut bytes = fs::read(&index).unwrap();
        let last = bytes.len() - 1;
        bytes[last] ^= 0x01;
        fs::write(&index, bytes).unwrap();

        assert!(Vault::open(&vault_dir, "passphrase 123").is_err());
    }

    #[test]
    fn password_change_rewraps_key() {
        let tmp = TempDir::new().unwrap();
        let vault_dir = tmp.path().join("vault");
        let mut vault = Vault::create(&vault_dir, "old password 1").unwrap();
        let src = sample_file(tmp.path(), "note.txt", 4096);
        let item = vault.import_file(&src).unwrap();
        vault.save_index().unwrap();
        vault.change_password("new password 2").unwrap();
        drop(vault);

        assert!(Vault::open(&vault_dir, "old password 1").is_err());
        let reopened = Vault::open(&vault_dir, "new password 2").unwrap();
        let dest = tmp.path().join("note.out");
        reopened.export_to(&item.id, &dest).unwrap();
        assert_eq!(fs::read(&src).unwrap(), fs::read(&dest).unwrap());
    }

    fn sample_png(dir: &Path, name: &str) -> PathBuf {
        let path = dir.join(name);
        let img = image::RgbaImage::from_fn(320, 200, |x, y| {
            image::Rgba([(x % 256) as u8, (y % 256) as u8, 120, 255])
        });
        img.save(&path).unwrap();
        path
    }

    #[test]
    fn full_lifecycle_import_thumb_rename_delete_relock() {
        let tmp = TempDir::new().unwrap();
        let vault_dir = tmp.path().join("vault");
        let mut vault = Vault::create(&vault_dir, "lifecycle pass 1").unwrap();

        let png = sample_png(tmp.path(), "photo.png");
        let txt = sample_file(tmp.path(), "notes.txt", 1024);
        let video = sample_file(tmp.path(), "clip.mp4", crypto::CHUNK_SIZE + 777);

        let photo = vault.import_file(&png).unwrap();
        let note = vault.import_file(&txt).unwrap();
        let clip = vault.import_file(&video).unwrap();
        vault.save_index().unwrap();

        assert_eq!(photo.kind, "image");
        assert_eq!(clip.kind, "video");
        assert!(photo.has_thumb);
        let thumb = vault.thumb(&photo.id).unwrap().unwrap();
        assert_eq!(&thumb[..2], &[0xFF, 0xD8]);
        assert!(vault.thumb(&note.id).unwrap().is_none());
        assert!(vault.thumb(&clip.id).unwrap().is_none());

        vault.rename(&note.id, "已加密笔记.txt").unwrap();
        vault.save_index().unwrap();

        vault.delete(&clip.id).unwrap();
        vault.save_index().unwrap();
        assert!(!vault
            .blobs_dir()
            .join(format!("{}.bin", clip.id))
            .exists());
        assert_eq!(vault.cleanup_orphans().unwrap(), 0);

        let opened = vault
            .decrypt_to_temp(&photo.id, &tmp.path().join("open"))
            .unwrap();
        assert_eq!(fs::read(&opened).unwrap(), fs::read(&png).unwrap());

        drop(vault);
        let mut reopened = Vault::open(&vault_dir, "lifecycle pass 1").unwrap();
        assert_eq!(reopened.manifest.items.len(), 2);
        assert_eq!(reopened.item_name(&note.id).unwrap(), "已加密笔记.txt");
        reopened.delete(&photo.id).unwrap();
        reopened.save_index().unwrap();
        assert_eq!(reopened.cleanup_orphans().unwrap(), 0);
        assert!(!vault_dir.join(THUMBS_DIR).join(format!("{}.bin", photo.id)).exists());
    }

    #[test]
    fn verify_flags_tampered_blob() {
        let tmp = TempDir::new().unwrap();
        let vault_dir = tmp.path().join("vault");
        let mut vault = Vault::create(&vault_dir, "passphrase 123").unwrap();
        let a = vault.import_file(&sample_file(tmp.path(), "a.bin", 4096)).unwrap();
        let b = vault.import_file(&sample_file(tmp.path(), "b.bin", 8192)).unwrap();
        vault.save_index().unwrap();
        assert!(vault.verify().is_empty());

        let blob = vault_dir.join(BLOBS_DIR).join(format!("{}.bin", b.id));
        let mut bytes = fs::read(&blob).unwrap();
        let last = bytes.len() - 3;
        bytes[last] ^= 0xA5;
        fs::write(&blob, bytes).unwrap();

        let issues = vault.verify();
        assert_eq!(issues.len(), 1);
        assert_eq!(issues[0].id, b.id);
        assert_eq!(issues[0].name, "b.bin");
        assert!(vault.item_name(&a.id).is_ok());
    }

    #[test]
    fn rename_rejects_path_traversal() {
        let tmp = TempDir::new().unwrap();
        let vault_dir = tmp.path().join("vault");
        let mut vault = Vault::create(&vault_dir, "passphrase 123").unwrap();
        let src = sample_file(tmp.path(), "a.txt", 10);
        let item = vault.import_file(&src).unwrap();

        assert!(vault.rename(&item.id, "../evil").is_err());
        assert!(vault.rename(&item.id, "good-name.txt").is_ok());
    }

    #[test]
    fn folder_import_rebuilds_the_tree_on_export() {
        let tmp = TempDir::new().unwrap();
        let vault_dir = tmp.path().join("vault");
        let mut vault = Vault::create(&vault_dir, "passphrase 123").unwrap();

        let deep = tmp.path().join("a").join("b").join("报告.pdf");
        fs::create_dir_all(deep.parent().unwrap()).unwrap();
        fs::write(&deep, b"pdf-bytes").unwrap();
        let flat = sample_file(tmp.path(), "根文件.txt", 7);

        let nested = vault
            .import_file_with_rel(&deep, Some("a/b/报告.pdf"))
            .unwrap();
        assert_eq!(nested.path.as_deref(), Some("a/b/报告.pdf"));
        assert_eq!(nested.name, "报告.pdf");

        let plain = vault.import_file_with_rel(&flat, Some("根文件.txt")).unwrap();
        assert_eq!(plain.path, None, "平铺导入不该多存一份和 name 重复的路径");

        vault.save_index().unwrap();
        let reopened = Vault::open(&vault_dir, "passphrase 123").unwrap();
        assert_eq!(
            reopened.manifest.items[0].path.as_deref(),
            Some("a/b/报告.pdf"),
            "相对路径要能穿过加密索引原样回来"
        );

        let out = tmp.path().join("out");
        for item in &reopened.manifest.items {
            let dest = out.join(Vault::item_rel_path(item));
            fs::create_dir_all(dest.parent().unwrap()).unwrap();
            reopened.export_to(&item.id, &dest).unwrap();
        }
        assert_eq!(fs::read(out.join("a/b/报告.pdf")).unwrap(), b"pdf-bytes");
        assert_eq!(fs::read(out.join("根文件.txt")).unwrap(), fs::read(&flat).unwrap());
    }

    #[test]
    fn hostile_relative_paths_degrade_to_filename() {
        let tmp = TempDir::new().unwrap();
        let vault_dir = tmp.path().join("vault");
        let mut vault = Vault::create(&vault_dir, "passphrase 123").unwrap();
        let src = sample_file(tmp.path(), "x.txt", 5);

        for hostile in [
            "../逃逸.txt",
            "/etc/passwd",
            "C:\\Windows\\evil.txt",
            "\\\\nas\\share\\x.txt",
            "a/../../b.txt",
            "a//b.txt",
            "",
        ] {
            let item = vault.import_file_with_rel(&src, Some(hostile)).unwrap();
            assert_eq!(item.path, None, "{hostile} 不应被记录成路径");
            // 退化成文件名之后，导出时依然只会落在输出目录里
            assert_eq!(Vault::item_rel_path(&item), PathBuf::from("x.txt"));
        }
    }

    #[test]
    fn legacy_index_without_path_field_still_loads() {
        let legacy = r#"{
            "id":"11111111-1111-1111-1111-111111111111",
            "name":"旧条目.bin",
            "size":10,"mime":"application/octet-stream","kind":"document",
            "added_at":1,"chunks":1,"has_thumb":false,
            "key":{"data":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="}
        }"#;
        let item: Item = serde_json::from_str(legacy).unwrap();
        assert_eq!(item.path, None);
        assert_eq!(Vault::item_rel_path(&item), PathBuf::from("旧条目.bin"));
    }

    #[test]
    fn rename_updates_the_recorded_relative_path() {
        let tmp = TempDir::new().unwrap();
        let vault_dir = tmp.path().join("vault");
        let mut vault = Vault::create(&vault_dir, "passphrase 123").unwrap();
        let src = sample_file(tmp.path(), "x.txt", 5);
        let item = vault
            .import_file_with_rel(&src, Some("2016/手机/x.txt"))
            .unwrap();

        vault.rename(&item.id, "改名后.txt").unwrap();
        let renamed = vault.find(&item.id).unwrap();
        assert_eq!(renamed.name, "改名后.txt");
        assert_eq!(renamed.path.as_deref(), Some("2016/手机/改名后.txt"));
        assert_eq!(
            Vault::item_rel_path(renamed),
            PathBuf::from("2016/手机/改名后.txt")
        );
    }

    #[test]
    fn only_the_vaults_own_entries_are_internal() {
        let tmp = TempDir::new().unwrap();
        let vault_dir = tmp.path().join("vault");
        let mut vault = Vault::create(&vault_dir, "passphrase 123").unwrap();
        let src = sample_file(tmp.path(), "原件.txt", 5);
        let item = vault.import_file(&src).unwrap();
        vault.save_index().unwrap();

        // 库自己的四样东西不能当导入源
        assert!(is_internal_path(&vault_dir, &vault_dir.join(HEADER_FILE)));
        assert!(is_internal_path(&vault_dir, &vault_dir.join(INDEX_FILE)));
        assert!(is_internal_path(
            &vault_dir,
            &vault_dir.join(BLOBS_DIR).join(format!("{}.bin", item.id))
        ));
        assert!(is_internal_path(&vault_dir, &vault_dir.join(THUMBS_DIR)));

        // 把库建在照片文件夹里时，同一目录下的用户文件照常可以加密
        fs::write(vault_dir.join("IMG_0001.jpg"), b"photo").unwrap();
        fs::create_dir_all(vault_dir.join("2016")).unwrap();
        fs::write(vault_dir.join("2016").join("IMG_0002.jpg"), b"photo").unwrap();
        assert!(!is_internal_path(&vault_dir, &vault_dir.join("IMG_0001.jpg")));
        assert!(!is_internal_path(
            &vault_dir,
            &vault_dir.join("2016").join("IMG_0002.jpg")
        ));

        // 库外面、以及把库目录本身选作导入源，都不算内部条目
        assert!(!is_internal_path(&vault_dir, &src));
        assert!(!is_internal_path(&vault_dir, &vault_dir));
    }

    #[test]
    fn internal_check_survives_windows_canonical_paths() {
        // commands.rs 两边都喂 fs::canonicalize 的结果：Windows 下会带 `\\?\` 前缀，
        // 前缀必须在比较里也对得上，否则又会退化成静默跳过一切。
        let tmp = TempDir::new().unwrap();
        let vault_dir = tmp.path().join("新建文件夹 (2)");
        let mut vault = Vault::create(&vault_dir, "passphrase 123").unwrap();
        let src = sample_file(tmp.path(), "原件.txt", 5);
        let item = vault.import_file(&src).unwrap();
        vault.save_index().unwrap();

        let root = fs::canonicalize(&vault_dir).unwrap();
        let photo = root.join("IMG_0001.jpg");
        fs::write(&photo, b"photo").unwrap();
        let blob = fs::canonicalize(root.join(BLOBS_DIR).join(format!("{}.bin", item.id))).unwrap();

        assert!(!is_internal_path(&root, &fs::canonicalize(&photo).unwrap()));
        assert!(is_internal_path(&root, &blob));
        assert!(is_internal_path(
            &root,
            &fs::canonicalize(root.join(INDEX_FILE)).unwrap()
        ));
        assert!(!is_internal_path(&root, &fs::canonicalize(&src).unwrap()));
    }
}
