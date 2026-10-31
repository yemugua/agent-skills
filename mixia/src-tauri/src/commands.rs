use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::Ordering;

use base64::{engine::general_purpose::STANDARD as B64, Engine};
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, Manager};
use walkdir::WalkDir;

use mixia::error::{VaultError, VaultResult};
use mixia::vault::{is_internal_path, Item, Vault};

use crate::state::{AppState, Session};

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct VaultInfo {
    pub path: String,
    pub unlocked: bool,
    pub item_count: usize,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct AppStateDto {
    pub unlocked: bool,
    pub vault_path: Option<String>,
    pub last_vault: Option<String>,
    pub item_count: usize,
}

#[derive(Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct JobProgress {
    pub done: usize,
    pub total: usize,
    pub current: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ImportedSource {
    pub id: String,
    pub name: String,
    pub path: String,
    pub size: u64,
}

#[derive(Serialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct ImportSummary {
    pub imported: usize,
    pub total: usize,
    pub bytes: u64,
    pub cancelled: bool,
    pub failed: Vec<String>,
    pub sources: Vec<ImportedSource>,
    /// 一个文件都没能开始加密时，用来说清楚原因；正常导入和取消都是 None。
    pub note: Option<String>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ItemDto {
    pub id: String,
    pub name: String,
    /// 导入时的相对路径；平铺导入或旧库为 null。
    pub path: Option<String>,
    pub dir: String,
    pub size: u64,
    pub mime: String,
    pub kind: String,
    pub added_at: u64,
    pub has_thumb: bool,
    pub ext: String,
}

impl From<&Item> for ItemDto {
    fn from(item: &Item) -> Self {
        let ext = Path::new(&item.name)
            .extension()
            .map(|e| e.to_string_lossy().to_ascii_lowercase())
            .unwrap_or_default();
        let dir = item
            .path
            .as_deref()
            .and_then(|rel| rel.rsplit_once('/'))
            .map(|(dir, _)| dir.to_string())
            .unwrap_or_default();
        Self {
            id: item.id.clone(),
            name: item.name.clone(),
            path: item.path.clone(),
            dir,
            size: item.size,
            mime: item.mime.clone(),
            kind: item.kind.clone(),
            added_at: item.added_at,
            has_thumb: item.has_thumb,
            ext,
        }
    }
}

#[tauri::command]
pub fn get_state(app: AppHandle) -> AppStateDto {
    let config = load_config(&app);
    let last_vault = config
        .last_vault
        .filter(|path| Path::new(path).join("vault.json").is_file());
    let state = app.state::<AppState>();
    let guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
    AppStateDto {
        unlocked: guard.session.is_some(),
        vault_path: guard
            .vault_path
            .as_ref()
            .map(|path| path.display().to_string()),
        last_vault,
        item_count: guard
            .session
            .as_ref()
            .map(|session| session.vault.manifest.items.len())
            .unwrap_or(0),
    }
}

#[tauri::command]
pub async fn pick_folder(title: String) -> Result<Option<String>, String> {
    tauri::async_runtime::spawn_blocking(move || {
        rfd::FileDialog::new()
            .set_title(title)
            .pick_folder()
            .map(|path| path.display().to_string())
    })
    .await
    .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn create_vault(
    app: AppHandle,
    path: String,
    password: String,
) -> Result<VaultInfo, String> {
    tauri::async_runtime::spawn_blocking(move || create_vault_inner(&app, path, password))
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string())
}

fn create_vault_inner(app: &AppHandle, path: String, password: String) -> VaultResult<VaultInfo> {
    let dir = PathBuf::from(&path);
    let vault = Vault::create(&dir, &password)?;
    let item_count = vault.manifest.items.len();
    let session = Session::new(vault)?;

    let state = app.state::<AppState>();
    let mut guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
    guard.vault_path = Some(dir.clone());
    guard.session = Some(session);
    drop(guard);

    save_last_vault(app, &dir);
    Ok(VaultInfo {
        path: dir.display().to_string(),
        unlocked: true,
        item_count,
    })
}

#[tauri::command]
pub async fn open_vault(app: AppHandle, path: String) -> Result<VaultInfo, String> {
    tauri::async_runtime::spawn_blocking(move || open_vault_inner(&app, path))
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string())
}

