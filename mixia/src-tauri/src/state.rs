use std::fs;
use std::path::PathBuf;
use std::sync::atomic::AtomicBool;
use std::sync::Mutex;

use mixia::error::{VaultError, VaultResult};
use mixia::vault::Vault;

#[derive(Default)]
pub struct AppState {
    pub inner: Mutex<Inner>,
    /// 长任务（导入 / 全部导出）的取消位。放在锁外面，否则工作线程占着锁时
    /// 界面根本没法把「取消」送进来。
    pub cancel: AtomicBool,
}

#[derive(Default)]
pub struct Inner {
    pub vault_path: Option<PathBuf>,
    pub session: Option<Session>,
}

impl Inner {
    pub fn session(&self) -> VaultResult<&Session> {
        self.session.as_ref().ok_or(VaultError::Locked)
    }

    pub fn session_mut(&mut self) -> VaultResult<&mut Session> {
        self.session.as_mut().ok_or(VaultError::Locked)
    }
}

pub struct Session {
    pub vault: Vault,
    pub temp_dir: PathBuf,
}

impl Session {
    pub fn new(vault: Vault) -> VaultResult<Self> {
        let temp_dir = std::env::temp_dir().join(format!("mixia-{}", uuid::Uuid::new_v4()));
        fs::create_dir_all(&temp_dir)?;
        Ok(Self { vault, temp_dir })
    }
}

impl Drop for Session {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.temp_dir);
    }
}
