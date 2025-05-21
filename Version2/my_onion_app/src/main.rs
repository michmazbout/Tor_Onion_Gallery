use gtk4::{
    gio, glib,
    prelude::*,
    Application, ApplicationWindow, Box, Button, CssProvider, Label, 
    Orientation, ScrolledWindow, StyleContext
};
use libadwaita::{HeaderBar, ToastOverlay};
use once_cell::sync::Lazy;
use serde::{Deserialize, Serialize};
use std::{fs, path::PathBuf, sync::Mutex};

// Bookmark data structure
#[derive(Debug, Clone, Serialize, Deserialize)]
struct Bookmark {
    name: String,
    url: String,
}

// App state
struct AppState {
    bookmarks: Vec<Bookmark>,
    config_dir: PathBuf,
}

static APP_STATE: Lazy<Mutex<AppState>> = Lazy::new(|| {
    let config_dir = dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from(".config"))
        .join("tor_launcher");
    
    fs::create_dir_all(&config_dir).ok();
    
    let bookmarks_file = config_dir.join("bookmarks.json");
    let bookmarks = if bookmarks_file.exists() {
        serde_json::from_str(&fs::read_to_string(bookmarks_file).unwrap_or_default()).unwrap_or_default()
    } else {
        Vec::new()
    };
    
    Mutex::new(AppState {
        bookmarks,
        config_dir,
    })
});

fn main() -> glib::ExitCode {
    let app = Application::builder()
        .application_id("com.example.TorLauncher")
        .build();

    app.connect_activate(|app| {
        // Create main window
        let window = ApplicationWindow::builder()
            .application(app)
            .title("Tor Launcher")
            .default_width(900)
            .default_height(700)
            .build();

        // CSS styling (you'll need a style.css file)
        let provider = CssProvider::new();
        provider.load_from_data(include_str!("style.css"));
        StyleContext::add_provider_for_display(
            &window.display(),
            &provider,
            gtk4::STYLE_PROVIDER_PRIORITY_APPLICATION,
        );

        // Main layout
        let root_box = Box::new(Orientation::Vertical, 0);
        let overlay = ToastOverlay::new();
        overlay.set_child(Some(&root_box));
        window.set_content(Some(&overlay));

        // Header bar
        let header = HeaderBar::new();
        root_box.append(&header);

        // Add button
        let add_btn = Button::builder()
            .icon_name("list-add-symbolic")
            .build();
        header.pack_end(&add_btn);

        // Bookmarks container
        let scrolled = ScrolledWindow::new();
        root_box.append(&scrolled);

        // Show window
        window.present();
    });

    app.run()
}