fn open_vault_inner(app: &AppHandle, path: String) -> VaultResult<VaultInfo> {
    let dir = PathBuf::from(&path);
    Vault::inspect(&dir)?;

    let state = app.state::<AppState>();
    let mut guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
    if guard.vault_path.as_ref() != Some(&dir) {
        guard.session = None;
    }
    guard.vault_path = Some(dir.clone());
    drop(guard);

    save_last_vault(app, &dir);
    Ok(VaultInfo {
        path: dir.display().to_string(),
        unlocked: false,
        item_count: 0,
    })
}

#[tauri::command]
pub async fn unlock_vault(app: AppHandle, password: String) -> Result<VaultInfo, String> {
    tauri::async_runtime::spawn_blocking(move || unlock_vault_inner(&app, password))
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string())
}

fn unlock_vault_inner(app: &AppHandle, password: String) -> VaultResult<VaultInfo> {
    let path = {
        let state = app.state::<AppState>();
        let mut guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
        guard.session = None;
        guard
            .vault_path
            .clone()
            .ok_or_else(|| VaultError::InvalidInput("请先选择保险库".into()))?
    };

    let vault = Vault::open(&path, &password)?;
    let _ = vault.cleanup_orphans();
    let item_count = vault.manifest.items.len();
    let session = Session::new(vault)?;

    let state = app.state::<AppState>();
    let mut guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
    guard.session = Some(session);
    drop(guard);

    Ok(VaultInfo {
        path: path.display().to_string(),
        unlocked: true,
        item_count,
    })
}

#[tauri::command]
pub fn lock_vault(app: AppHandle) {
    let state = app.state::<AppState>();
    let mut guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
    guard.session = None;
}

#[tauri::command]
pub fn list_items(app: AppHandle) -> Result<Vec<ItemDto>, String> {
    list_items_inner(&app).map_err(|e| e.to_string())
}

fn list_items_inner(app: &AppHandle) -> VaultResult<Vec<ItemDto>> {
    let state = app.state::<AppState>();
    let guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
    let session = guard.session()?;
    let mut items: Vec<ItemDto> = session
        .vault
        .manifest
        .items
        .iter()
        .map(ItemDto::from)
        .collect();
    items.sort_by(|a, b| {
        b.added_at
            .cmp(&a.added_at)
            .then_with(|| a.name.cmp(&b.name))
    });
    Ok(items)
}

#[tauri::command]
pub fn get_thumb(app: AppHandle, id: String) -> Result<Option<String>, String> {
    let state = app.state::<AppState>();
    let guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
    let session = guard.session().map_err(|e| e.to_string())?;
    match session.vault.thumb(&id).map_err(|e| e.to_string())? {
        Some(bytes) => Ok(Some(B64.encode(bytes))),
        None => Ok(None),
    }
}

#[tauri::command]
pub async fn import_files(app: AppHandle) -> Result<ImportSummary, String> {
    tauri::async_runtime::spawn_blocking(move || import_files_inner(&app))
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string())
}

fn import_files_inner(app: &AppHandle) -> VaultResult<ImportSummary> {
    let picked = rfd::FileDialog::new()
        .set_title("选择要加密的文件")
        .pick_files();
    let Some(paths) = picked else {
        return Ok(empty_summary());
    };
    import_paths_inner(app, paths)
}

#[tauri::command]
pub async fn import_folder(app: AppHandle) -> Result<ImportSummary, String> {
    tauri::async_runtime::spawn_blocking(move || import_folder_inner(&app))
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string())
}

fn import_folder_inner(app: &AppHandle) -> VaultResult<ImportSummary> {
    let picked = rfd::FileDialog::new()
        .set_title("选择要加密的文件夹")
        .pick_folder();
    let Some(folder) = picked else {
        return Ok(empty_summary());
    };
    import_paths_inner(app, vec![folder])
}

#[tauri::command]
pub async fn import_paths(
    app: AppHandle,
    paths: Vec<String>,
) -> Result<ImportSummary, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let paths = paths.into_iter().map(PathBuf::from).collect();
        import_paths_inner(&app, paths)
    })
    .await
    .map_err(|e| e.to_string())?
    .map_err(|e| e.to_string())
}

