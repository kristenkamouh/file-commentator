# File Comment Inserter 🚀

A powerful terminal-based Python tool that automatically adds comment blocks to the top of all files in a directory while preserving their original content.

## ✨ Features

- **🎯 Batch Processing**: Process entire directories recursively
- **📊 Real-time Progress**: Beautiful progress bar with file-by-file updates
- **🔍 Smart Filtering**: Filter by file extensions (.py, .java, .cpp, etc.)
- **🛡️ Safety First**: Prevents duplicate comments and handles errors gracefully
- **🎨 Terminal UI**: Clean, professional interface with emojis and progress tracking
- **⚡ Fast Performance**: Optimized for large codebases
- **📁 Flexible Input**: Command-line arguments or interactive mode

## 🔧 Installation

### Prerequisites
- Python 3.6 or higher
- No external dependencies required (uses only standard library)

### Setup
1. Download the script:
```bash
curl -O https://raw.githubusercontent.com/your-repo/file-comment-inserter/main/comment_inserter.py
```

2. Make it executable:
```bash
chmod +x comment_inserter.py
```

3. (Optional) Add to PATH for global usage:
```bash
# Add this line to your ~/.bashrc or ~/.zshrc
export PATH="$PATH:/path/to/script/directory"
```

## 🚀 Usage

### Quick Start
```bash
# Process current directory
python comment_inserter.py .

# Process specific directory
python comment_inserter.py /path/to/your/project

# Interactive mode
python comment_inserter.py
```

### Interactive Mode
When you run the script without arguments, it guides you through:

1. **Directory Selection**: Enter the path to your project
2. **Comment Customization**: Use default or create custom comment
3. **File Filtering**: Choose specific file extensions or process all files
4. **Confirmation**: Review settings before processing

### Command Examples

```bash
# Process all Python files in a project
python comment_inserter.py ~/my-python-project
# Then enter: .py when prompted

# Process C++ and Java files
python comment_inserter.py ~/my-code
# Then enter: .cpp,.java when prompted

# Process all files in current directory
python comment_inserter.py .
# Press Enter when prompted for extensions
```

## 📝 Default Comment Block

```
/*
this is a test comment for demonstration purposes
*/
```

### Custom Comments
You can easily add custom comments like:
- License headers
- Copyright notices
- Project documentation
- Author information
- Version tags

## 📊 Sample Output

```
╔══════════════════════════════════════════════════════════════╗
║                    FILE COMMENT INSERTER                    ║
║                     v1.0 - Terminal Edition                 ║
╚══════════════════════════════════════════════════════════════╝

📁 Using directory from command line: /home/user/project
🎯 Target directory: /home/user/project
📝 Using default comment block
🎯 Will process files: .py, .java, .cpp

📂 Scanning directory: /home/user/project
🔍 Counting files...
📄 Found 47 files to process
🚀 Starting processing...

[=============================================] 100% (47/47)

============================================================
🎉 PROCESSING COMPLETE! 🎉
============================================================
✅ Files processed successfully: 42
⏭️  Files skipped (already had comment): 3
❌ Files with errors: 2
📊 Total files examined: 47
============================================================
```

## 🛡️ Safety Features

- **Duplicate Prevention**: Won't add comments if they already exist
- **Directory Exclusion**: Automatically skips `.git`, `__pycache__`, `node_modules`, etc.
- **Large File Handling**: Skips files larger than 10MB to prevent memory issues
- **Error Recovery**: Continues processing even if individual files fail
- **Confirmation Prompts**: Always asks before making changes
- **Encoding Support**: Handles UTF-8 with fallback for problematic files

## 🎯 Use Cases

### Software Development
- Add license headers to all source files
- Insert copyright notices
- Add project documentation headers
- Version control tags

### Code Organization
- Add author information
- Insert project descriptions
- Add modification timestamps
- Include usage instructions

### Educational Projects
- Add student information to assignments
- Insert course details
- Add submission dates

## ⚙️ Configuration Options

### File Extensions
Specify which files to process:
```
.py          # Python files only
.java,.cpp   # Java and C++ files
.js,.ts,.jsx # JavaScript/TypeScript files
.php,.html   # Web development files
```

### Excluded Directories
The following directories are automatically excluded:
- `.git` - Git repository data
- `__pycache__` - Python cache files
- `.vscode` - VS Code settings
- `node_modules` - Node.js packages
- `.idea` - IntelliJ IDEA files

## 🔄 How It Works

1. **Directory Scanning**: Recursively walks through all subdirectories
2. **File Counting**: Counts total files for progress tracking
3. **Content Preservation**: Reads original content before modification
4. **Smart Insertion**: Prepends comment while keeping original content intact
5. **Progress Updates**: Real-time progress bar with current file display
6. **Summary Report**: Detailed completion statistics

## 🐛 Troubleshooting

### Common Issues

**"Directory does not exist"**
- Check the path spelling and make sure the directory exists
- Use absolute paths to avoid confusion

**"Files skipped (already had comment)"**
- This is normal - prevents duplicate comments
- Files with existing comments are safely ignored

**"Files with errors"**
- Usually caused by permission issues or corrupted files
- Check file permissions with `ls -la`

**Large files skipped**
- Files over 10MB are automatically skipped for performance
- Modify `10 * 1024 * 1024` in the code to change this limit

### Performance Tips
- Use file extension filtering for large projects
- Run on SSD storage for faster file I/O
- Close other applications when processing very large directories

## 📜 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

### Development Setup
```bash
git clone https://github.com/your-repo/file-comment-inserter
cd file-comment-inserter
python comment_inserter.py --help
```

## 📧 Support

If you encounter any issues or have questions:
- Open an issue on GitHub
- Check the troubleshooting section above
- Review the code comments for technical details

## 🎉 Acknowledgments

Built with ❤️ for developers who need to quickly add headers to multiple files.

---

**Happy Coding! 🚀**