import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
import json
from PIL import Image, ImageTk
import os

class GraphicsPackSelectionDialog(tk.Toplevel):
    def __init__(self, parent, graphics_packs):
        super().__init__(parent)
        self.title("Select Graphics Pack")
        self.transient(parent)
        self.grab_set()

        self.result = None

        label = tk.Label(self, text="Select a graphics pack:")
        label.pack(pady=10)

        # Frame for listbox and scrollbar
        self.list_frame = tk.Frame(self)
        self.list_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(self.list_frame)
        for pack in graphics_packs:
            self.listbox.insert(tk.END, pack)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        self.listbox.bind("<Double-1>", self.on_double_click)

        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)

        select_button = tk.Button(button_frame, text="Select", command=self.on_select_button)
        select_button.pack(side=tk.LEFT, padx=5)

        cancel_button = tk.Button(button_frame, text="Cancel", command=self.on_cancel_button)
        cancel_button.pack(side=tk.LEFT, padx=5)

    def on_select(self, event):
        # Enable select button if an item is selected
        if self.listbox.curselection():
            pass # Button is always enabled now

    def on_double_click(self, event):
        self.on_select_button()

    def on_select_button(self):
        selected_index = self.listbox.curselection()
        if selected_index:
            self.result = self.listbox.get(selected_index[0])
            self.destroy()
        else:
            messagebox.showinfo("Info", "Please select a graphics pack.")

    def on_cancel_button(self):
        self.result = None
        self.destroy()

    def show(self):
        self.wait_window()
        return self.result
class TileViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CDDA Tile Viewer --- By Bzver")

        self.tile_config = None
        self.tile_images = {} # This will now be used as a cache for currently displayed images
        self.tiles_data = {} # Stores parsed tile data keyed by tile_id
        self.tiles_by_file = {} # Stores tile_ids grouped by file_name
        self.displayed_photos = [] # List to hold PhotoImage references
        self.image_sprite_ranges = [] # To store (file_name, start_index, end_index, sprite_width, sprite_height)
        self.base_dir = None # Store the base directory of the config file
        self.zoom_level = 1.0 # Initial zoom level
        self.current_tile_id = None # Store the currently displayed tile ID

        # GUI Elements
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(pady=10) # Pack the button frame at the top

        self.load_cdda_button = tk.Button(self.button_frame, text="Load from CDDA Folder", command=self.load_from_cdda)
        self.load_cdda_button.pack(side=tk.LEFT, padx=5)

        self.load_button = tk.Button(self.button_frame, text="Load tile_config.json", command=self.load_config)
        self.load_button.pack(side=tk.LEFT, padx=5)


        # Frame for zoom controls
        self.zoom_frame = tk.Frame(root)
        self.zoom_frame.pack(pady=5)
        self.zoom_frame.pack_forget() # Initially hide the zoom frame

        self.zoom_label = tk.Label(self.zoom_frame, text="Zoom:")
        self.zoom_label.pack(side=tk.LEFT, padx=5)

        self.zoom_slider = ttk.Scale(
            self.zoom_frame,
            from_=0.1, # Minimum zoom level
            to=5.0, # Maximum zoom level
            orient=tk.HORIZONTAL,
            command=self.on_zoom_slide
        )
        self.zoom_slider.set(self.zoom_level) # Set initial value
        self.zoom_slider.pack(side=tk.LEFT, padx=5)

        self.extract_button = tk.Button(self.zoom_frame, text="Extract Tile", command=self.extract_tile)
        self.extract_button.pack(side=tk.LEFT, padx=5)

        # Frame for search controls
        self.search_frame = tk.Frame(root)
        self.search_frame.pack(pady=5)
        self.search_frame.pack_forget() # Initially hide the search frame

        self.search_label = tk.Label(self.search_frame, text="Search Tile ID:")
        self.search_label.pack(side=tk.LEFT, padx=5)

        self.search_entry = tk.Entry(self.search_frame)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<Return>", self.search_tiles) # Bind Enter key

        self.search_button = tk.Button(self.search_frame, text="Search", command=self.search_tiles)
        self.search_button.pack(side=tk.LEFT, padx=5)

        self.clear_search_button = tk.Button(self.search_frame, text="Clear Search", command=self.clear_search)
        self.clear_search_button.pack(side=tk.LEFT, padx=5)


        # Frame for the Treeview and Canvas
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Treeview for displaying tile IDs grouped by file
        self.tree_frame = tk.Frame(self.main_frame)
        self.tree_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.tree = ttk.Treeview(self.tree_frame, columns=("ID"), show="tree headings")
        self.tree.heading("#0", text="Image File")
        self.tree.heading("ID", text="Tile ID")
        self.tree.pack(side=tk.LEFT, fill=tk.Y)

        self.tree_scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scrollbar.set)
        self.tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind selection event
        self.tree.bind("<<TreeviewSelect>>", self.on_tile_select)

        # Canvas for displaying the selected tile
        self.canvas = tk.Canvas(self.main_frame, bg="gray")
        self.canvas.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=10)

        # Initially hide the main frame
        self.main_frame.pack_forget()


    def load_config(self):
        file_path = filedialog.askopenfilename(
            initialdir=".",
            title="Select tile_config.json",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*"))
        )
        if not file_path:
            return

        try:
            with open(file_path, 'r') as f:
                self.tile_config = json.load(f)
            messagebox.showinfo("Success", "tile_config.json loaded successfully.")
            self.base_dir = os.path.dirname(file_path) # Store base directory
            self.parse_config()
            self.populate_treeview()
            self.main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10) # Show main frame
            self.zoom_frame.pack(pady=5) # Show zoom frame
            self.search_frame.pack(pady=5) # Show zoom frame

        except Exception as e:
            messagebox.showerror("Error loading config", str(e))
            self.tile_config = None
            self.tile_images = {}
            self.tiles_data = {}
            self.tiles_by_file = {}
            self.image_sprite_ranges = []
            self.base_dir = None
            self.main_frame.pack_forget() # Hide main frame on error


    def load_from_cdda(self):
        cdda_folder = filedialog.askdirectory(
            initialdir=".",
            title="Select CDDA Installation Folder"
        )
        if not cdda_folder:
            return

        gfx_path = os.path.join(cdda_folder, "gfx")
        if not os.path.isdir(gfx_path):
            messagebox.showerror("Error", f"Could not find 'gfx' folder in {cdda_folder}")
            return

        graphics_packs = [d for d in os.listdir(gfx_path) if os.path.isdir(os.path.join(gfx_path, d))]

        if not graphics_packs:
            messagebox.showinfo("Info", f"No graphics packs found in {gfx_path}")
            return

        dialog = GraphicsPackSelectionDialog(self.root, graphics_packs)
        selected_pack = dialog.show()

        if selected_pack:
            tile_config_path = os.path.join(gfx_path, selected_pack, "tile_config.json")
            if not os.path.exists(tile_config_path):
                messagebox.showerror("Error", f"Could not find tile_config.json in {os.path.join(gfx_path, selected_pack)}")
                return

            # Load the selected tile_config.json
            try:
                with open(tile_config_path, 'r') as f:
                    self.tile_config = json.load(f)
                messagebox.showinfo("Success", f"tile_config.json loaded successfully from {selected_pack}.")
                self.base_dir = os.path.dirname(tile_config_path) # Store base directory of the loaded config
                self.parse_config()
                self.populate_treeview()
                self.main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10) # Show main frame
                self.zoom_frame.pack(pady=5) # Show zoom frame
                self.search_frame.pack(pady=5) # Show search frame

            except Exception as e:
                messagebox.showerror("Error loading config", str(e))
                self.tile_config = None
                self.tile_images = {}
                self.tiles_data = {}
                self.tiles_by_file = {}
                self.image_sprite_ranges = []
                self.base_dir = None
                self.main_frame.pack_forget() # Hide main frame on error


    def parse_config(self):
        self.tiles_data = {}
        self.tiles_by_file = {}
        self.tile_images = {} # Clear image cache
        self.image_sprite_ranges = []
        current_sprite_index = 0 # Global cumulative index

        if not self.tile_config or "tiles-new" not in self.tile_config:
            return

        # First pass: Determine sprite index ranges without loading images
        for tile_set in self.tile_config.get("tiles-new", []):
            file_name = tile_set.get("file")
            if not file_name:
                continue

            # We need image dimensions to calculate sprite count, so we'll open it briefly
            image_path = os.path.join(self.base_dir, file_name)
            try:
                # Open image just to get dimensions, don't keep it in self.tile_images yet
                img = Image.open(image_path)
                try:
                    sprite_width = tile_set.get("sprite_width", self.tile_config["tile_info"][0]["width"])
                    sprite_height = tile_set.get("sprite_height", self.tile_config["tile_info"][0]["height"])

                    sprites_in_image = (img.width // sprite_width) * (img.height // sprite_height)
                    start_index = current_sprite_index
                    end_index = current_sprite_index + sprites_in_image - 1
                    self.image_sprite_ranges.append((file_name, start_index, end_index, sprite_width, sprite_height))
                    current_sprite_index = end_index + 1
                finally:
                    img.close() # Explicitly close the image file

            except FileNotFoundError:
                print(f"Warning: Image file not found: {image_path}")
                # Still add a range entry so subsequent indices are correct
                self.image_sprite_ranges.append((file_name, current_sprite_index, current_sprite_index -1, 0, 0)) # Invalid range
            except Exception as e:
                print(f"Warning: Could not process image {image_path} for dimensions: {e}")
                self.image_sprite_ranges.append((file_name, current_sprite_index, current_sprite_index -1, 0, 0)) # Invalid range


        # Second pass: Parse tile data using global sprite indices
        for tile_set in self.tile_config.get("tiles-new", []):
             file_name = tile_set.get("file")
             if not file_name:
                 continue

             if "tiles" in tile_set:
                for tile_entry in tile_set.get("tiles", []):
                    tile_ids = tile_entry.get("id")
                    if not tile_ids:
                        continue

                    if not isinstance(tile_ids, list):
                        tile_ids = [tile_ids]

                    fg_sprites_raw = tile_entry.get("fg")

                    if fg_sprites_raw is not None:
                        fg_list = []
                        if isinstance(fg_sprites_raw, list):
                            for item in fg_sprites_raw:
                                if isinstance(item, int):
                                    fg_list.append({"sprite": item})
                                elif isinstance(item, dict):
                                    fg_list.append(item)
                                else:
                                    print(f"Warning: Unexpected type in fg list: {type(item)}")
                        elif isinstance(fg_sprites_raw, int):
                            fg_list = [{"sprite": fg_sprites_raw}]

                        for fg_entry in fg_list:
                            global_sprite_index = fg_entry.get("sprite")
                            if global_sprite_index is not None:
                                # Find which image this global index belongs to
                                found_image_info = None
                                for range_file_name, start, end, sprite_width, sprite_height in self.image_sprite_ranges:
                                    if start <= global_sprite_index <= end:
                                        found_image_info = (range_file_name, start, sprite_width, sprite_height) # Include start index
                                        break

                                if found_image_info:
                                    range_file_name, start_index, sprite_width, sprite_height = found_image_info

                                    # Calculate local sprite index within the image
                                    local_sprite_index = global_sprite_index - (start_index - 1)

                                    # Store all necessary info to crop later
                                    for tile_id in tile_ids:
                                        if tile_id not in self.tiles_data:
                                            self.tiles_data[tile_id] = []
                                        self.tiles_data[tile_id].append({
                                            "image": range_file_name, # Use the file name from the range info
                                            "global_sprite_index": global_sprite_index, # Store global index
                                            "sprite_width": sprite_width,
                                            "sprite_height": sprite_height,
                                            "type": "fg"
                                        })
                                        # Populate tiles_by_file
                                        if range_file_name not in self.tiles_by_file:
                                            self.tiles_by_file[range_file_name] = set() # Use a set to avoid duplicate tile IDs per file
                                        self.tiles_by_file[range_file_name].add(tile_id)

                                else:
                                    print(f"Warning: Global sprite index {global_sprite_index} is outside of any defined image range.")


    def populate_treeview(self, tiles_to_display=None):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Determine which tiles to display
        if tiles_to_display is None:
            tiles_data = self.tiles_by_file
        else:
            tiles_data = tiles_to_display

        # Populate the treeview
        for file_name, tile_ids in tiles_data.items():
            # Insert the file name as a parent node
            file_node = self.tree.insert("", "end", text=file_name, open=False)
            # Insert tile IDs as children under the file node
            for tile_id in sorted(list(tile_ids)): # Sort tile IDs alphabetically
                self.tree.insert(file_node, "end", text=tile_id, values=(tile_id,))


    def on_tile_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return

        # Get the first selected item (we'll only display one tile at a time for simplicity)
        selected_item = selected_items[0]
        item_text = self.tree.item(selected_item, "text")
        parent_item = self.tree.parent(selected_item)

        if parent_item: # It's a tile ID (child node)
            tile_id_to_display = item_text
            self.current_tile_id = tile_id_to_display # Store the current tile ID
            self.display_current_tile()
        # else: # It's a file name (parent node) - could implement displaying all tiles in a file here if needed
            # pass

    def zoom_in(self):
        self.zoom_level *= 1.25 # Increase zoom by 25%
        self.display_current_tile()

    def zoom_out(self):
        self.zoom_level /= 1.25 # Decrease zoom by 25%
        if self.zoom_level < 0.1: # Prevent zooming out too much
            self.zoom_level = 0.1
        self.display_current_tile()

    def display_current_tile(self):
        if self.current_tile_id:
            self.display_tile(self.current_tile_id)

    def extract_tile(self):
        if not self.current_displayed_image:
            messagebox.showinfo("Info", "No tile is currently displayed to extract.")
            return

        file_path = filedialog.asksaveasfilename(
            initialdir=".",
            title="Save Tile Image",
            defaultextension=".png",
            filetypes=(("PNG files", "*.png"), ("All files", "*.*"))
        )
        if not file_path:
            return

        try:
            self.current_displayed_image.save(file_path)
            messagebox.showinfo("Success", f"Tile image saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Error saving image", str(e))

    def on_zoom_slide(self, value):
        self.zoom_level = float(value)
        self.display_current_tile()

    def search_tiles(self, event=None): # Added event=None for binding
        search_term = self.search_entry.get().lower()
        if not search_term:
            self.populate_treeview() # If search term is empty, show all tiles
            return

        filtered_tiles_by_file = {}
        for file_name, tile_ids in self.tiles_by_file.items():
            filtered_ids = {tile_id for tile_id in tile_ids if search_term in tile_id.lower()}
            if filtered_ids:
                filtered_tiles_by_file[file_name] = filtered_ids

        self.populate_treeview(filtered_tiles_by_file)

    def clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.populate_treeview() # Show all tiles


    def display_tile(self, tile_id_to_display):
        self.canvas.delete("all")
        self.displayed_photos = [] # Clear previous images
        self.tile_images = {} # Clear image cache for display
        self.current_displayed_image = None # Clear previous combined image

        x_offset, y_offset = 10, 10
        max_row_height = 0
        combined_image_width = 0
        combined_image_height = 0
        sprite_images = [] # Store individual sprite images before combining

        sprites_to_display = self.tiles_data.get(tile_id_to_display, [])

        if not sprites_to_display:
            self.canvas.create_text(10, 10, text=f"Tile ID '{tile_id_to_display}' not found in parsed data.", anchor=tk.NW)
            return

        # First pass: Load and crop all sprites, calculate combined image size
        for sprite_info in sprites_to_display:
            image_name = sprite_info["image"]
            global_sprite_index = sprite_info["global_sprite_index"]
            sprite_width = sprite_info["sprite_width"]
            sprite_height = sprite_info["sprite_height"]

            # Load image only if not already in cache
            if image_name not in self.tile_images:
                image_path = os.path.join(self.base_dir, image_name)
                try:
                    img = Image.open(image_path).convert("RGBA")
                    self.tile_images[image_name] = img
                except FileNotFoundError:
                    print(f"Error: Image file not found for display: {image_path}")
                    continue
                except Exception as e:
                    print(f"Error loading image for display {image_path}: {e}")
                    continue

            img = self.tile_images.get(image_name)

            if img:
                try:
                    # Find the sprite range for this image to calculate local index
                    start_index = -1
                    for file_name, start, end, w, h in self.image_sprite_ranges:
                        if file_name == image_name:
                            start_index = start
                            break

                    if start_index != -1:
                        local_sprite_index = global_sprite_index - (start_index - 1)

                        # Calculate sprite grid position
                        sprites_per_row = img.width // sprite_width
                        row = (local_sprite_index - 1) // sprites_per_row
                        col = (local_sprite_index - 1) % sprites_per_row

                        # Calculate cropping coordinates (x1, y1, x2, y2)
                        x1 = col * sprite_width
                        y1 = row * sprite_height
                        x2 = x1 + sprite_width
                        y2 = y1 + sprite_height

                        # Ensure coordinates are within image bounds
                        if x1 >= 0 and y1 >= 0 and x2 <= img.width and y2 <= img.height:
                            # Crop the sprite from the image
                            sprite_img = img.crop((x1, y1, x2, y2))
                            sprite_images.append(sprite_img)

                            # Calculate combined image size (simple row layout)
                            combined_image_width += sprite_img.width + 20 # Add spacing
                            combined_image_height = max(combined_image_height, sprite_img.height)

                        else:
                            print(f"Warning: Calculated coordinates for global sprite index {global_sprite_index} ({image_name}) are out of bounds during display.")
                    else:
                         print(f"Error: Could not find sprite range for image {image_name} during display.")


                except Exception as e:
                    print(f"Error processing sprite for {tile_id_to_display}: {e}")

        # Create a blank image to paste sprites onto
        if sprite_images:
            self.current_displayed_image = Image.new("RGBA", (combined_image_width + 10, combined_image_height + 10)) # Add padding

            # Second pass: Paste sprites onto the combined image and display on canvas
            paste_x_offset = 10
            for sprite_img in sprite_images:
                 # Apply zoom to the sprite image before displaying and pasting
                if self.zoom_level != 1.0:
                    new_width = int(sprite_img.width * self.zoom_level)
                    new_height = int(sprite_img.height * self.zoom_level)
                    scaled_sprite_img = sprite_img.resize((new_width, new_height), Image.Resampling.NEAREST) # Use NEAREST for pixel art
                else:
                    scaled_sprite_img = sprite_img

                photo_img = ImageTk.PhotoImage(scaled_sprite_img)

                # Display the sprite on the canvas with offset
                self.canvas.create_image(x_offset , y_offset , image=photo_img, anchor=tk.NW)

                # Paste onto the combined image
                self.current_displayed_image.paste(sprite_img, (paste_x_offset, 10), sprite_img) # Paste original size for extraction
                paste_x_offset += sprite_img.width + 20

                # Keep a reference to the PhotoImage to prevent garbage collection
                self.displayed_photos.append(photo_img)

                # Adjust offset and max height based on scaled image size for canvas display
                x_offset += scaled_sprite_img.width + 20
                max_row_height = max(max_row_height, scaled_sprite_img.height + 25)

                # Move to the next row if needed (simple wrapping)
                if x_offset + scaled_sprite_img.width > self.canvas.winfo_width() and self.canvas.winfo_width() > 0:
                    x_offset = 10
                    y_offset += max_row_height
                    max_row_height = 0


if __name__ == "__main__":
    root = tk.Tk()
    app = TileViewerApp(root)
    root.mainloop()