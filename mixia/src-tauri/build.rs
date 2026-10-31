use std::path::PathBuf;

fn main() {
    #[cfg(windows)]
    if let Some(icon) = safe_icon_path() {
        let attributes = tauri_build::Attributes::new().windows_attributes(
            tauri_build::WindowsAttributes::new().window_icon_path(icon),
        );
        tauri_build::try_build(attributes).expect("failed to run tauri-build");
        return;
    }

    tauri_build::build()
}

/// Windows 资源编译器会把路径中的单引号错误转义。
/// 当项目路径包含单引号时，改用一个不含单引号的图标副本。
#[cfg(windows)]
fn safe_icon_path() -> Option<PathBuf> {
    let manifest_dir = PathBuf::from(std::env::var_os("CARGO_MANIFEST_DIR")?);
    let icon = manifest_dir.join("icons").join("icon.ico");
    let icon_text = icon.to_string_lossy();

    if !icon_text.contains('\'') {
        return None;
    }

    let public = PathBuf::from(std::env::var_os("PUBLIC")?);
    let target_dir = public.join("MixiaBuild");
    std::fs::create_dir_all(&target_dir).ok()?;
    let target = target_dir.join("icon.ico");
    std::fs::copy(&icon, &target).ok()?;
    Some(target)
}