fn import_paths_inner(app: &AppHandle, inputs: Vec<PathBuf>) -> VaultResult<ImportSummary> {
    let state = app.state::<AppState>();
    let vault_dir = {
        let guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
        guard.session()?.vault.path.clone()
    };

    let collected = collect_files(&inputs, &vault_dir);
    let files = collected.files;
    let total = files.len();
    if total == 0 {
        return Ok(if collected.internal > 0 {
            noop_summary(
                "选中的只有保险库自己的文件（blobs、index.enc 等），密文不能再加密一层。请改选原始的照片或文档。",
            )
        } else {
            noop_summary("没有可加密的文件：所选文件夹是空的，或者里面的文件已被移动、删除。")
        });
    }
    state.cancel.store(false, Ordering::Relaxed);

    emit_progress(app, "import-progress", 0, total, "");
    let mut guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
    let session = guard.session_mut()?;

    let mut sources: Vec<ImportedSource> = Vec::new();
    let mut failed: Vec<String> = Vec::new();
    let mut cancelled = false;
    for (index, file) in files.iter().enumerate() {
        // 取消只在整文件之间生效：已经写完的块都在同一个 blob 里，不会留下半个文件
        if state.cancel.load(Ordering::Relaxed) {
            cancelled = true;
            break;
        }
        let name = file.rel.rsplit('/').next().unwrap_or(&file.rel).to_string();
        emit_progress(app, "import-progress", index, total, &name);
        match session.vault.import_file_with_rel(&file.path, Some(&file.rel)) {
            Ok(item) => sources.push(ImportedSource {
                id: item.id.clone(),
                name: item.name.clone(),
                path: file.path.display().to_string(),
                size: item.size,
            }),
            Err(e) => failed.push(format!("{name}：{e}")),
        }
    }
    // 已导入的部分照常入索引；中断不会让索引和 blobs 对不上
    session.vault.save_index()?;
    emit_progress(app, "import-progress", sources.len() + failed.len(), total, "");
    drop(guard);

    let bytes = sources.iter().map(|source| source.size).sum();
    Ok(ImportSummary {
        imported: sources.len(),
        total,
        bytes,
        cancelled,
        failed,
        sources,
        note: None,
    })
}

#[tauri::command]
pub async fn export_item(app: AppHandle, id: String) -> Result<Option<String>, String> {
    tauri::async_runtime::spawn_blocking(move || export_item_inner(&app, &id))
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string())
}

fn export_item_inner(app: &AppHandle, id: &str) -> VaultResult<Option<String>> {
    let name = {
        let state = app.state::<AppState>();
        let guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
        guard.session()?.vault.item_name(id)?
    };
    let Some(dest) = rfd::FileDialog::new()
        .set_title("导出解密文件")
        .set_file_name(&name)
        .save_file()
    else {
        return Ok(None);
    };
    {
        let state = app.state::<AppState>();
        let guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
        guard.session()?.vault.export_to(id, &dest)?;
    }
    Ok(Some(dest.display().to_string()))
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ExportSummary {
    pub exported: usize,
    pub total: usize,
    pub bytes: u64,
    pub cancelled: bool,
    pub failed: Vec<String>,
}

/// 整库解出到某个目录，按导入时记录的相对路径还原目录树。
#[tauri::command]
pub async fn export_all(app: AppHandle, dest: String) -> Result<ExportSummary, String> {
    tauri::async_runtime::spawn_blocking(move || export_all_inner(&app, PathBuf::from(dest)))
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string())
}

fn export_all_inner(app: &AppHandle, dest: PathBuf) -> VaultResult<ExportSummary> {
    let state = app.state::<AppState>();
    state.cancel.store(false, Ordering::Relaxed);
    fs::create_dir_all(&dest)?;

    let guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
    let session = guard.session()?;
    let items = session.vault.manifest.items.clone();
    let total = items.len();

    let mut exported = 0usize;
    let mut bytes = 0u64;
    let mut failed: Vec<String> = Vec::new();
    for (index, item) in items.iter().enumerate() {
        if state.cancel.load(Ordering::Relaxed) {
            return Ok(ExportSummary {
                exported,
                total,
                bytes,
                cancelled: true,
                failed,
            });
        }
        emit_progress(app, "export-progress", index, total, &item.name);
        let target = dest.join(Vault::item_rel_path(item));
        if let Some(parent) = target.parent() {
            fs::create_dir_all(parent)?;
        }
        match session.vault.export_to(&item.id, &target) {
            Ok(()) => {
                exported += 1;
                bytes += item.size;
            }
            Err(e) => failed.push(format!("{}：{e}", item.name)),
        }
    }
    emit_progress(app, "export-progress", total, total, "");

    Ok(ExportSummary {
        exported,
        total,
        bytes,
        cancelled: false,
        failed,
    })
}

