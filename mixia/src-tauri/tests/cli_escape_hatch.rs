//! 逃生通道的端到端契约测试。
//!
//! 这里**只**通过 `mixia-cli` 的命令行接口操作保险库：退出码、stdout、解出的字节。
//! GUI 和存储层内部怎么改，都不该让这条路断掉——它是「项目不再维护了，你的文件还取得出来」
//! 这句话唯一的凭据，所以要用真进程、真文件、真密码来验，而不是用库内函数模拟。

use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

const PASSWORD: &str = "tao-sheng-tong-dao-2026";
const NEW_PASSWORD: &str = "huan-le-mi-ma-ye-neng-kai-2026";

fn mixia(command: &str, vault: &Path, extra: &[&Path], password: &str) -> Output {
    let mut args = vec![command.into(), vault.to_path_buf()];
    args.extend(extra.iter().map(|p| p.to_path_buf()));
    Command::new(env!("CARGO_BIN_EXE_mixia-cli"))
        .args(&args)
        .env("MIXIA_PASSWORD", password)
        .output()
        .expect("无法启动 mixia-cli")
}

fn stdout(out: &Output) -> String {
    String::from_utf8_lossy(&out.stdout).to_string()
}

fn stderr(out: &Output) -> String {
    String::from_utf8_lossy(&out.stderr).to_string()
}

fn assert_ok(out: &Output, what: &str) {
    assert!(
        out.status.success(),
        "{what} 应当成功，实际退出码 {:?}，stderr: {}",
        out.status.code(),
        stderr(out)
    );
}

/// 造三个覆盖边界的文件：空、非整块长度、整块倍数。
fn seed_samples(dir: &Path) -> Vec<PathBuf> {
    [("零字节.bin", 0usize), ("小文件.txt", 1234), ("整块.bin", 2 * 1024 * 1024)]
        .into_iter()
        .map(|(name, len)| {
            let path = dir.join(name);
            let bytes: Vec<u8> = (0..len).map(|i| (i % 251) as u8).collect();
            fs::write(&path, bytes).expect("写入样本失败");
            path
        })
        .collect()
}

fn largest_blob(vault: &Path) -> PathBuf {
    fs::read_dir(vault.join("blobs"))
        .expect("没有 blobs 目录")
        .flatten()
        .map(|entry| entry.path())
        .max_by_key(|path| fs::metadata(path).map(|meta| meta.len()).unwrap_or(0))
        .expect("blobs 目录为空")
}

#[test]
fn escape_hatch_creates_verifies_extracts_and_detects_tampering() {
    let tmp = tempfile::tempdir().expect("tempdir");
    let root = tmp.path();
    let vault = root.join("我的保险库");
    let out_dir = root.join("取回");
    fs::create_dir(&vault).expect("建库目录失败");

    let samples = seed_samples(root);
    let empty: &[&Path] = &[];

    assert_ok(
        &mixia("create", &vault, empty, PASSWORD),
        "create",
    );
    assert!(vault.join("vault.json").is_file(), "应写出 vault.json");
    assert!(vault.join("index.enc").is_file(), "应写出 index.enc");

    let paths: Vec<&Path> = samples.iter().map(|p| p.as_path()).collect();
    let imported = mixia("import", &vault, &paths, PASSWORD);
    assert_ok(&imported, "import");
    assert!(
        stdout(&imported).contains("共导入 3 个文件"),
        "导入结果不对：{}",
        stdout(&imported)
    );

    let listed = stdout(&mixia("list", &vault, empty, PASSWORD));
    for name in ["零字节.bin", "小文件.txt", "整块.bin"] {
        assert!(listed.contains(name), "list 输出缺少 {name}：{listed}");
    }

    assert_ok(
        &mixia("verify", &vault, empty, PASSWORD),
        "verify（干净库）",
    );

    assert_ok(
        &mixia("extract", &vault, &[out_dir.as_path()], PASSWORD),
        "extract",
    );
    for sample in &samples {
        let name = sample.file_name().unwrap();
        let got = fs::read(out_dir.join(name)).expect("解出的文件不存在");
        let want = fs::read(sample).expect("样本文件不见了");
        assert_eq!(got, want, "{name:?} 解出的内容与原文件不一致");
    }

    let wrong = mixia("list", &vault, empty, "cuo-wu-de-mi-ma-123456");
    assert_eq!(wrong.status.code(), Some(1), "错误密码竟然列出了文件");
}

#[test]
fn escape_hatch_survives_password_change_and_reports_damaged_blob() {
    let tmp = tempfile::tempdir().expect("tempdir");
    let root = tmp.path();
    let vault = root.join("保险库");
    fs::create_dir(&vault).expect("建库目录失败");
    let samples = seed_samples(root);
    let paths: Vec<&Path> = samples.iter().map(|p| p.as_path()).collect();
    let empty: &[&Path] = &[];

    assert_ok(&mixia("create", &vault, empty, PASSWORD), "create");
    assert_ok(&mixia("import", &vault, &paths, PASSWORD), "import");

    assert_ok(
        &mixia(
            "set-password",
            &vault,
            &[Path::new(NEW_PASSWORD)],
            PASSWORD,
        ),
        "set-password",
    );
    assert_ok(
        &mixia("list", &vault, empty, NEW_PASSWORD),
        "改密后用新密码 list",
    );
    assert!(
        !mixia("list", &vault, empty, PASSWORD).status.success(),
        "改密后旧密码仍然可用"
    );

    let blob = largest_blob(&vault);
    let mut raw = fs::read(&blob).expect("读密文失败");
    let middle = raw.len() / 2;
    raw[middle] ^= 0xff;
    fs::write(&blob, raw).expect("写密文失败");

    let damaged = mixia("verify", &vault, empty, NEW_PASSWORD);
    assert_eq!(damaged.status.code(), Some(2), "篡改后 verify 没有退出 2");
    assert!(
        stdout(&damaged).contains("损坏"),
        "体检报告没指出损坏项：{}",
        stdout(&damaged)
    );
}
