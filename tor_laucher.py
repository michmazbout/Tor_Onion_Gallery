import gi
import json
import os
import subprocess
from pathlib import Path
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, GdkPixbuf

class AddBookmarkDialog(Adw.Window):
    def __init__(self, parent, callback):
        super().__init__(title="Add New Bookmark")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(400, 300)
        self.callback = callback
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, 
                     margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        
        self.name_entry = Gtk.Entry(placeholder_text="Site Name")
        box.append(self.name_entry)
        
        self.url_entry = Gtk.Entry(placeholder_text="Onion URL (e.g., http://example.onion)")
        box.append(self.url_entry)
        
        icon_button = Gtk.Button(label="Select Icon")
        self.icon_path_label = Gtk.Label(label="No icon selected")
        self.icon_path = None
        
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
        
        add_button = Gtk.Button(label="Add Bookmark")
        add_button.connect("clicked", self.on_add_clicked)
        box.append(add_button)
        
        self.set_content(box)
    
    def on_file_chooser_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            self.icon_path = dialog.get_file().get_path()
            self.icon_path_label.set_label(os.path.basename(self.icon_path))
        dialog.destroy()
    
    def on_add_clicked(self, button):
        name = self.name_entry.get_text()
        url = self.url_entry.get_text()
        
        if name and url:
            self.callback({
                "name": name,
                "url": url,
                "icon_path": self.icon_path
            })
            self.destroy()

class OnionWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Tor Site Launcher")
        self.set_default_size(800, 600)
        
        self.config_dir = Path.home() / ".config" / "tor-launcher"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.bookmarks_file = self.config_dir / "bookmarks.json"
        self.bookmarks = self.load_bookmarks()
        
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        
        self.header = Adw.HeaderBar()
        self.add_button = Gtk.Button.new_from_icon_name("list-add-symbolic")
        self.add_button.connect("clicked", self.show_add_dialog)
        self.header.pack_end(self.add_button)
        self.box.append(self.header)
        
        self.search = Gtk.SearchEntry(placeholder_text="Search onion sites...")
        self.search.connect("search-changed", self.on_search)  # Corrected method name
        self.box.append(self.search)
        
        self.flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE)
        self.flow.set_max_children_per_line(3)
        self.flow.set_homogeneous(True)
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_child(self.flow)
        self.box.append(self.scrolled)
        
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
        card.connect("clicked", self.open_tor, site["url"])
        
        gesture = Gtk.GestureClick(button=3)
        gesture.connect("pressed", self.on_card_right_click, site)
        card.add_controller(gesture)
        
        self.flow.append(card)
    
    def show_add_dialog(self, button):
        def callback(bookmark):
            self.bookmarks.append(bookmark)
            self.save_bookmarks()
            self.refresh_bookmarks()
        
        dialog = AddBookmarkDialog(self, callback)
        dialog.present()
    
    def on_card_right_click(self, gesture, n_press, x, y, site):
        menu = Gio.Menu()
        menu.append("Delete", "delete")
        
        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu)
        popover.set_parent(gesture.get_widget())
        popover.set_position(Gtk.PositionType.BOTTOM)
        
        def on_delete(*args):
            self.bookmarks = [b for b in self.bookmarks if b != site]
            self.save_bookmarks()
            self.refresh_bookmarks()
            popover.popdown()
        
        action = Gio.SimpleAction.new("delete", None)
        action.connect("activate", on_delete)
        self.add_action(action)
        
        popover.popup()
    
    def open_tor(self, button, url):
        """Improved Tor Browser launcher that opens URLs in existing instances"""
        attempts = [
            ["xdg-open", url],  # First try the standard way
            ["torbrowser-launcher", "--", url],
            ["flatpak", "run", "com.github.micahflee.torbrowser-launcher", url],
            [os.path.expanduser("~/tor-browser/Browser/start-tor-browser"), url]
        ]
        
        env = os.environ.copy()
        env["MOZ_ENABLE_WAYLAND"] = "1"
        
        for cmd in attempts:
            try:
                result = subprocess.run(
                    cmd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=5
                )
                
                if "already running" in result.stderr.lower():
                    subprocess.Popen(
                        ["xdg-open", url],
                        env=env,
                        start_new_session=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    return
                
                if result.returncode == 0:
                    return
                    
            except subprocess.TimeoutExpired:
                continue
            except Exception as e:
                print(f"Attempt failed ({cmd}): {e}")
                continue
        
        try:
            subprocess.Popen(
                ["xdg-open", url],
                env=env,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            self.show_error_dialog(
                "Tor Browser Error",
                f"Could not open URL. Error: {str(e)}"
            )
    
    def on_search(self, entry):  # Correctly named method
        text = entry.get_text().lower()
        for child in self.flow.get_children():
            label = child.get_child().get_children()[1]
            child.set_visible(text in label.get_text().lower())
    
    def show_error_dialog(self, heading, body):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=heading,
            body=body
        )
        dialog.add_response("ok", "_OK")
        dialog.present()

class OnionApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.example.OnionLauncher')
    
    def do_activate(self):
        win = OnionWindow(application=self)
        win.present()

app = OnionApp()
app.run(None)