#[tauri::command]
pub fn cancel_operation(app: AppHandle) {
    app.state::<AppState>()
        .cancel
        .store(true, Ordering::Relaxed);
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DeleteReport {
    pub deleted: usize,
    pub bytes: u64,
    pub failed: Vec<String>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SourceRef {
    pub id: String,
    pub path: String,
}

/// 删掉刚导入的那批原件。**先逐个验密文，验不过的绝不删**；
/// 并且只删普通文件、绝不碰保险库自己写出来的条目、大小对不上的也不删。
#[tauri::command]
pub async fn delete_sources(
    app: AppHandle,
    sources: Vec<SourceRef>,
) -> Result<DeleteReport, String> {
    tauri::async_runtime::spawn_blocking(move || delete_sources_inner(&app, sources))
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string())
}

fn delete_sources_inner(app: &AppHandle, sources: Vec<SourceRef>) -> VaultResult<DeleteReport> {
    let state = app.state::<AppState>();
    let guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
    let session = guard.session()?;
    let vault_root = fs::canonicalize(&session.vault.path)
        .unwrap_or_else(|_| session.vault.path.clone());

    let mut deleted = 0usize;
    let mut bytes = 0u64;
    let mut failed: Vec<String> = Vec::new();

    for source in &sources {
        let item = match session.vault.find(&source.id) {
            Ok(item) => item,
            Err(e) => {
                failed.push(format!("{}：{e}", source.path));
                continue;
            }
        };
        if let Err(e) = session.vault.verify_item(item) {
            failed.push(format!("{}：密文未通过校验，不删原件（{e}）", source.path));
            continue;
        }
        let raw = PathBuf::from(&source.path);
        let path = match fs::canonicalize(&raw) {
            Ok(path) => path,
            Err(_) => {
                failed.push(format!("{}：原件已经不在这个位置了", source.path));
                continue;
            }
        };
        if is_internal_path(&vault_root, &path) {
            failed.push(format!("{}：是保险库自己的文件，拒绝删除", source.path));
            continue;
        }
        let meta = match fs::metadata(&path) {
            Ok(meta) if meta.is_file() => meta,
            _ => {
                failed.push(format!("{}：不是普通文件，拒绝删除", source.path));
                continue;
            }
        };
        if meta.len() != item.size {
            failed.push(format!(
                "{}：磁盘大小 {} 与库内记录 {} 不一致，拒绝删除",
                source.path,
                meta.len(),
                item.size
            ));
            continue;
        }
        match fs::remove_file(&path) {
            Ok(()) => {
                deleted += 1;
                bytes += item.size;
            }
            Err(e) => failed.push(format!("{}：{e}", source.path)),
        }
    }

    Ok(DeleteReport {
        deleted,
        bytes,
        failed,
    })
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct OriginalMatch {
    pub id: String,
    pub name: String,
    pub path: String,
    pub size: u64,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct OriginalScan {
    pub folder: String,
    pub scanned: usize,
    pub matched: Vec<OriginalMatch>,
    pub bytes: u64,
}

/// 在用户指定的文件夹里找出「已经安全躺在库里」的原件，用于随时随地的批量清理，
/// 不限于刚刚导入的那一批。
///
/// 匹配只看文件名与大小，真正的安全边界留给 `delete_sources`：逐个验证库内密文能解开、
/// 磁盘大小与记录一致、是普通文件、且不是保险库自己的条目，才敢删。
#[tauri::command]
pub async fn scan_originals(app: AppHandle, folder: String) -> Result<OriginalScan, String> {
    tauri::async_runtime::spawn_blocking(move || scan_originals_inner(&app, folder))
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string())
}

fn scan_originals_inner(app: &AppHandle, folder: String) -> VaultResult<OriginalScan> {
    let state = app.state::<AppState>();
    let (vault_root, records) = {
        let guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
        let session = guard.session()?;
        let root = fs::canonicalize(&session.vault.path)
            .unwrap_or_else(|_| session.vault.path.clone());
        // 只带走匹配需要的三样信息，扫描期间不占着锁
        let records: Vec<(String, u64, String)> = session
            .vault
            .manifest
            .items
            .iter()
            .map(|item| (item.name.to_ascii_lowercase(), item.size, item.id.clone()))
            .collect();
        (root, records)
    };

    let dir = fs::canonicalize(&folder).map_err(|_| {
        VaultError::InvalidInput("这个文件夹打不开，可能已经被移动或删除了".to_string())
    })?;

    let mut wanted: HashMap<(String, u64), String> = HashMap::new();
    for (name, size, id) in records {
        wanted.entry((name, size)).or_insert(id);
    }

    let mut scanned = 0usize;
    let mut matched: Vec<OriginalMatch> = Vec::new();
    let mut bytes = 0u64;
    for entry in WalkDir::new(&dir)
        .follow_links(false)
        .into_iter()
        .filter_map(|entry| entry.ok())
    {
        if !entry.file_type().is_file() {
            continue;
        }
        let path = entry.path();
        if is_internal_path(&vault_root, path) {
            continue;
        }
        let size = match fs::metadata(path) {
            Ok(meta) if meta.is_file() => meta.len(),
            _ => continue,
        };
        scanned += 1;
        let raw_name = path
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_default();
        if raw_name.is_empty() {
            continue;
        }
        if let Some(id) = wanted.get(&(raw_name.to_ascii_lowercase(), size)) {
            bytes += size;
            matched.push(OriginalMatch {
                id: id.clone(),
                name: raw_name,
                path: path.display().to_string(),
                size,
            });
        }
    }
    matched.sort_by(|a, b| a.path.cmp(&b.path));

    Ok(OriginalScan {
        folder: dir.display().to_string(),
        scanned,
        matched,
        bytes,
    })
}

#[tauri::command]
pub async fn open_item(app: AppHandle, id: String) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || open_item_inner(&app, &id))
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string())
}

