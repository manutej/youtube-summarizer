# `/yt` Command Reference

Quick reference guide for the Claude Code `/yt` slash command.

## Overview

The `/yt` slash command integrates the YouTube Video Summarizer with Claude Code, allowing you to quickly summarize videos directly in your Claude Code session.

## Basic Syntax

```bash
/yt <url> [flags]
```

## Quick Examples

```bash
# Quick summary (concise format)
/yt https://youtube.com/watch?v=dQw4w9WgXcQ

# Detailed summary with timestamps
/yt https://youtube.com/watch?v=dQw4w9WgXcQ -d

# Academic notes format
/yt https://youtube.com/watch?v=dQw4w9WgXcQ -a

# Bullet points format
/yt https://youtube.com/watch?v=dQw4w9WgXcQ -b

# Deep analysis with extended thinking
/yt https://youtube.com/watch?v=dQw4w9WgXcQ -a -t
```

## Format Flags

| Flag | Format | Best For |
|------|--------|----------|
| `-c` | Concise | Quick overview, deciding if video is worth watching |
| `-d` | Detailed | Comprehensive understanding, reference material |
| `-a` | Academic | Course notes, technical learning, research |
| `-b` | Bullets | Quick reference, time-constrained review |

**Default**: Concise format (`-c`)

## Processing Flags

| Flag | Description | Use Case |
|------|-------------|----------|
| `-t` | Extended thinking | Complex/technical content requiring deep analysis |
| `--chunking <strategy>` | Chunking strategy | Control how transcript is split |
| `--chunk-size <size>` | Chunk size in tokens | Adjust chunk granularity |
| `-v` | Verbose output | See processing details |

### Chunking Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| `none` | No chunking | Short videos (< 10 min) |
| `auto` | Auto-select (default) | General use |
| `recursive` | Natural boundaries | Medium videos (10-30 min) |
| `semantic` | Topic-based | Structured lectures, long videos (> 30 min) |
| `timestamp` | Time intervals | Very long videos (> 1 hour) |

## Output Flags

| Flag | Description | Example |
|------|-------------|---------|
| `-o <file>` | Custom output path | `-o summaries/my-video.md` |
| No flag | Auto-generated filename | `summaries/ChannelName_VideoTitle_videoID.md` |

## Batch Processing

```bash
# Process multiple videos
/yt url1 url2 url3 --batch

# Batch with format
/yt url1 url2 url3 --batch -d

# Batch with custom output directory (requires individual -o for each)
/yt url1 -o summaries/vid1.md url2 -o summaries/vid2.md --batch
```

## Common Workflows

### Quick Screening
```bash
# Decide if video is worth watching
/yt <url>
```

### Deep Learning
```bash
# Academic notes with deep analysis
/yt <url> -a -t
```

### Research Paper
```bash
# Academic format with semantic chunking
/yt <url> -a --chunking semantic -o docs/research/paper.md
```

### Tutorial Series
```bash
# Batch process with detailed summaries
/yt url1 url2 url3 url4 --batch -d
```

### Conference Talk
```bash
# Detailed summary with extended thinking
/yt <url> -d -t -o summaries/conferences/talk.md
```

## Flag Combinations

### Recommended Combinations

```bash
# Quick overview
/yt <url> -c

# Standard summary
/yt <url> -d

# Deep technical analysis
/yt <url> -a -t --chunking semantic

# Rapid reference
/yt <url> -b

# Long video (1+ hour)
/yt <url> -d --chunking timestamp

# Multilingual (if supported)
/yt <url> -d --language es en
```

## Video ID Formats

All formats are supported:

```bash
# Full URL
/yt https://youtube.com/watch?v=dQw4w9WgXcQ

# Short URL
/yt https://youtu.be/dQw4w9WgXcQ

# Video ID only
/yt dQw4w9WgXcQ
```

## Output Structure

Summaries are automatically saved to:
```
summaries/
├── ChannelName_VideoTitle_videoID.md
├── AnotherChannel_AnotherVideo_xyz123.md
└── custom-name.md  # If using -o flag
```

## Tips

1. **Use auto-chunking**: Let the tool choose the best strategy
   ```bash
   /yt <url> -d  # Uses --chunking auto by default
   ```

2. **Extended thinking for complex content**: Use `-t` for technical videos
   ```bash
   /yt <url> -a -t
   ```

3. **Organize outputs**: Use `-o` to organize by topic/date
   ```bash
   /yt <url> -d -o summaries/2025-10/react-patterns.md
   ```

4. **Batch processing**: Process multiple videos at once
   ```bash
   /yt url1 url2 url3 --batch -d
   ```

5. **Verbose for debugging**: Use `-v` to see what's happening
   ```bash
   /yt <url> -v
   ```

## Environment Requirements

- `ANTHROPIC_API_KEY` must be set in `.env`
- `./bin/yt` must be executable (`chmod +x ./bin/yt`)
- Python virtual environment should be activated (handled by `./bin/yt`)

## Troubleshooting

### "No transcript available"
- Video doesn't have captions
- Try: Check video on YouTube for CC button
- Alternative: Try different language `--language en es`

### "ANTHROPIC_API_KEY not set"
- API key not configured
- Fix: Add to `.env` file: `ANTHROPIC_API_KEY=your_key`

### Semantic chunking fails
- Missing dependencies or OpenAI key
- Fix: `pip install langchain-experimental langchain-openai`
- Fix: Add `OPENAI_API_KEY` to `.env`
- Alternative: Use `--chunking recursive`

### Command not found
- Slash command not registered
- Fix: Check `.claude/commands/yt.md` exists
- Fix: Restart Claude Code session

## Performance Notes

| Video Length | Processing Time | Recommended Format |
|--------------|----------------|-------------------|
| < 10 min | ~30-60 sec | Concise or Detailed |
| 10-30 min | ~1-2 min | Detailed with auto-chunking |
| 30-60 min | ~2-4 min | Detailed with semantic chunking |
| 1+ hour | ~4-8 min | Detailed with timestamp chunking |

*Times vary based on content complexity and chunking strategy*

## Cost Considerations

- Concise summaries: Lower token usage
- Extended thinking (`-t`): Higher token usage but better analysis
- Semantic chunking: Additional OpenAI API calls for embeddings
- Batch processing: Multiple API calls (one per video)

## See Also

- [USAGE_GUIDE.md](../USAGE_GUIDE.md) - Comprehensive usage guide
- [README.md](../README.md) - Project overview
- [QUICKSTART.md](../QUICKSTART.md) - Quick start guide
- [.claude/commands/yt.md](../.claude/commands/yt.md) - Slash command definition

---

**Generated with**: [Claude Code](https://claude.com/claude-code)
