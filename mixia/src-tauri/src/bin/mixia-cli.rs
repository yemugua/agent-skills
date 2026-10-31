//! 秘匣命令行工具：图形界面之外的逃生通道。
//!
//! 保险库格式是公开文档（docs/FORMAT.md），这个 CLI 与 GUI 共用同一套存储层，
//! 因此即使 GUI 不再维护，用户依然能列出、校验并完整解出自己的文件。

use std::io::{IsTerminal, Write};
use std::path::{Path, PathBuf};

use mixia::vault::Vault;

const USAGE: &str = "\
秘匣命令行工具 —— 不依赖图形界面的保险库读写

用法：
  mixia-cli <命令> <保险库目录> [参数] [--password 密码]

命令：
  info                      查看保险库头部与密钥派生参数
  list                      列出所有文件（id、大小、类型、名称）
  verify                    逐个校验密文完整性，不写出明文
  export   <id> <目标文件>   解密单个文件（id 可用唯一前缀）
  extract  <输出目录>        解密全部文件到目录
  create                    新建保险库（目录需为空）
  import   <文件...>         加密导入若干文件
  set-password <新密码>      修改密码（只重新包装主密钥）

密码来源，按优先级：
  1. --password 参数（会出现在进程列表与 shell 历史里，仅建议脚本临时使用）
  2. 环境变量 MIXIA_PASSWORD
  3. 交互式输入（终端不回显无法关闭，输入时会明文显示，请留意周围）

退出码：0 成功；1 参数或密码错误；2 校验发现损坏。
";

fn main() {
    match run() {
        Ok(code) => std::process::exit(code),
        Err(message) => {
            eprintln!("错误：{message}");
            std::process::exit(1);
        }
    }
}

fn run() -> Result<i32, String> {
    let mut args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        print!("{USAGE}");
        return Ok(0);
    }

    let mut password: Option<String> = None;
    if let Some(index) = args.iter().position(|a| a == "--password") {
        let value = args
            .get(index + 1)
            .cloned()
            .ok_or("--password 缺少参数值")?;
        args.remove(index + 1);
        args.remove(index);
        password = Some(value);
    }

    let command = args.remove(0);
    if command == "help" || command == "--help" || command == "-h" {
        print!("{USAGE}");
        return Ok(0);
    }
    let dir = match args.first() {
        Some(path) => PathBuf::from(path),
        None => return Err(format!("缺少保险库目录\n\n{USAGE}")),
    };

    if command == "create" {
        let vault = Vault::create(&dir, &take_password(password)?).map_err(err)?;
        println!("已创建保险库：{}", vault.path.display());
        return Ok(0);
    }

    let vault = Vault::open(&dir, &take_password(password)?).map_err(err)?;

    match command.as_str() {
        "info" => {
            let header = &vault.header;
            println!("保险库目录  : {}", dir.display());
            println!("格式版本    : {}", header.version);
            println!("创建时间    : {}", format_time(header.created_at));
            println!("KDF         : {} m={} t={} p={}", header.kdf.name, header.kdf.m_cost, header.kdf.t_cost, header.kdf.p_cost);
            println!("文件数      : {}", vault.manifest.items.len());
            Ok(0)
        }
        "list" => {
            for item in &vault.manifest.items {
                println!(
                    "{:8}  {:>10}  {:<8}  {}",
                    short(&item.id),
                    item.size,
                    item.kind,
                    item.name
                );
            }
            Ok(0)
        }
        "verify" => {
            let issues = vault.verify();
            for issue in &issues {
                println!("损坏  {}  {}  —— {}", short(&issue.id), issue.name, issue.reason);
            }
            if issues.is_empty() {
                println!(
                    "校验通过：{} 个文件全部可解密",
                    vault.manifest.items.len()
                );
                Ok(0)
            } else {
                println!("发现 {} 个文件无法解密", issues.len());
                Ok(2)
            }
        }
        "export" => {
            let id = args.get(1).ok_or("export 需要 <id> <目标文件>")?;
            let dest = args.get(2).ok_or("export 需要 <目标文件>")?;
            let item = find(&vault, id)?;
            vault
                .export_to(&item.id, Path::new(dest))
                .map_err(err)?;
            println!("已解密导出：{} -> {}", item.name, dest);
            Ok(0)
        }
        "extract" => {
            let out = args.get(1).ok_or("extract 需要 <输出目录>")?.clone();
            let dir_out = Path::new(&out);
            std::fs::create_dir_all(dir_out).map_err(err)?;
            let items = vault.manifest.items.clone();
            for item in &items {
                let dest = dir_out.join(Vault::item_rel_path(item));
                if let Some(parent) = dest.parent() {
                    std::fs::create_dir_all(parent).map_err(err)?;
                }
                vault.export_to(&item.id, &dest).map_err(err)?;
                println!("已导出 {}", item.name);
            }
            println!("共导出 {} 个文件到 {}", items.len(), out);
            Ok(0)
        }
        "import" => {
            if args.len() < 2 {
                return Err("import 需要至少一个文件路径".into());
            }
            let mut vault = vault;
            let mut added = 0usize;
            for path in &args[1..] {
                match vault.import_file(Path::new(path)) {
                    Ok(item) => {
                        println!("已加密 {}（{} 字节）", item.name, item.size);
                        added += 1;
                    }
                    Err(e) => eprintln!("跳过 {}：{}", path, e),
                }
            }
            vault.save_index().map_err(err)?;
            println!("共导入 {} 个文件", added);
            Ok(0)
        }
        "set-password" => {
            let new_password = args.get(1).cloned().ok_or("set-password 需要 <新密码>")?;
            let mut vault = vault;
            vault.change_password(&new_password).map_err(err)?;
            println!("密码已修改。请用新密码重新验证一次：mixia-cli info {} --password 新密码", dir.display());
            Ok(0)
        }
        other => Err(format!("未知命令：{other}\n\n{USAGE}")),
    }
}

