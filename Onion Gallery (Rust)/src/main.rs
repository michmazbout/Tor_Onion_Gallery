use eframe::egui;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{File, OpenOptions};
use std::io::{Read, Write};
use std::path::PathBuf;

#[derive(Serialize, Deserialize, Clone)]
struct OnionLink {
    title: String,
    url: String,
}

struct OnionLinkManager {
    links: HashMap<String, OnionLink>,
    new_title: String,
    new_url: String,
    edit_title: Option<String>,
    edit_url: Option<String>,
    file_path: PathBuf,
}

impl Default for OnionLinkManager {
    fn default() -> Self {
        let mut app = Self {
            links: HashMap::new(),
            new_title: String::new(),
            new_url: String::new(),
            edit_title: None,
            edit_url: None,
            file_path: PathBuf::from("onion_links.json"),
        };
        app.load_links();
        app
    }
}

impl OnionLinkManager {
    fn load_links(&mut self) {
        if let Ok(mut file) = File::open(&self.file_path) {
            let mut contents = String::new();
            file.read_to_string(&mut contents).unwrap();
            if let Ok(links) = serde_json::from_str::<HashMap<String, OnionLink>>(&contents) {
                self.links = links;
            }
        }
    }

    fn save_links(&self) {
        let contents = serde_json::to_string(&self.links).unwrap();
        let mut file = OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .open(&self.file_path)
            .unwrap();
        file.write_all(contents.as_bytes()).unwrap();
    }
}

impl eframe::App for OnionLinkManager {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("Onion Link Manager");

            // Modern UI styling
            ui.style_mut().spacing.item_spacing = egui::vec2(10.0, 10.0);
            ui.style_mut().visuals.widgets.noninteractive.rounding = 5.0.into();
            ui.style_mut().visuals.widgets.inactive.rounding = 5.0.into();
            ui.style_mut().visuals.widgets.hovered.rounding = 5.0.into();
            ui.style_mut().visuals.widgets.active.rounding = 5.0.into();
            ui.style_mut().visuals.widgets.open.rounding = 5.0.into();

            // Add a new link
            ui.horizontal(|ui| {
                ui.label("Title:");
                ui.text_edit_singleline(&mut self.new_title);
                ui.label("URL:");
                ui.text_edit_singleline(&mut self.new_url);
                if ui.button("Add").clicked() {
                    if !self.new_title.is_empty() && !self.new_url.is_empty() {
                        self.links.insert(
                            self.new_title.clone(),
                            OnionLink {
                                title: self.new_title.clone(),
                                url: self.new_url.clone(),
                            },
                        );
                        self.new_title.clear();
                        self.new_url.clear();
                        self.save_links();
                    }
                }
            });

            // Display existing links
            ui.separator();
            ui.label("Saved Links:");

            // Collect keys to avoid borrowing issues
            let keys: Vec<String> = self.links.keys().cloned().collect();
            for title in keys {
                if let Some(link) = self.links.get(&title) {
                    let link_clone = link.clone(); // Clone the link to avoid borrowing issues
                    ui.horizontal(|ui| {
                        if let Some(edit_title) = &self.edit_title {
                            if edit_title == &title {
                                let mut edit_title_clone = edit_title.clone();
                                let mut edit_url_clone = self.edit_url.clone().unwrap_or_default();
                                ui.text_edit_singleline(&mut edit_title_clone);
                                ui.text_edit_singleline(&mut edit_url_clone);
                                if ui.button("Save").clicked() {
                                    let mut updated_link = link_clone.clone();
                                    updated_link.title = edit_title_clone.clone();
                                    updated_link.url = edit_url_clone.clone();
                                    self.links.insert(edit_title_clone.clone(), updated_link);
                                    if edit_title_clone != title {
                                        self.links.remove(&title);
                                    }
                                    self.edit_title = None;
                                    self.edit_url = None;
                                    self.save_links();
                                }
                            } else {
                                ui.label(&link_clone.title);
                                if ui.link(&link_clone.url).clicked() {
                                    ui.output_mut(|o| o.copied_text = link_clone.url.clone());
                                }
                                if ui.button("Edit").clicked() {
                                    self.edit_title = Some(link_clone.title.clone());
                                    self.edit_url = Some(link_clone.url.clone());
                                }
                                if ui.button("Delete").clicked() {
                                    self.links.remove(&title);
                                    self.save_links();
                                }
                            }
                        } else {
                            ui.label(&link_clone.title);
                            if ui.link(&link_clone.url).clicked() {
                                ui.output_mut(|o| o.copied_text = link_clone.url.clone());
                            }
                            if ui.button("Edit").clicked() {
                                self.edit_title = Some(link_clone.title.clone());
                                self.edit_url = Some(link_clone.url.clone());
                            }
                            if ui.button("Delete").clicked() {
                                self.links.remove(&title);
                                self.save_links();
                            }
                        }
                    });
                }
            }
        });
    }
}

fn main() {
    let options = eframe::NativeOptions::default();
    eframe::run_native(
        "Onion Link Manager",
        options,
        Box::new(|_cc| Box::new(OnionLinkManager::default())),
    );
}
