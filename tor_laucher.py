import gi
import json
import os
import re
from pathlib import Path

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, Gdk, GdkPixbuf

CSS = """
    .card {
        background: alpha(@card_bg_color, 0.8);
        border-radius: 18px;
        padding: 18px;
        margin: 6px;
        box-shadow: 0 4px 6px -1px alpha(@card_shade_color, 0.1), 
                    0 2px 4px -1px alpha(@card_shade_color, 0.06);
        transition: all 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
    }
    
    .card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 15px -3px alpha(@card_shade_color, 0.1), 
                    0 4px 6px -2px alpha(@card_shade_color, 0.05);
        background: alpha(@card_bg_color, 0.9);
    }
    
    .card:active {
        transform: translateY(0);
        transition-duration: 50ms;
    }
    
    .card-icon {
        opacity: 0.9;
        -gtk-icon-size: 48px;
    }
    
    .title-label {
        font-size: 14px;
        font-weight: 600;
        margin-top: 8px;
    }
    
    .toast {
        background: @accent_bg_color;
        color: @accent_fg_color;
        border-radius: 12px;
        margin: 12px;
        padding: 12px 18px;
        box-shadow: 0 4px 12px alpha(black, 0.15);
    }
    
    .search-bar {
        background: alpha(@headerbar_bg_color, 0.8);
        margin: 12px;
        border-radius: 12px;
        box-shadow: 0 2px 8px alpha(black, 0.08);
    }
    
    .empty-state {
        opacity: 0.5;
    }
"""

class ModernToast(Gtk.Revealer):
    def __init__(self, message):
        super().__init__()
        self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.set_transition_duration(300)
        self.set_valign(Gtk.Align.END)
        self.set_halign(Gtk.Align.CENTER)
        
        box = Gtk.Box(spacing=12, margin_top=6, margin_bottom=24,
                     margin_start=12, margin_end=12)
        box.add_css_class("toast")
        
        label = Gtk.Label(label=message)
        box.append(label)
        
        self.set_child(box)
    
    def show(self):
        self.set_reveal_child(True)
        GLib.timeout_add_seconds(3, self.dismiss)
    
    def dismiss(self):
        self.set_reveal_child(False)
        return False

class BookmarkCard(Gtk.Button):
    def __init__(self, name, icon_name="web-browser-symbolic"):
        super().__init__()
        self.add_css_class("card")
        self.set_size_request(160, 140)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_valign(Gtk.Align.CENTER)
        
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.add_css_class("card-icon")
        box.append(icon)
        
        label = Gtk.Label(label=name)
        label.add_css_class("title-label")
        label.set_max_width_chars(15)
        label.set_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)
        box.append(label)
        
        self.set_child(box)

class AddEditDialog(Adw.Window):
    def __init__(self, parent, bookmark=None):
        super().__init__(title="Edit Bookmark" if bookmark else "Add Bookmark")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(400, 300)
        
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=self.get_title(), 
                                              subtitle="Manage your onion links"))
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(500)
        clamp.set_margin_top(12)
        clamp.set_margin_bottom(12)
        clamp.set_margin_start(24)
        clamp.set_margin_end(24)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        
        self.name_entry = Adw.EntryRow(title="Site Name")
        self.name_entry.set_text(bookmark["name"] if bookmark else "")
        box.append(self.name_entry)
        
        self.url_entry = Adw.EntryRow(title="Onion URL")
        self.url_entry.set_text(bookmark["url"] if bookmark else "")
        box.append(self.url_entry)
        
        button_box = Gtk.Box(spacing=12, halign=Gtk.Align.END)
        
        if bookmark:
            delete_btn = Gtk.Button(label="Delete")
            delete_btn.add_css_class("destructive-action")
            delete_btn.connect("clicked", self.on_delete)
            button_box.append(delete_btn)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.destroy())
        button_box.append(cancel_btn)
        
        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self.on_save)
        button_box.append(save_btn)
        
        box.append(button_box)
        clamp.set_child(box)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(header)
        main_box.append(clamp)
        self.set_content(main_box)
        
        self.callback = None
        self.bookmark = bookmark
    
    def on_save(self, button):
        name = self.name_entry.get_text().strip()
        url = self.url_entry.get_text().strip()
        
        if not name:
            self.show_error("Name is required")
            return
        
        if not url:
            self.show_error("URL is required")
            return
        
        if not re.match(r'^https?://[a-z2-7]{56}\.onion/?$', url):
            self.show_error("Invalid .onion URL format")
            return
        
        if self.callback:
            self.callback({
                "name": name,
                "url": url
            }, self.bookmark)
        
        self.destroy()
    
    def on_delete(self, button):
        if self.callback:
            self.callback(None, self.bookmark)
        self.destroy()
    
    def show_error(self, message):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Validation Error",
            body=message
        )
        dialog.add_response("ok", "OK")
        dialog.present()

