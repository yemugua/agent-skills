#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod state;

use state::AppState;
use tauri::Manager;

fn main() {
    let app = tauri::Builder::default()
        .manage(AppState::default())
        .invoke_handler(tauri::generate_handler![
            commands::get_state,
            commands::pick_folder,
            commands::create_vault,
            commands::open_vault,
            commands::unlock_vault,
            commands::lock_vault,
            commands::list_items,
            commands::get_thumb,
            commands::import_files,
            commands::import_folder,
            commands::import_paths,
            commands::export_item,
            commands::export_all,
            commands::cancel_operation,
            commands::delete_sources,
            commands::scan_originals,
            commands::open_item,
            commands::delete_item,
            commands::delete_items,
            commands::rename_item,
            commands::change_password,
        ])
        .setup(|_app| {
            cleanup_stale_temp();
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build Mixia");

    app.run(|handle, event| {
        if let tauri::RunEvent::Exit = event {
            if let Some(state) = handle.try_state::<AppState>() {
                let mut guard = state.inner.lock().unwrap_or_else(|e| e.into_inner());
                guard.session = None;
            }
        }
    });
}

fn cleanup_stale_temp() {
    let Ok(entries) = std::fs::read_dir(std::env::temp_dir()) else {
        return;
    };
    let now = std::time::SystemTime::now();
    for entry in entries.flatten() {
        let name = entry.file_name();
        let name = name.to_string_lossy();
        if !name.starts_with("mixia-") {
            continue;
        }
        let stale = entry
            .metadata()
            .ok()
            .and_then(|meta| meta.modified().ok())
            .and_then(|modified| now.duration_since(modified).ok())
            .map(|age| age.as_secs() > 86_400)
            .unwrap_or(false);
        if stale {
            let _ = std::fs::remove_dir_all(entry.path());
        }
    }
}
