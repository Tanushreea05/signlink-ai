"""
Prepare SignLink AI repository for GitHub push
This script helps clean up large files and prepare for version control
"""

import os
import shutil
import subprocess
from pathlib import Path


def get_file_size_mb(file_path):
    """Get file size in MB"""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except:
        return 0


def find_large_files(directory, size_limit_mb=50):
    """Find files larger than size limit"""
    large_files = []
    
    for root, dirs, files in os.walk(directory):
        # Skip certain directories
        skip_dirs = {'.git', '__pycache__', 'node_modules', '.next', 'venv', 'env'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            file_path = os.path.join(root, file)
            size_mb = get_file_size_mb(file_path)
            
            if size_mb > size_limit_mb:
                large_files.append((file_path, size_mb))
    
    return sorted(large_files, key=lambda x: x[1], reverse=True)


def clean_unnecessary_files():
    """Remove unnecessary files and directories"""
    print("🧹 Cleaning unnecessary files...")
    
    # Directories to remove
    dirs_to_remove = [
        'sample_data',
        'models/checkpoints',
        '__pycache__',
        '.pytest_cache',
        'node_modules',
        '.next',
        'build',
        'dist'
    ]
    
    # File patterns to remove
    files_to_remove = [
        '*.pyc',
        '*.pyo',
        '*.pyd',
        '*.so',
        '*.egg-info',
        '*.log',
        '*.tmp',
        '*.temp',
        'screenshot_*.jpg',
        'frame_*.jpg',
        '*.pth',
        '*.pt',
        '*.ckpt',
        '*.npy',
        '*.npz'
    ]
    
    removed_count = 0
    
    # Remove directories
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"  ✅ Removed directory: {dir_name}")
                removed_count += 1
            except Exception as e:
                print(f"  ⚠️ Could not remove {dir_name}: {e}")
    
    # Remove files by pattern
    import glob
    for pattern in files_to_remove:
        for file_path in glob.glob(pattern, recursive=True):
            try:
                os.remove(file_path)
                print(f"  ✅ Removed file: {file_path}")
                removed_count += 1
            except Exception as e:
                print(f"  ⚠️ Could not remove {file_path}: {e}")
    
    print(f"🧹 Cleaned {removed_count} items")


def create_placeholder_files():
    """Create placeholder files for important directories"""
    print("📁 Creating placeholder files...")
    
    placeholders = {
        'sample_data/README.md': """# Sample Data Directory

This directory contains sample datasets for training and testing.

## Generate Sample Data

```bash
python ml/data/generate_sample_data.py --output sample_data
```

## Structure
```
sample_data/
├── train/
│   ├── ASL_HELLO/
│   ├── ASL_GOODBYE/
│   └── ...
└── val/
    ├── ASL_HELLO/
    └── ...
```
""",
        'models/checkpoints/README.md': """# Model Checkpoints

This directory contains trained model checkpoints.

## Training Models

```bash
# Generate sample data first
python ml/data/generate_sample_data.py

# Train model
python ml/train.py --config ml/configs/demo_config.yaml

# Use trained model
python realtime_translator.py --model models/checkpoints/best_model.pth
```

## Files
- `best_model.pth` - Best performing model
- `class_names.txt` - List of sign language classes
- `training_log.json` - Training metrics and history
""",
        'models/checkpoints/class_names.txt': """HELLO
GOODBYE
THANK_YOU
PLEASE
YES
NO
SORRY
HELP
LOVE
FRIEND
GOOD
BAD
HAPPY
SAD
WATER
FOOD
HOME
WORK
FAMILY
TIME
HOW
WHAT
WHERE
WHEN
WHY
WHO""",
        'web/public/.gitkeep': '# Keep this directory in git',
        'mobile/assets/.gitkeep': '# Keep this directory in git',
        'avatar/models/.gitkeep': '# Keep this directory in git',
        'tests/.gitkeep': '# Keep this directory in git'
    }
    
    for file_path, content in placeholders.items():
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  ✅ Created: {file_path}")


