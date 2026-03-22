"""
Setup script for Clip Swiper Web App
Run this to create all necessary files and folders
"""

from pathlib import Path
import shutil

def create_web_app_structure():
    """Create all necessary directories and copy template files"""
    
    base_dir = Path(__file__).parent
    print(f"Setting up in: {base_dir}\n")
    
    # Create directories
    dirs = [
        base_dir / 'templates',
        base_dir / 'static' / 'css',
        base_dir / 'static' / 'js'
    ]
    
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {dir_path}")
    
    # Check if template files exist
    template_file = base_dir / 'templates' / 'index.html'
    css_file = base_dir / 'static' / 'css' / 'style.css'
    js_file = base_dir / 'static' / 'js' / 'app.js'
    
    files_needed = []
    if not template_file.exists():
        files_needed.append('templates/index.html')
    if not css_file.exists():
        files_needed.append('static/css/style.css')
    if not js_file.exists():
        files_needed.append('static/js/app.js')
    
    if files_needed:
        print(f"\n⚠️  Missing files:")
        for f in files_needed:
            print(f"   - {f}")
        print(f"\nPlease download these files from the outputs folder")
        print(f"and place them in the correct directories.\n")
        return False
    
    print(f"\n✅ All files present!")
    print(f"\n{'='*60}")
    print(f"Setup complete! Run the app with:")
    print(f"python web_app.py")
    print(f"{'='*60}\n")
    return True

if __name__ == '__main__':
    create_web_app_structure()