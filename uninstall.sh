#!/usr/bin/env bash
#
# YouTube Video Summarizer - Uninstallation Script
#

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}YouTube Video Summarizer - Uninstall${NC}"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BIN_DIR="$SCRIPT_DIR/bin"

# Detect shell profile
SHELL_NAME=$(basename "$SHELL")
case "$SHELL_NAME" in
    bash)
        PROFILE_FILE="$HOME/.bashrc"
        [[ ! -f "$PROFILE_FILE" ]] && PROFILE_FILE="$HOME/.bash_profile"
        ;;
    zsh)
        PROFILE_FILE="$HOME/.zshrc"
        ;;
    *)
        PROFILE_FILE="$HOME/.profile"
        ;;
esac

echo "This will:"
echo "  1. Remove PATH entry from $PROFILE_FILE"
echo "  2. Remove virtual environment"
echo "  3. Keep generated summaries (summaries/)"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Remove from PATH
if [[ -f "$PROFILE_FILE" ]]; then
    if grep -q "$BIN_DIR" "$PROFILE_FILE"; then
        echo "Removing from $PROFILE_FILE..."
        # Create backup
        cp "$PROFILE_FILE" "$PROFILE_FILE.bak"
        # Remove the line and the comment before it
        sed -i.tmp '/# YouTube Video Summarizer/d' "$PROFILE_FILE"
        sed -i.tmp "\|$BIN_DIR|d" "$PROFILE_FILE"
        rm -f "$PROFILE_FILE.tmp"
        echo -e "${GREEN}✓ Removed from PATH${NC}"
        echo -e "${YELLOW}Backup saved: $PROFILE_FILE.bak${NC}"
    fi
fi

# Remove venv
if [[ -d "$SCRIPT_DIR/venv" ]]; then
    echo "Removing virtual environment..."
    rm -rf "$SCRIPT_DIR/venv"
    echo -e "${GREEN}✓ Virtual environment removed${NC}"
fi

echo ""
echo -e "${GREEN}Uninstallation complete!${NC}"
echo ""
echo "Reload your shell:"
echo "  source $PROFILE_FILE"
echo ""
echo "To completely remove, delete the directory:"
echo "  rm -rf $SCRIPT_DIR"
echo ""
