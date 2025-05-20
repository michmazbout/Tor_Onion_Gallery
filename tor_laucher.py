import gi
import json
import os
import subprocess
from pathlib import Path
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, GdkPixbuf, Gdk

class AddEditBookmarkDialog(Adw.Window):
    def __init__(self, parent, callback, bookmark=None):
        super().__init__(title="Edit Bookmark" if bookmark else "Add New Bookmark")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(400, 300)
        self.callback = callback
        self.bookmark = bookmark
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                     margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        
        self.name_entry = Gtk.Entry(placeholder_text="Site Name")
        if bookmark:
            self.name_entry.set_text(bookmark["name"])
        box.append(self.name_entry)
        
        self.url_entry = Gtk.Entry(placeholder_text="Onion URL (e.g., http://example.onion)")
        if bookmark:
            self.url_entry.set_text(bookmark["url"])
        box.append(self.url_entry)
        
        icon_button = Gtk.Button(label="Select Icon")
        self.icon_path_label = Gtk.Label(label="No icon selected")
        self.icon_path = bookmark["icon_path"] if bookmark else None
        if self.icon_path:
            self.icon_path_label.set_label(os.path.basename(self.icon_path))
        
        def on_icon_clicked(button):
            dialog = Gtk.FileChooserNative.new(
                "Choose Icon",
                self,
                Gtk.FileChooserAction.OPEN,
                "Open",
                "Cancel"
            )
            filter = Gtk.FileFilter()
            filter.set_name("Image files")
            filter.add_mime_type("image/*")
            dialog.add_filter(filter)
            dialog.connect("response", self.on_file_chooser_response)
            dialog.show()
        
        icon_button.connect("clicked", on_icon_clicked)
        box.append(icon_button)
        box.append(self.icon_path_label)
        
        action_buttons = Gtk.Box(spacing=6)
        if bookmark:
            delete_button = Gtk.Button(label="Delete", css_classes=["destructive-action"])
            delete_button.connect("clicked", self.on_delete_clicked)
            action_buttons.append(delete_button)
        
        save_button = Gtk.Button(label="Save", css_classes=["suggested-action"])
        save_button.connect("clicked", self.on_save_clicked)
        action_buttons.append(save_button)
        
        box.append(action_buttons)
        self.set_content(box)
    
    def on_file_chooser_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            self.icon_path = dialog.get_file().get_path()
            self.icon_path_label.set_label(os.path.basename(self.icon_path))
        dialog.destroy()
    
    def on_save_clicked(self, button):
        name = self.name_entry.get_text()
        url = self.url_entry.get_text()
        if name and url:
            self.callback({
                "name": name,
                "url": url,
                "icon_path": self.icon_path
            }, self.bookmark)
            self.destroy()
    
    def on_delete_clicked(self, button):
        self.callback(None, self.bookmark)
        self.destroy()

class OnionWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Tor Site Launcher")
        self.set_default_size(800, 600)
        
        # Clipboard setup
        self.clipboard = Gdk.Display.get_default().get_clipboard()
        
        # Storage setup
        self.config_dir = Path.home() / ".config" / "tor-launcher"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.bookmarks_file = self.config_dir / "bookmarks.json"
        self.bookmarks = self.load_bookmarks()
        
        # Main layout
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        # Header bar with add button
        self.header = Adw.HeaderBar()
        self.add_button = Gtk.Button.new_from_icon_name("list-add-symbolic")
        self.add_button.connect("clicked", self.show_add_dialog)
        self.header.pack_end(self.add_button)
        self.box.append(self.header)
        
        # Search
        self.search = Gtk.SearchEntry(placeholder_text="Search onion sites...")
        self.search.connect("search-changed", self.on_search)
        self.box.append(self.search)
        
        # Flow box for sites
        self.flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE)
        self.flow.set_max_children_per_line(3)
        self.flow.set_homogeneous(True)
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_child(self.flow)
        self.box.append(self.scrolled)
        
        # Load bookmarks
        self.refresh_bookmarks()
        self.set_content(self.box)
    
    def load_bookmarks(self):
        if self.bookmarks_file.exists():
            try:
                with open(self.bookmarks_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_bookmarks(self):
        with open(self.bookmarks_file, 'w') as f:
            json.dump(self.bookmarks, f)
    
    def refresh_bookmarks(self):
        while self.flow.get_first_child():
            self.flow.remove(self.flow.get_first_child())
        
        for site in self.bookmarks:
            self.add_bookmark_card(site)
    
    def add_bookmark_card(self, site):
        card = Gtk.Button()
        card.set_size_request(200, 150)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        # Icon (custom or default)
        icon = Gtk.Image()
        if site.get("icon_path") and os.path.exists(site["icon_path"]):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(site["icon_path"], 48, 48)
                icon.set_from_pixbuf(pixbuf)
            except:
                icon.set_from_icon_name("applications-internet")
                icon.set_pixel_size(48)
        else:
            icon.set_from_icon_name("applications-internet")
            icon.set_pixel_size(48)
        
        box.append(icon)
        box.append(Gtk.Label(label=site["name"]))
        card.set_child(box)
        
        # Click handlers
        gesture = Gtk.GestureClick()
        gesture.connect("pressed", self.on_card_clicked, site)
        card.add_controller(gesture)
        
        # Right-click menu
        menu_gesture = Gtk.GestureClick(button=3)
        menu_gesture.connect("pressed", self.on_card_right_click, site)
        card.add_controller(menu_gesture)
        
        self.flow.append(card)
    
    def on_card_clicked(self, gesture, n_press, x, y, site):
        if gesture.get_current_button() == 1:  # Left click
            self.clipboard.set(site["url"])
            self.show_toast(f"Copied: {site['url']}")
    
    def on_card_right_click(self, gesture, n_press, x, y, site):
        menu = Gio.Menu()
        menu.append("Edit", "edit")
        menu.append("Delete", "delete")
        
        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu)
        popover.set_parent(gesture.get_widget())
        popover.set_position(Gtk.PositionType.BOTTOM)
        
        def on_edit(*args):
            self.show_edit_dialog(site)
            popover.popdown()
        
        def on_delete(*args):
            self.bookmarks.remove(site)
            self.save_bookmarks()
            self.refresh_bookmarks()
            popover.popdown()
        
        edit_action = Gio.SimpleAction.new("edit", None)
        edit_action.connect("activate", on_edit)
        self.add_action(edit_action)
        
        delete_action = Gio.SimpleAction.new("delete", None)
        delete_action.connect("activate", on_delete)
        self.add_action(delete_action)
        
        popover.popup()
    
    def show_add_dialog(self, button):
        def callback(bookmark, _):
            if bookmark:
                self.bookmarks.append(bookmark)
                self.save_bookmarks()
                self.refresh_bookmarks()
        
        dialog = AddEditBookmarkDialog(self, callback)
        dialog.present()
    
    def show_edit_dialog(self, bookmark):
        def callback(updated_bookmark, original_bookmark):
            if updated_bookmark:  # Save
                index = self.bookmarks.index(original_bookmark)
                self.bookmarks[index] = updated_bookmark
            else:  # Delete
                self.bookmarks.remove(original_bookmark)
            self.save_bookmarks()
            self.refresh_bookmarks()
        
        dialog = AddEditBookmarkDialog(self, callback, bookmark)
        dialog.present()
    
    def on_search(self, entry):
        text = entry.get_text().lower()
        for child in self.flow.get_children():
            label = child.get_child().get_children()[1]
            child.set_visible(text in label.get_text().lower())
    
    def show_toast(self, message):
        toast = Adw.Toast.new(message)
        toast.set_timeout(2)  # 2 seconds
        self.add_toast(toast)

class OnionApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.example.OnionLauncher')
    
    def do_activate(self):
        win = OnionWindow(application=self)
        win.present()

app = OnionApp()
app.run(None)