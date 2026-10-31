use std::io::{Read, Write};

use argon2::{Algorithm, Argon2, Params, Version};
use chacha20poly1305::{
    aead::{Aead, Payload},
    KeyInit, XChaCha20Poly1305, XNonce,
};
use rand::{rngs::OsRng, RngCore};
use zeroize::{Zeroize, Zeroizing};

use crate::error::{VaultError, VaultResult};

pub const KEY_LEN: usize = 32;
pub const NONCE_LEN: usize = 24;
pub const TAG_LEN: usize = 16;
pub const CHUNK_SIZE: usize = 1024 * 1024;

const BLOB_MAGIC: &[u8; 8] = b"MIXBLOB1";
const CHUNK_FLAG_FINAL: u32 = 1;

pub fn random_array<const N: usize>() -> [u8; N] {
    let mut out = [0u8; N];
    OsRng.fill_bytes(&mut out);
    out
}

pub fn derive_kek(
    password: &str,
    salt: &[u8],
    m_cost: u32,
    t_cost: u32,
    p_cost: u32,
) -> VaultResult<Zeroizing<[u8; KEY_LEN]>> {
    let params = Params::new(m_cost, t_cost, p_cost, Some(KEY_LEN))
        .map_err(|e| VaultError::Invalid(format!("Argon2 参数无效：{e}")))?;
    let argon = Argon2::new(Algorithm::Argon2id, Version::V0x13, params);
    let mut kek = Zeroizing::new([0u8; KEY_LEN]);
    argon
        .hash_password_into(password.as_bytes(), salt, &mut *kek)
        .map_err(|e| VaultError::Invalid(format!("密钥派生失败：{e}")))?;
    Ok(kek)
}

pub fn seal(key: &[u8; KEY_LEN], plaintext: &[u8], aad: &[u8]) -> VaultResult<Vec<u8>> {
    let cipher = XChaCha20Poly1305::new_from_slice(key).map_err(|_| VaultError::Encrypt)?;
    let nonce = random_array::<NONCE_LEN>();
    let ciphertext = cipher
        .encrypt(
            XNonce::from_slice(&nonce),
            Payload {
                msg: plaintext,
                aad,
            },
        )
        .map_err(|_| VaultError::Encrypt)?;
    let mut out = Vec::with_capacity(NONCE_LEN + ciphertext.len());
    out.extend_from_slice(&nonce);
    out.extend_from_slice(&ciphertext);
    Ok(out)
}

pub fn open(key: &[u8; KEY_LEN], sealed: &[u8], aad: &[u8]) -> VaultResult<Zeroizing<Vec<u8>>> {
    if sealed.len() < NONCE_LEN + TAG_LEN {
        return Err(VaultError::BadPassword);
    }
    let (nonce, ciphertext) = sealed.split_at(NONCE_LEN);
    let cipher = XChaCha20Poly1305::new_from_slice(key).map_err(|_| VaultError::BadPassword)?;
    let plaintext = cipher
        .decrypt(
            XNonce::from_slice(nonce),
            Payload {
                msg: ciphertext,
                aad,
            },
        )
        .map_err(|_| VaultError::BadPassword)?;
    Ok(Zeroizing::new(plaintext))
}

pub fn item_aad(id: &str, domain: &str) -> Vec<u8> {
    let mut aad = b"mixia-chunk-v1".to_vec();
    aad.extend_from_slice(domain.as_bytes());
    aad.push(b':');
    aad.extend_from_slice(id.as_bytes());
    aad
}

pub fn key_aad(id: &str) -> Vec<u8> {
    let mut aad = b"mixia-fk-v1:".to_vec();
    aad.extend_from_slice(id.as_bytes());
    aad
}

pub fn thumb_aad(id: &str) -> Vec<u8> {
    let mut aad = b"mixia-thumb-v1:".to_vec();
    aad.extend_from_slice(id.as_bytes());
    aad
}

fn chunk_aad(base: &[u8], index: u32, is_final: bool) -> Vec<u8> {
    let mut aad = Vec::with_capacity(base.len() + 5);
    aad.extend_from_slice(base);
    aad.extend_from_slice(&index.to_le_bytes());
    aad.push(if is_final { 1 } else { 0 });
    aad
}

pub fn encrypt_blob<R: Read, W: Write>(
    mut reader: R,
    mut writer: W,
    key: &[u8; KEY_LEN],
    aad_base: &[u8],
) -> VaultResult<(u64, u32)> {
    let cipher = XChaCha20Poly1305::new_from_slice(key).map_err(|_| VaultError::Encrypt)?;
    writer.write_all(BLOB_MAGIC)?;

    let mut buf = vec![0u8; CHUNK_SIZE];
    let mut chunks: u32 = 0;
    let mut total: u64 = 0;

    loop {
        let read = read_full(&mut reader, &mut buf)?;
        if read == 0 {
            write_chunk(&cipher, &mut writer, &[], true, chunks, aad_base)?;
            chunks += 1;
            break;
        }
        total += read as u64;
        let is_final = read < CHUNK_SIZE;
        write_chunk(
            &cipher,
            &mut writer,
            &buf[..read],
            is_final,
            chunks,
            aad_base,
        )?;
        chunks += 1;
        if is_final {
            break;
        }
    }

    buf.zeroize();
    writer.flush()?;
    Ok((total, chunks))
}

