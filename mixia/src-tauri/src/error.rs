use thiserror::Error;

#[derive(Debug, Error)]
pub enum VaultError {
    #[error("文件读写失败：{0}")]
    Io(#[from] std::io::Error),
    #[error("数据解析失败：{0}")]
    Json(#[from] serde_json::Error),
    #[error("加密失败")]
    Encrypt,
    #[error("密码错误，或保险库数据已损坏")]
    BadPassword,
    #[error("保险库格式无效：{0}")]
    Invalid(String),
    #[error("保险库尚未解锁")]
    Locked,
    #[error("找不到该文件")]
    ItemNotFound,
    #[error("该文件夹中已经存在保险库")]
    AlreadyExists,
    #[error("参数不合法：{0}")]
    InvalidInput(String),
}

pub type VaultResult<T> = std::result::Result<T, VaultError>;