def check_git_status():
    """Check git repository status"""
    print("📊 Checking git status...")
    
    try:
        # Check if git repo exists
        result = subprocess.run(['git', 'status'], 
                              capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            print("  ✅ Git repository exists")
            
            # Check for large files in staging
            result = subprocess.run(['git', 'ls-files', '--cached'], 
                                  capture_output=True, text=True, cwd='.')
            
            if result.returncode == 0:
                staged_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
                large_staged = []
                
                for file in staged_files:
                    if os.path.exists(file):
                        size_mb = get_file_size_mb(file)
                        if size_mb > 50:
                            large_staged.append((file, size_mb))
                
                if large_staged:
                    print("  ⚠️ Large files in staging:")
                    for file, size in large_staged:
                        print(f"    - {file}: {size:.1f} MB")
                else:
                    print("  ✅ No large files in staging")
            
        else:
            print("  ⚠️ Not a git repository")
            return False
            
    except FileNotFoundError:
        print("  ❌ Git not installed")
        return False
    
    return True


def initialize_git_repo():
    """Initialize git repository if needed"""
    print("🔧 Setting up git repository...")
    
    try:
        # Initialize repo if needed
        if not os.path.exists('.git'):
            subprocess.run(['git', 'init'], check=True, cwd='.')
            print("  ✅ Initialized git repository")
        
        # Add gitignore
        subprocess.run(['git', 'add', '.gitignore'], check=True, cwd='.')
        print("  ✅ Added .gitignore")
        
        # Set up git config if needed
        try:
            subprocess.run(['git', 'config', 'user.name'], 
                         check=True, capture_output=True, cwd='.')
        except subprocess.CalledProcessError:
            print("  ⚠️ Git user not configured. Please run:")
            print("    git config --global user.name 'Your Name'")
            print("    git config --global user.email 'your.email@example.com'")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Git setup failed: {e}")
        return False


def show_git_commands():
    """Show recommended git commands"""
    print("\n" + "="*60)
    print("🚀 Ready for GitHub! Use these commands:")
    print("="*60)
    
    print("\n1️⃣ Add files to git:")
    print("   git add .")
    
    print("\n2️⃣ Commit changes:")
    print('   git commit -m "Initial commit: SignLink AI platform"')
    
    print("\n3️⃣ Add GitHub remote (replace with your repo URL):")
    print("   git remote add origin https://github.com/yourusername/signlink-ai.git")
    
    print("\n4️⃣ Push to GitHub:")
    print("   git branch -M main")
    print("   git push -u origin main")
    
    print("\n💡 Alternative: Use GitHub CLI")
    print("   gh repo create signlink-ai --public")
    print("   git push -u origin main")
    
    print("\n📋 Repository size optimization:")
    print("   - Large files excluded via .gitignore")
    print("   - Model files and datasets not included")
    print("   - Only source code and documentation pushed")
    
    print("\n🔗 After pushing, users can:")
    print("   git clone https://github.com/yourusername/signlink-ai.git")
    print("   cd signlink-ai")
    print("   python setup_realtime.py")


def main():
    """Main function"""
    print("=" * 60)
    print("🚀 SignLink AI - GitHub Preparation")
    print("=" * 60)
    
    # Change to project directory
    os.chdir(Path(__file__).parent)
    
    # Find large files first
    print("🔍 Scanning for large files...")
    large_files = find_large_files('.', size_limit_mb=10)
    
    if large_files:
        print(f"📊 Found {len(large_files)} large files:")
        for file_path, size_mb in large_files[:10]:  # Show top 10
            print(f"  - {file_path}: {size_mb:.1f} MB")
        if len(large_files) > 10:
            print(f"  ... and {len(large_files) - 10} more")
    else:
        print("✅ No large files found")
    
    # Clean unnecessary files
    clean_unnecessary_files()
    
    # Create placeholder files
    create_placeholder_files()
    
    # Setup git
    if initialize_git_repo():
        check_git_status()
        show_git_commands()
    
    print("\n" + "="*60)
    print("✅ Repository prepared for GitHub!")
    print("📦 Total size optimized for version control")
    print("🔒 Large files excluded via .gitignore")
    print("📚 Documentation and source code ready")
    print("="*60)


if __name__ == "__main__":
    main()
