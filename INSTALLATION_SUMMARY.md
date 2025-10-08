# Installation & Setup Summary

Complete guide for getting `yt` command working on your system.

## ✅ Quick Installation (Recommended)

```bash
# 1. Navigate to project
cd /Users/manu/Documents/LUXOR/Git_Repos/yt

# 2. Run installer
./install.sh

# 3. Reload shell
source ~/.bashrc  # or ~/.zshrc

# 4. Test it!
yt --help
```

## 📋 What the Installer Does

The `install.sh` script automatically:

1. ✅ Creates Python virtual environment
2. ✅ Installs all dependencies
3. ✅ Configures API key (interactive prompt)
4. ✅ Adds `bin/yt` to your PATH
5. ✅ Creates output directory

## 🎯 Manual Installation (Alternative)

If you prefer manual setup:

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate it
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 5. Add to PATH (choose your shell)
# For bash:
echo 'export PATH="/Users/manu/Documents/LUXOR/Git_Repos/yt/bin:$PATH"' >> ~/.bashrc

# For zsh:
echo 'export PATH="/Users/manu/Documents/LUXOR/Git_Repos/yt/bin:$PATH"' >> ~/.zshrc

# 6. Reload shell
source ~/.bashrc  # or ~/.zshrc

# 7. Test
yt --help
```

## 🔑 API Key Setup

### Option 1: During Installation
The installer will prompt for your API key interactively.

### Option 2: Manual Setup
```bash
# Edit .env file
nano .env

# Add this line:
ANTHROPIC_API_KEY=your_api_key_here
```

### Get API Key
1. Visit: https://console.anthropic.com/
2. Create account (if needed)
3. Generate API key
4. Copy and paste into `.env`

## 🧪 Testing the Installation

```bash
# 1. Check help
yt --help

# 2. Check version
yt --version

# 3. Test with a video (replace with any YouTube URL)
yt dRsjO-88nBs -c

# Should output:
# 🚀 YouTube Video Summarizer
# ...
# ✅ Complete!
```

## 📍 Directory Structure After Installation

```
/Users/manu/Documents/LUXOR/Git_Repos/yt/
├── bin/
│   └── yt              ← Executable bash script (in PATH)
├── venv/               ← Python virtual environment
├── src/                ← Python source code
├── summaries/          ← Generated summaries go here
├── docs/               ← Documentation
├── .env                ← Your API key (created by installer)
├── install.sh          ← Installation script
├── uninstall.sh        ← Uninstallation script
└── README.md           ← Main documentation
```

## 🔧 Customization

### Change Default Format
```bash
# Add to .bashrc or .zshrc
export YT_FORMAT=detailed  # or concise, academic, bullet_points
```

### Change Output Directory
```bash
# Add to .bashrc or .zshrc
export YT_OUTPUT_DIR=~/my-summaries
```

### Create Aliases
```bash
# Add to .bashrc or .zshrc
alias ytq='yt --format concise'        # Quick summary
alias ytd='yt --format detailed'       # Detailed summary
alias yta='yt --format academic'       # Academic notes
alias ytt='yt --extended-thinking'     # Deep thinking
```

Then use:
```bash
ytq VIDEO_URL    # Quick summary
ytd VIDEO_URL    # Detailed summary
```

## 🗑️ Uninstallation

```bash
# Run uninstaller
cd /Users/manu/Documents/LUXOR/Git_Repos/yt
./uninstall.sh

# This removes:
# - PATH entry from your shell profile
# - Virtual environment
#
# Keeps:
# - Generated summaries (summaries/)
# - Source code
```

## 🐛 Troubleshooting

### "yt: command not found"

**Cause**: PATH not set or shell not reloaded

**Fix**:
```bash
# Reload shell
source ~/.bashrc  # or ~/.zshrc

# Or manually add to PATH:
export PATH="/Users/manu/Documents/LUXOR/Git_Repos/yt/bin:$PATH"

# Check if it's in PATH:
which yt
```

### "ANTHROPIC_API_KEY not set"

**Cause**: .env file missing or incorrect

**Fix**:
```bash
# Check .env exists
ls -la .env

# Edit and add key
nano .env

# Should contain:
# ANTHROPIC_API_KEY=sk-ant-...
```

### "No module named 'youtube_transcript_api'"

**Cause**: Dependencies not installed

**Fix**:
```bash
# Activate venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Permission denied errors

**Cause**: Scripts not executable

**Fix**:
```bash
# Make scripts executable
chmod +x bin/yt install.sh uninstall.sh
```

## 📚 Next Steps

After installation:

1. **Read Docs**:
   - `README.md` - Project overview
   - `QUICKSTART.md` - Quick start guide
   - `USAGE_GUIDE.md` - Complete usage examples

2. **Try Different Formats**:
   ```bash
   yt URL -c    # Concise
   yt URL -d    # Detailed
   yt URL -a    # Academic
   yt URL -b    # Bullet points
   ```

3. **Explore Advanced Features**:
   ```bash
   yt URL -t                    # Extended thinking
   yt URL --chunking semantic   # Semantic chunking
   yt URL1 URL2 URL3 --batch    # Batch processing
   ```

4. **Check Output**:
   ```bash
   # Summaries are saved here:
   ls -l summaries/

   # View a summary:
   cat summaries/VIDEO_ID.md
   ```

## ✅ Verification Checklist

After installation, verify:

- [ ] `yt --help` shows help message
- [ ] `yt --version` shows version
- [ ] `which yt` returns `/Users/manu/Documents/LUXOR/Git_Repos/yt/bin/yt`
- [ ] `.env` file exists with API key
- [ ] `venv/` directory exists
- [ ] Can summarize a test video successfully

## 🎓 Learning Resources

- **Quick Reference**: `yt --help`
- **Examples**: `USAGE_GUIDE.md`
- **Research**: `docs/LANGCHAIN_RESEARCH.md`
- **Testing**: `TEST_RESULTS.md`

---

**Installation complete! 🎉**

Start summarizing videos with: `yt <youtube-url>`
