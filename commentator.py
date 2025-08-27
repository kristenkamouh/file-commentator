import os
import sys
import time
from pathlib import Path

def create_progress_bar(current, total, bar_length=50):
    """
    Create a visual progress bar
    
    Args:
        current (int): Current progress
        total (int): Total items
        bar_length (int): Length of the progress bar
    
    Returns:
        str: Formatted progress bar string
    """
    if total == 0:
        return "[" + "=" * bar_length + "] 100%"
    
    percent = float(current) / total
    filled_length = int(bar_length * percent)
    
    bar = "=" * filled_length + "-" * (bar_length - filled_length)
    percentage = int(percent * 100)
    
    return f"[{bar}] {percentage}% ({current}/{total})"

def count_files(directory_path, file_extensions=None, exclude_dirs=None):
    """
    Count total files to process for progress tracking
    """
    if exclude_dirs is None:
        exclude_dirs = ['.git', '__pycache__', '.vscode', 'node_modules', '.idea']
    
    count = 0
    directory = Path(directory_path)
    
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            file_path = Path(root) / file
            
            # Skip if file extensions are specified and this file doesn't match
            if file_extensions and file_path.suffix.lower() not in file_extensions:
                continue
            
            # Skip large files
            if file_path.stat().st_size > 10 * 1024 * 1024:
                continue
                
            count += 1
    
    return count

def add_comment_to_file(file_path, comment_block):
    """
    Add a comment block to the top of a file while preserving its content
    """
    try:
        # Read the original content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            original_content = file.read()
        
        # Check if the comment already exists to avoid duplicates
        if comment_block.strip() in original_content[:len(comment_block) + 50]:
            return "exists"
        
        # Write the comment block followed by the original content
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(comment_block + '\n' + original_content)
        
        return "success"
    
    except Exception as e:
        return f"error: {e}"

def process_directory(directory_path, comment_block, file_extensions=None, exclude_dirs=None):
    """
    Process all files in a directory and add comment blocks with progress bar
    """
    if exclude_dirs is None:
        exclude_dirs = ['.git', '__pycache__', '.vscode', 'node_modules', '.idea']
    
    directory = Path(directory_path)
    
    if not directory.exists():
        print(f"❌ Directory does not exist: {directory_path}")
        return
    
    if not directory.is_dir():
        print(f"❌ Path is not a directory: {directory_path}")
        return
    
    print(f"📂 Scanning directory: {directory_path}")
    print("🔍 Counting files...")
    
    total_files = count_files(directory_path, file_extensions, exclude_dirs)
    
    if total_files == 0:
        print("❌ No files found to process!")
        return
    
    print(f"📄 Found {total_files} files to process")
    print("🚀 Starting processing...\n")
    
    processed_count = 0
    skipped_count = 0
    error_count = 0
    current_file = 0
    
    # Walk through all files and subdirectories
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            file_path = Path(root) / file
            
            # Skip if file extensions are specified and this file doesn't match
            if file_extensions and file_path.suffix.lower() not in file_extensions:
                continue
            
            # Skip large files
            if file_path.stat().st_size > 10 * 1024 * 1024:
                skipped_count += 1
                current_file += 1
                continue
            
            current_file += 1
            
            # Update progress bar
            progress = create_progress_bar(current_file, total_files)
            filename = file_path.name[:30] + "..." if len(file_path.name) > 30 else file_path.name
            print(f"\r{progress} Processing: {filename}", end="", flush=True)
            
            result = add_comment_to_file(file_path, comment_block)
            
            if result == "success":
                processed_count += 1
            elif result == "exists":
                skipped_count += 1
            else:
                error_count += 1
            
            # Small delay for visual effect (remove in production if too slow)
            time.sleep(0.01)
    
    # Clear the progress line and show completion
    print(f"\r{create_progress_bar(total_files, total_files)}")
    print("\n" + "=" * 60)
    print("🎉 PROCESSING COMPLETE! 🎉")
    print("=" * 60)
    print(f"✅ Files processed successfully: {processed_count}")
    print(f"⏭️  Files skipped (already had comment): {skipped_count}")
    print(f"❌ Files with errors: {error_count}")
    print(f"📊 Total files examined: {current_file}")
    print("=" * 60)

def print_banner():
    """Print a nice banner for the tool"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    FILE COMMENT INSERTER                    ║
║                     v1.0 - Terminal Edition                 ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)

def main():
    print_banner()
    
    # Default comment block
    default_comment = """/*
this is a test comment for demonstration purposes
*/"""
    
    # Get directory path
    if len(sys.argv) > 1:
        directory_path = sys.argv[1]
        print(f"📁 Using directory from command line: {directory_path}")
    else:
        directory_path = input("📁 Enter directory path (or press Enter for current directory): ").strip()
        if not directory_path:
            directory_path = "."
            print("📁 Using current directory")
    
    # Resolve absolute path for display
    abs_path = os.path.abspath(directory_path)
    print(f"🎯 Target directory: {abs_path}")
    
    # Ask for custom comment (optional)
    print("\n" + "-" * 50)
    use_custom = input("✏️  Use custom comment? (y/n, default: n): ").strip().lower()
    if use_custom == 'y':
        print("📝 Enter your comment block (press Enter twice when done):")
        comment_lines = []
        empty_lines = 0
        while empty_lines < 2:
            line = input()
            if line == "":
                empty_lines += 1
            else:
                empty_lines = 0
                comment_lines.append(line)
        comment_block = '\n'.join(comment_lines)
    else:
        comment_block = default_comment
        print("📝 Using default comment block")
    
    # Ask for file extensions filter (optional)
    print("\n" + "-" * 50)
    extensions_input = input("🎯 Enter file extensions (e.g., .py,.java,.cpp) or press Enter for all: ").strip()
    if extensions_input:
        file_extensions = [ext.strip() for ext in extensions_input.split(',')]
        file_extensions = ['.' + ext.lstrip('.') for ext in file_extensions]
        print(f"🎯 Will process files: {', '.join(file_extensions)}")
    else:
        file_extensions = None
        print("🎯 Will process all files")
    
    # Show preview
    print("\n" + "=" * 60)
    print("📋 PROCESSING PREVIEW")
    print("=" * 60)
    print(f"Directory: {abs_path}")
    print(f"Extensions: {'All files' if not file_extensions else ', '.join(file_extensions)}")
    print("\nComment to add:")
    print("-" * 30)
    print(comment_block)
    print("-" * 30)
    
    # Final confirmation
    confirm = input("\n🚀 Ready to proceed? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Operation cancelled. Goodbye! 👋")
        return
    
    print("\n" + "=" * 60)
    # Process the directory
    process_directory(directory_path, comment_block, file_extensions)
    
    print("✨ Thank you for using File Comment Inserter! ✨")

if __name__ == "__main__":
    main()