class ModernTorLauncher(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Tor Launcher")
        self.set_default_size(900, 700)
        
        # Apply CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Clipboard
        self.clipboard = Gdk.Display.get_default().get_clipboard()
        
        # Bookmarks storage
        self.config_dir = Path.home() / ".config" / "tor-launcher"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.bookmarks_file = self.config_dir / "bookmarks.json"
        self.bookmarks = self.load_bookmarks()
        
        # Main layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Overlay for toast notifications
        self.overlay = Gtk.Overlay()
        self.overlay.set_child(self.main_box)
        self.set_content(self.overlay)
        
        # Header bar with theme toggle
        self.header = Adw.HeaderBar()
        self.main_box.append(self.header)
        
        # Theme switcher
        self.theme_btn = Gtk.ToggleButton()
        self.theme_btn.set_icon_name("weather-clear-night-symbolic")
        self.theme_btn.connect("toggled", self.on_theme_toggle)
        self.header.pack_end(self.theme_btn)
        
        # Add button
        self.add_btn = Gtk.Button.new_from_icon_name("list-add-symbolic")
        self.add_btn.connect("clicked", self.show_add_dialog)
        self.header.pack_end(self.add_btn)
        
        # Search bar
        self.search_bar = Gtk.SearchEntry(placeholder_text="Search bookmarks...")
        self.search_bar.add_css_class("search-bar")
        self.search_bar.connect("search-changed", self.on_search)
        self.main_box.append(self.search_bar)
        
        # Scrolled window for bookmarks
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.main_box.append(self.scrolled)
        
        # Flow box with nice spacing
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_max_children_per_line(5)
        self.flow.set_column_spacing(12)
        self.flow.set_row_spacing(12)
        self.flow.set_margin_start(12)
        self.flow.set_margin_end(12)
        self.flow.set_margin_bottom(12)
        self.scrolled.set_child(self.flow)
        
        # Empty state container
        self.empty_state = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, 
                                 spacing=12, valign=Gtk.Align.CENTER)
        self.empty_state.add_css_class("empty-state")
        empty_icon = Gtk.Image.new_from_icon_name("bookmark-missing-symbolic")
        empty_icon.set_pixel_size(64)
        self.empty_state.append(empty_icon)
        empty_label = Gtk.Label(label="No bookmarks yet\nClick + to add one")
        self.empty_state.append(empty_label)
        
        # Right-click menu actions
        self.edit_action = Gio.SimpleAction.new("edit", None)
        self.edit_action.connect("activate", self.on_edit_action)
        self.add_action(self.edit_action)
        
        self.delete_action = Gio.SimpleAction.new("delete", None)
        self.delete_action.connect("activate", self.on_delete_action)
        self.add_action(self.delete_action)
        
        # Load bookmarks
        self.refresh_bookmarks()
        
        # Show empty state if no bookmarks
        if not self.bookmarks:
            self.flow.insert(self.empty_state, -1)
    
    def load_bookmarks(self):
        try:
            if self.bookmarks_file.exists():
                with open(self.bookmarks_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return []
    
    def save_bookmarks(self):
        with open(self.bookmarks_file, 'w') as f:
            json.dump(self.bookmarks, f, indent=2)
    
    def refresh_bookmarks(self):
        # Clear existing
        while self.flow.get_first_child():
            self.flow.remove(self.flow.get_first_child())
        
        # Show empty state if no bookmarks
        if not self.bookmarks:
            self.flow.insert(self.empty_state, -1)
            return
        
        # Add all bookmarks
        for site in self.bookmarks:
            card = BookmarkCard(site["name"])
            card.connect("clicked", self.on_card_clicked, site)
            
            # Right click menu
            gesture = Gtk.GestureClick(button=3)
            gesture.connect("pressed", self.on_card_right_click, site)
            card.add_controller(gesture)
            
            self.flow.append(card)
    
    def on_card_clicked(self, button, site):
        self.clipboard.set(site["url"])
        self.show_toast(f"Copied: {site['url']}")
    
    def on_card_right_click(self, gesture, n_press, x, y, site):
        # Store the selected site
        self.selected_site = site
        
        # Create and show the popover menu
        menu = Gio.Menu()
        menu.append("Edit", "win.edit")
        menu.append("Delete", "win.delete")
        
        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu)
        popover.set_parent(gesture.get_widget())
        popover.set_position(Gtk.PositionType.BOTTOM)
        popover.popup()
    
    def on_edit_action(self, action, param):
        if hasattr(self, 'selected_site'):
            self.show_edit_dialog(self.selected_site)
            del self.selected_site
    
    def on_delete_action(self, action, param):
        if hasattr(self, 'selected_site'):
            self.show_delete_dialog(self.selected_site)
            del self.selected_site
    
    def show_add_dialog(self, button):
        dialog = AddEditDialog(self)
        dialog.callback = self.on_bookmark_modified
        dialog.present()
    
    def show_edit_dialog(self, site):
        dialog = AddEditDialog(self, site)
        dialog.callback = self.on_bookmark_modified
        dialog.present()
    
    def show_delete_dialog(self, site):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Delete Bookmark?",
            body=f"Are you sure you want to delete '{site['name']}'?"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", lambda d, r: self.on_delete_response(d, r, site))
        dialog.present()
    
    def on_delete_response(self, dialog, response, site):
        if response == "delete":
            try:
                self.bookmarks.remove(site)
                self.save_bookmarks()
                self.refresh_bookmarks()
                self.show_toast("Bookmark deleted")
            except ValueError:
                self.show_toast("Error: Bookmark not found")
        dialog.destroy()
    
    def on_bookmark_modified(self, bookmark, original):
        if bookmark:  # Add or update
            if original:  # Update
                index = self.bookmarks.index(original)
                self.bookmarks[index] = bookmark
                self.show_toast("Bookmark updated")
            else:  # Add new
                self.bookmarks.append(bookmark)
                self.show_toast("Bookmark added")
        else:  # Delete
            self.bookmarks.remove(original)
            self.show_toast("Bookmark deleted")
        
        self.save_bookmarks()
        self.refresh_bookmarks()
    
    def on_search(self, entry):
        text = entry.get_text().lower()
        for i in range(len(self.bookmarks)):
            child = self.flow.get_child_at_index(i)
            if child:
                site = self.bookmarks[i]
                visible = text in site["name"].lower() or text in site["url"].lower()
                child.set_visible(visible)
    
    def on_theme_toggle(self, button):
        style_manager = Adw.StyleManager.get_default()
        if button.get_active():
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            button.set_icon_name("weather-clear-symbolic")
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            button.set_icon_name("weather-clear-night-symbolic")
    
    def show_toast(self, message):
        toast = ModernToast(message)
        self.overlay.add_overlay(toast)
        toast.show()

class TorLauncherApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.example.TorLauncher',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
    
    def do_activate(self):
        win = ModernTorLauncher(application=self)
        win.present()

if __name__ == "__main__":
    app = TorLauncherApp()
    app.run(None)