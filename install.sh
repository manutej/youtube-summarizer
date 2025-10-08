#!/usr/bin/env bash
#
# YouTube Video Summarizer - Installation Script
#
# This script sets up the yt command and adds it to your PATH
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}YouTube Video Summarizer - Installation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BIN_DIR="$SCRIPT_DIR/bin"
YT_SCRIPT="$BIN_DIR/yt"

# Check if yt script exists
if [[ ! -f "$YT_SCRIPT" ]]; then
    echo -e "${RED}Error: yt script not found at $YT_SCRIPT${NC}"
    exit 1
fi

# Make executable
chmod +x "$YT_SCRIPT"

echo -e "${YELLOW}Step 1: Setting up Python environment${NC}"

# Check if venv exists
if [[ ! -d "$SCRIPT_DIR/venv" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Install dependencies
echo "Installing dependencies..."
source "$SCRIPT_DIR/venv/bin/activate"
pip install -q --upgrade pip
pip install -q -r "$SCRIPT_DIR/requirements.txt"
deactivate
echo -e "${GREEN}✓ Dependencies installed${NC}"

echo ""
echo -e "${YELLOW}Step 2: Configuring API key${NC}"

# Check if .env exists
if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
    echo "Creating .env file..."

    # Prompt for API key
    echo -e "${BLUE}Enter your Anthropic API key (or press Enter to skip):${NC}"
    read -r api_key

    if [[ -n "$api_key" ]]; then
        cat > "$SCRIPT_DIR/.env" << EOF
ANTHROPIC_API_KEY=$api_key
CLAUDE_MODEL=claude-sonnet-4-20250514
OUTPUT_DIR=summaries
MAX_TOKENS=4096
EOF
        echo -e "${GREEN}✓ API key configured${NC}"
    else
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
        echo -e "${YELLOW}⚠ Skipped API key setup. Edit .env file manually.${NC}"
    fi
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

echo ""
echo -e "${YELLOW}Step 3: Adding to PATH${NC}"

# Detect shell
SHELL_NAME=$(basename "$SHELL")
case "$SHELL_NAME" in
    bash)
        PROFILE_FILE="$HOME/.bashrc"
        if [[ ! -f "$PROFILE_FILE" ]]; then
            PROFILE_FILE="$HOME/.bash_profile"
        fi
        ;;
    zsh)
        PROFILE_FILE="$HOME/.zshrc"
        ;;
    *)
        echo -e "${YELLOW}Warning: Unsupported shell: $SHELL_NAME${NC}"
        PROFILE_FILE="$HOME/.profile"
        ;;
esac

# Check if already in PATH
PATH_EXPORT="export PATH=\"$BIN_DIR:\$PATH\""

if grep -q "$BIN_DIR" "$PROFILE_FILE" 2>/dev/null; then
    echo -e "${GREEN}✓ Already in PATH ($PROFILE_FILE)${NC}"
else
    echo ""
    echo "Adding yt to PATH in $PROFILE_FILE"
    echo ""
    echo -e "${BLUE}Add this line to $PROFILE_FILE?${NC}"
    echo "  $PATH_EXPORT"
    echo ""
    read -p "Add to PATH? (y/n) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "" >> "$PROFILE_FILE"
        echo "# YouTube Video Summarizer" >> "$PROFILE_FILE"
        echo "$PATH_EXPORT" >> "$PROFILE_FILE"
        echo -e "${GREEN}✓ Added to $PROFILE_FILE${NC}"
        echo -e "${YELLOW}Run: source $PROFILE_FILE${NC}"
    else
        echo -e "${YELLOW}⚠ Skipped PATH setup. Add manually:${NC}"
        echo "  echo '$PATH_EXPORT' >> $PROFILE_FILE"
    fi
fi

echo ""
echo -e "${YELLOW}Step 4: Creating output directory${NC}"
mkdir -p "$SCRIPT_DIR/summaries"
echo -e "${GREEN}✓ Output directory ready${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Quick Start:${NC}"
echo ""
echo "  1. Reload your shell:"
echo -e "     ${YELLOW}source $PROFILE_FILE${NC}"
echo ""
echo "  2. Test the command:"
echo -e "     ${YELLOW}yt --help${NC}"
echo ""
echo "  3. Summarize a video:"
echo -e "     ${YELLOW}yt https://youtube.com/watch?v=VIDEO_ID${NC}"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  yt <url>          Quick summary"
echo "  yt <url> -d       Detailed summary"
echo "  yt <url> -a       Academic notes"
echo "  yt <url> -t       Deep thinking mode"
echo "  yt --help         Full help"
echo ""
echo -e "${BLUE}Documentation:${NC}"
echo "  README:       $SCRIPT_DIR/README.md"
echo "  Quick Start:  $SCRIPT_DIR/QUICKSTART.md"
echo "  Usage Guide:  $SCRIPT_DIR/USAGE_GUIDE.md"
echo ""
echo -e "${GREEN}Happy summarizing! 🎬 → 📝${NC}"
echo ""
