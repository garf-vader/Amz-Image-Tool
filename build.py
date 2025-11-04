#!/usr/bin/env python3
"""
Build script for creating a standalone executable of the Image Tool application.

This script uses PyInstaller to bundle combined_ui.py and all its dependencies
into a single executable for Windows.

Usage:
    python build.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def clean_build_artifacts():
    """Remove previous build artifacts."""
    artifacts = ['build', 'dist', '__pycache__']
    for artifact in artifacts:
        if os.path.exists(artifact):
            print(f"Removing {artifact}/")
            shutil.rmtree(artifact)
    
    # Remove spec file if it exists
    spec_file = 'combined_ui.spec'
    if os.path.exists(spec_file):
        print(f"Removing {spec_file}")
        os.remove(spec_file)


def build_executable():
    """Build the executable using PyInstaller."""
    
    # PyInstaller command with options
    cmd = [
        'pyinstaller',
        '--name=ImageTool',
        '--onefile',  # Create a single executable
        '--windowed',  # No console window (GUI app)
        '--icon=NONE',  # Add an icon file if you have one
        
        # Hidden imports for modules loaded dynamically
        '--hidden-import=colour_sorter',
        '--hidden-import=color_phase',
        '--hidden-import=order_phase',
        '--hidden-import=front_image',
        '--hidden-import=amz_rename',
        '--hidden-import=pt_order',
        '--hidden-import=fetch_sku2asin',
        '--hidden-import=ui_utils',
        '--hidden-import=logic_utils',
        '--hidden-import=undo',
        
        # PyQt5 imports
        '--hidden-import=PyQt5',
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtGui',
        '--hidden-import=PyQt5.QtWidgets',
        
        # PIL/Pillow imports
        '--hidden-import=PIL',
        '--hidden-import=PIL.Image',
        '--hidden-import=PIL._imaging',
        
        # Add data files
        '--add-data=sku2asin.csv;.' if os.path.exists('sku2asin.csv') else '',
        
        # Clean build
        '--clean',
        
        # Exclude unnecessary modules to reduce size
        '--exclude-module=matplotlib',
        '--exclude-module=numpy',
        '--exclude-module=pandas',
        '--exclude-module=scipy',
        '--exclude-module=IPython',
        '--exclude-module=jupyter',
        
        # Main script
        'combined_ui.py'
    ]
    
    # Filter out empty strings
    cmd = [arg for arg in cmd if arg]
    
    print("\n" + "="*60)
    print("Building ImageTool executable...")
    print("="*60)
    print(f"\nCommand: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("\n" + "="*60)
        print("✓ Build completed successfully!")
        print("="*60)
        print(f"\nExecutable location: {os.path.join('dist', 'ImageTool.exe')}")
        return True
    except subprocess.CalledProcessError as e:
        print("\n" + "="*60)
        print("✗ Build failed!")
        print("="*60)
        print(f"\nError: {e}")
        return False
    except FileNotFoundError:
        print("\n" + "="*60)
        print("✗ PyInstaller not found!")
        print("="*60)
        print("\nPlease install PyInstaller:")
        print("  pip install pyinstaller")
        return False


def create_build_info():
    """Create a build info file."""
    from datetime import datetime
    
    build_info = f"""Image Tool Build Information
{'='*50}
Build Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Python Version: {sys.version}
Platform: {sys.platform}

Executable: ImageTool.exe
Location: dist/ImageTool.exe

Notes:
- The executable includes all required dependencies
- sku2asin.csv should be in the same directory as the executable
- Outputs/ folder will be created in the same directory
"""
    
    with open('dist/BUILD_INFO.txt', 'w') as f:
        f.write(build_info)
    
    print("\n✓ Build info created: dist/BUILD_INFO.txt")


def main():
    """Main build process."""
    print("\n" + "="*60)
    print("Image Tool - Build Script")
    print("="*60)
    
    # Ensure we're in the correct directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    print(f"\nWorking directory: {os.getcwd()}")
    
    # Clean previous builds
    print("\n[1/3] Cleaning previous build artifacts...")
    clean_build_artifacts()
    
    # Build executable
    print("\n[2/3] Building executable with PyInstaller...")
    if not build_executable():
        sys.exit(1)
    
    # Create build info
    print("\n[3/3] Creating build information...")
    create_build_info()
    
    # Final instructions
    print("\n" + "="*60)
    print("Build Process Complete!")
    print("="*60)
    print("\nTo run the application:")
    print("  1. Navigate to: dist/")
    print("  2. Copy sku2asin.csv to the dist/ folder")
    print("  3. Run: ImageTool.exe")
    print("\nNote: The first run may take a few seconds to start.")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
