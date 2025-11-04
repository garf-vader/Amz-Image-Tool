# Building ImageTool Executable

## Prerequisites

1. Install PyInstaller:
   ```powershell
   pip install pyinstaller
   ```

2. Ensure all dependencies are installed:
   ```powershell
   pip install -r requirements.txt
   ```

## Build Methods

### Method 1: Using build.py (Recommended)

The simplest method - automatically handles everything:

```powershell
python build.py
```

This will:
- Clean previous build artifacts
- Build the executable with all dependencies
- Create build information
- Place the executable in `dist/ImageTool.exe`

### Method 2: Using the spec file

For more control over the build process:

```powershell
pyinstaller ImageTool.spec
```

### Method 3: Manual PyInstaller command

If you want to customize the build:

```powershell
pyinstaller --name=ImageTool --onefile --windowed ^
  --hidden-import=colour_sorter --hidden-import=color_phase ^
  --hidden-import=order_phase --hidden-import=front_image ^
  --hidden-import=amz_rename --hidden-import=pt_order ^
  --hidden-import=ui_utils --hidden-import=logic_utils ^
  combined_ui.py
```

## After Building

1. Navigate to the `dist/` folder
2. Copy `sku2asin.csv` to the same folder as `ImageTool.exe`
3. Run `ImageTool.exe`

## Build Output

After building, you'll find:
- `dist/ImageTool.exe` - The standalone executable
- `dist/BUILD_INFO.txt` - Build information
- `build/` - Temporary build files (can be deleted)
- `ImageTool.spec` - PyInstaller configuration

## Troubleshooting

### "PyInstaller not found"
Install it: `pip install pyinstaller`

### Missing modules at runtime
Add them to `hiddenimports` in `ImageTool.spec` or `build.py`

### Executable is too large
The exe includes Python, PyQt5, and PIL. Typical size: 30-50 MB.
To reduce size, consider using `--onedir` instead of `--onefile`.

### Antivirus flags the executable
This is common with PyInstaller executables. You may need to:
- Add an exception in your antivirus
- Sign the executable with a code signing certificate

## Distribution

To distribute the application:

1. Copy from `dist/`:
   - `ImageTool.exe`
   - `sku2asin.csv`

2. Users need:
   - Windows 10 or later
   - No Python installation required
   - The executable creates `Outputs/` folder automatically

## Clean Build

To start fresh:

```powershell
# Remove all build artifacts
Remove-Item -Recurse -Force build, dist
Remove-Item ImageTool.spec
```

Or simply run:
```powershell
python build.py
```
(It automatically cleans before building)