pub fn decrypt_blob<R: Read, W: Write>(
    mut reader: R,
    mut writer: W,
    key: &[u8; KEY_LEN],
    aad_base: &[u8],
    expected_chunks: u32,
) -> VaultResult<u64> {
    let mut magic = [0u8; 8];
    reader
        .read_exact(&mut magic)
        .map_err(|_| VaultError::Invalid("加密文件头不完整".into()))?;
    if &magic != BLOB_MAGIC {
        return Err(VaultError::Invalid("加密文件头无效".into()));
    }
    if expected_chunks == 0 {
        return Err(VaultError::Invalid("索引中的分块数无效".into()));
    }

    let cipher = XChaCha20Poly1305::new_from_slice(key).map_err(|_| VaultError::Encrypt)?;
    let mut total: u64 = 0;
    let mut index: u32 = 0;

    loop {
        if index >= expected_chunks {
            return Err(VaultError::Invalid("加密文件包含多余分块".into()));
        }

        let mut header = [0u8; 8];
        reader
            .read_exact(&mut header)
            .map_err(|_| VaultError::Invalid("加密文件被截断".into()))?;
        let len = u32::from_le_bytes(header[0..4].try_into().unwrap()) as usize;
        let flags = u32::from_le_bytes(header[4..8].try_into().unwrap());
        if len > CHUNK_SIZE {
            return Err(VaultError::Invalid("加密文件分块长度异常".into()));
        }
        let is_final = flags & CHUNK_FLAG_FINAL != 0;

        let mut nonce = [0u8; NONCE_LEN];
        reader
            .read_exact(&mut nonce)
            .map_err(|_| VaultError::Invalid("加密文件被截断".into()))?;
        let mut ciphertext = vec![0u8; len + TAG_LEN];
        reader
            .read_exact(&mut ciphertext)
            .map_err(|_| VaultError::Invalid("加密文件被截断".into()))?;

        let aad = chunk_aad(aad_base, index, is_final);
        let plaintext = cipher
            .decrypt(
                XNonce::from_slice(&nonce),
                Payload {
                    msg: &ciphertext,
                    aad: &aad,
                },
            )
            .map_err(|_| VaultError::Invalid("数据校验失败，文件可能被篡改".into()))?;
        let plaintext = Zeroizing::new(plaintext);

        writer.write_all(&plaintext)?;
        total += plaintext.len() as u64;
        index += 1;

        if is_final {
            break;
        }
    }

    if index != expected_chunks {
        return Err(VaultError::Invalid("加密文件被截断".into()));
    }

    let mut extra = [0u8; 1];
    loop {
        match reader.read(&mut extra) {
            Ok(0) => break,
            Ok(_) => return Err(VaultError::Invalid("加密文件包含多余数据".into())),
            Err(e) if e.kind() == std::io::ErrorKind::Interrupted => continue,
            Err(e) => return Err(e.into()),
        }
    }

    writer.flush()?;
    Ok(total)
}

fn write_chunk<W: Write>(
    cipher: &XChaCha20Poly1305,
    writer: &mut W,
    plaintext: &[u8],
    is_final: bool,
    index: u32,
    aad_base: &[u8],
) -> VaultResult<()> {
    let nonce = random_array::<NONCE_LEN>();
    let aad = chunk_aad(aad_base, index, is_final);
    let ciphertext = cipher
        .encrypt(
            XNonce::from_slice(&nonce),
            Payload {
                msg: plaintext,
                aad: &aad,
            },
        )
        .map_err(|_| VaultError::Encrypt)?;

    writer.write_all(&(plaintext.len() as u32).to_le_bytes())?;
    writer.write_all(&(if is_final { CHUNK_FLAG_FINAL } else { 0 }).to_le_bytes())?;
    writer.write_all(&nonce)?;
    writer.write_all(&ciphertext)?;
    Ok(())
}

fn read_full<R: Read>(reader: &mut R, buf: &mut [u8]) -> VaultResult<usize> {
    let mut filled = 0;
    while filled < buf.len() {
        match reader.read(&mut buf[filled..]) {
            Ok(0) => break,
            Ok(n) => filled += n,
            Err(e) if e.kind() == std::io::ErrorKind::Interrupted => continue,
            Err(e) => return Err(e.into()),
        }
    }
    Ok(filled)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    #[test]
    fn chunked_roundtrip_for_various_sizes() {
        let key = random_array::<KEY_LEN>();
        let aad = b"test-aad";
        for size in [0usize, 1, 1024, CHUNK_SIZE - 1, CHUNK_SIZE, CHUNK_SIZE * 2] {
            let data: Vec<u8> = (0..size).map(|i| (i % 251) as u8).collect();
            let mut encrypted = Vec::new();
            let (written, chunks) =
                encrypt_blob(Cursor::new(&data), &mut encrypted, &key, aad).unwrap();
            assert_eq!(written, size as u64);
            assert!(chunks >= 1);

            let mut decrypted = Vec::new();
            let read = decrypt_blob(
                Cursor::new(&encrypted),
                &mut decrypted,
                &key,
                aad,
                chunks,
            )
            .unwrap();
            assert_eq!(read, size as u64);
            assert_eq!(decrypted, data);
        }
    }

    #[test]
    fn tampering_and_truncation_are_rejected() {
        let key = random_array::<KEY_LEN>();
        let aad = b"test-aad";
        let data = vec![7u8; 4096];
        let mut encrypted = Vec::new();
        let (_, chunks) = encrypt_blob(Cursor::new(&data), &mut encrypted, &key, aad).unwrap();

        let mut tampered = encrypted.clone();
        let last = tampered.len() - 1;
        tampered[last] ^= 0xFF;
        assert!(decrypt_blob(Cursor::new(&tampered), Vec::new(), &key, aad, chunks).is_err());

        let truncated = encrypted[..encrypted.len() - 1].to_vec();
        assert!(decrypt_blob(Cursor::new(&truncated), Vec::new(), &key, aad, chunks).is_err());

        let mut extended = encrypted.clone();
        extended.push(0);
        assert!(decrypt_blob(Cursor::new(&extended), Vec::new(), &key, aad, chunks).is_err());
    }
}