fn open_item_inner(app: &AppHandle, id: &str) -> VaultResult<String> {
    let dest = {
        let state = app.state::<AppState>();
        let guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
        let session = guard.session()?;
        session.vault.decrypt_to_temp(id, &session.temp_dir)?
    };
    open::that(&dest).map_err(|e| VaultError::Invalid(format!("无法调用系统默认程序：{e}")))?;
    Ok(dest.display().to_string())
}

#[tauri::command]
pub async fn delete_item(app: AppHandle, id: String) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || delete_item_inner(&app, &id))
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string())
}

fn delete_item_inner(app: &AppHandle, id: &str) -> VaultResult<()> {
    let state = app.state::<AppState>();
    let mut guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
    let session = guard.session_mut()?;
    session.vault.delete(id)?;
    session.vault.save_index()
}

/// 批量删除的结果。`bytes` 是这些条目在库里记录的原始大小。
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BatchDeleteReport {
    pub deleted: usize,
    pub bytes: u64,
    pub failed: Vec<String>,
}

/// 一次删掉勾选的多个条目：清单在内存里改完，**索引只落盘一次**，
/// 几百个文件也不用一个一个确认。单个失败不影响其余，失败原因照常返回。
#[tauri::command]
pub async fn delete_items(app: AppHandle, ids: Vec<String>) -> Result<BatchDeleteReport, String> {
    tauri::async_runtime::spawn_blocking(move || delete_items_inner(&app, ids))
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string())
}

fn delete_items_inner(app: &AppHandle, ids: Vec<String>) -> VaultResult<BatchDeleteReport> {
    let state = app.state::<AppState>();
    let mut guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
    let session = guard.session_mut()?;

    let mut deleted = 0usize;
    let mut bytes = 0u64;
    let mut failed: Vec<String> = Vec::new();

    for id in &ids {
        let item = match session.vault.find(id) {
            Ok(item) => item,
            // 库里已经没有这个条目（比如刚在另一个窗口删掉了），跳过，不算失败
            Err(_) => continue,
        };
        let name = item.name.clone();
        let size = item.size;
        match session.vault.delete(id) {
            Ok(()) => {
                deleted += 1;
                bytes += size;
            }
            Err(e) => failed.push(format!("{}：{e}", name)),
        }
    }

    if deleted > 0 {
        session.vault.save_index()?;
    }

    Ok(BatchDeleteReport {
        deleted,
        bytes,
        failed,
    })
}

#[tauri::command]
pub async fn rename_item(app: AppHandle, id: String, name: String) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || rename_item_inner(&app, &id, &name))
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string())
}

fn rename_item_inner(app: &AppHandle, id: &str, name: &str) -> VaultResult<()> {
    let state = app.state::<AppState>();
    let mut guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
    let session = guard.session_mut()?;
    session.vault.rename(id, name)?;
    session.vault.save_index()
}

#[tauri::command]
pub async fn change_password(app: AppHandle, new_password: String) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || change_password_inner(&app, &new_password))
        .await
        .map_err(|e| e.to_string())?
        .map_err(|e| e.to_string())
}