fn take_password(explicit: Option<String>) -> Result<String, String> {
    if let Some(value) = explicit {
        return Ok(value);
    }
    if let Ok(from_env) = std::env::var("MIXIA_PASSWORD") {
        return Ok(from_env);
    }
    if !std::io::stdin().is_terminal() {
        return Err("未提供密码：请用 --password 或环境变量 MIXIA_PASSWORD".into());
    }
    eprint!("保险库密码（输入不会隐藏）：");
    std::io::stderr().flush().ok();
    let mut line = String::new();
    std::io::stdin()
        .read_line(&mut line)
        .map_err(|e| e.to_string())?;
    let trimmed = line.trim_end_matches(['\r', '\n']).to_string();
    if trimmed.is_empty() {
        return Err("密码不能为空".into());
    }
    Ok(trimmed)
}

fn find(vault: &Vault, needle: &str) -> Result<mixia::vault::Item, String> {
    let matches: Vec<_> = vault
        .manifest
        .items
        .iter()
        .filter(|item| item.id == needle || item.id.starts_with(needle) || item.name == needle)
        .cloned()
        .collect();
    match matches.len() {
        0 => Err(format!("找不到 id 或名称为 {needle} 的文件")),
        1 => Ok(matches.into_iter().next().unwrap()),
        _ => Err(format!("{needle} 匹配到 {} 个文件，请写更完整的前缀", matches.len())),
    }
}

fn err(error: impl std::fmt::Display) -> String {
    error.to_string()
}

fn short(id: &str) -> String {
    id.chars().take(8).collect()
}

fn format_time(secs: u64) -> String {
    // 不引入日期库：只给出 UTC 秒与近似天数，够用来核对建库时间。
    format!("{secs} 秒（UTC，约 {} 天前）", secs / 86_400)
}
