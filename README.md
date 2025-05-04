# CDDA-Tileset-Viewer

A simple tool for previewing tilesets for Cataclysm: Dark Days Ahead.

This tool allows you to easily view and browse different tilesets for the game Cataclysm: Dark Days Ahead, helping you to compare and choose your preferred visual style.

## Screenshot

![Capture](https://github.com/user-attachments/assets/9c34b25a-d43f-4597-b7e7-3f8842b4e297)

## How to Use

### Installation

You have two options for installation:

1.  **Download the executable:**
    * Simply download the latest V1.0 executable.
    * Run the downloaded executable file.

2.  **Run from source:**
    * Clone the repository:
        ```bash
        git clone [https://github.com/Bzver/CDDA-Tileset-Viewer.git](https://github.com/your-username/CDDA-Tileset-Viewer.git)
        ```
    * Navigate to the cloned directory:
        ```bash
        cd CDDA-Tileset-Viewer
        ```
    * Make sure you have Python installed.
    * Run the script:
        ```bash
        python tile_viewer.py
        ```

### Running the Viewer

You can load the tileset in two ways:

1.  **Load from CDDA folder:**
    * Select the main Cataclysm: Dark Days Ahead game folder. The viewer will attempt to find the installed tilesets within the game's directory structure.

2.  **Load from `tileset_config.json`:**
    * Navigate to the specific tileset's folder you want to preview.
    * Select the `tileset_config.json` file located **inside** that tileset's folder.
  
## Known Issues

* The "PenAndPaper" overmap tileset currently cannot be viewed.
* Only the fg tiles can be displayed.



