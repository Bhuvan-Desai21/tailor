// Prevents additional console window on Windows in release builds
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod window_manager;
mod sidecar_manager;
mod dependency_checker;
mod ipc_router;
mod event_bus;

use std::sync::Arc;
use tauri::Manager;
use tokio::sync::Mutex;

use window_manager::WindowManager;
use sidecar_manager::SidecarManager;
use event_bus::EventBus;

#[derive(Default)]
struct AppState {
    window_manager: Arc<Mutex<WindowManager>>,
    sidecar_manager: Arc<SidecarManager>,
    event_bus: Arc<EventBus>,
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            // Initialize application state
            let window_manager = Arc::new(Mutex::new(WindowManager::new()));
            let sidecar_manager = Arc::new(SidecarManager::new());
            let event_bus = Arc::new(EventBus::new());

            // Store state in app
            app.manage(AppState {
                window_manager: window_manager.clone(),
                sidecar_manager: sidecar_manager.clone(),
                event_bus: event_bus.clone(),
            });

            println!("Tailor initialized successfully");
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            ipc_router::open_vault,
            ipc_router::send_to_sidecar,
            ipc_router::close_vault,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
