//! 秘匣的存储格式层：密钥派生、分块 AEAD、保险库索引。
//!
//! 图形界面（`src/main.rs`）和命令行工具（`src/bin/mixia-cli.rs`）共用这一层，
//! 因此即使不再维护 GUI，用户也能用 CLI 或本模块自行解开保险库。

pub mod crypto;
pub mod error;
pub mod vault;

pub use error::{VaultError, VaultResult};