fn change_password_inner(app: &AppHandle, new_password: &str) -> VaultResult<()> {
    let state = app.state::<AppState>();
    let mut guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
    let session = guard.session_mut()?;
    session.vault.change_password(new_password)
}

fn empty_summary() -> ImportSummary {
    ImportSummary::default()
}

/// 一个都没开始加密时用：`total` 仍是 0，但界面上要能说明为什么。
fn noop_summary(note: &str) -> ImportSummary {
    ImportSummary {
        note: Some(note.to_string()),
        ..ImportSummary::default()
    }
}

fn emit_progress(app: &AppHandle, event: &str, done: usize, total: usize, current: &str) {
    let _ = app.emit(
        event,
        JobProgress {
            done,
            total,
            current: current.to_string(),
        },
    );
}

/// 一个待导入候选：磁盘路径 + 相对所选根目录的路径（`/` 分隔）。
struct Candidate {
    path: PathBuf,
    rel: String,
}

/// 一次扫描的结果：可导入的候选，以及被排除的保险库自身条目数量。
struct Collected {
    files: Vec<Candidate>,
    internal: usize,
}

fn collect_files(inputs: &[PathBuf], vault_dir: &Path) -> Collected {
    let vault_root = fs::canonicalize(vault_dir).unwrap_or_else(|_| vault_dir.to_path_buf());
    let mut picked: HashSet<PathBuf> = HashSet::new();
    let mut files: Vec<Candidate> = Vec::new();
    let mut internal = 0usize;

    for input in inputs {
        if input.is_file() {
            let rel = input
                .file_name()
                .map(|n| n.to_string_lossy().into_owned())
                .unwrap_or_default();
            push_unique(
                input,
                &rel,
                &vault_root,
                &mut picked,
                &mut files,
                &mut internal,
            );
        } else if input.is_dir() {
            // 把所选目录自己的名字留作相对路径的第一段：这样导入一个文件夹，
            // 在库里就是「一个文件夹」，而不是散成一地看不出来源的文件
            let root_name = input
                .file_name()
                .map(|n| n.to_string_lossy().into_owned())
                .unwrap_or_default();
            for entry in WalkDir::new(input)
                .follow_links(false)
                .into_iter()
                .filter_map(|entry| entry.ok())
            {
                if !entry.file_type().is_file() {
                    continue;
                }
                let inner = entry
                    .path()
                    .strip_prefix(input)
                    .unwrap_or(entry.path())
                    .to_string_lossy()
                    .replace('\\', "/");
                let rel = if root_name.is_empty() {
                    inner
                } else {
                    format!("{root_name}/{inner}")
                };
                push_unique(
                    entry.path(),
                    &rel,
                    &vault_root,
                    &mut picked,
                    &mut files,
                    &mut internal,
                );
            }
        }
    }

    files.sort_by(|a, b| a.path.cmp(&b.path));
    Collected { files, internal }
}

fn push_unique(
    path: &Path,
    rel: &str,
    vault_root: &Path,
    picked: &mut HashSet<PathBuf>,
    files: &mut Vec<Candidate>,
    internal: &mut usize,
) {
    if rel.is_empty() {
        return;
    }
    let key = fs::canonicalize(path).unwrap_or_else(|_| path.to_path_buf());
    // 只排除保险库自己写出来的密文；同目录里用户自己的照片文档照常能加密进去
    if is_internal_path(vault_root, &key) {
        *internal += 1;
        return;
    }
    if picked.insert(key) {
        files.push(Candidate {
            path: path.to_path_buf(),
            rel: rel.to_string(),
        });
    }
}

#[derive(Serialize, Deserialize, Default)]
struct AppConfig {
    last_vault: Option<String>,
}

fn config_file(app: &AppHandle) -> Option<PathBuf> {
    app.path()
        .app_config_dir()
        .ok()
        .map(|dir| dir.join("config.json"))
}

fn load_config(app: &AppHandle) -> AppConfig {
    config_file(app)
        .and_then(|path| fs::read_to_string(path).ok())
        .and_then(|raw| serde_json::from_str(&raw).ok())
        .unwrap_or_default()
}

fn save_last_vault(app: &AppHandle, path: &Path) {
    if let Some(file) = config_file(app) {
        if let Some(parent) = file.parent() {
            let _ = fs::create_dir_all(parent);
        }
        let config = AppConfig {
            last_vault: Some(path.display().to_string()),
        };
        if let Ok(raw) = serde_json::to_vec_pretty(&config) {
            let _ = fs::write(file, raw);
        }
    }
}
