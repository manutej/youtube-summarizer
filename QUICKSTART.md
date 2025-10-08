# Quick Start Guide

Get up and running with YouTube Video Summarizer in 5 minutes.

## Prerequisites

- Python 3.8+
- Anthropic API key ([get one here](https://console.anthropic.com/))

## Installation (3 steps)

### 1. Install Dependencies

```bash
cd /Users/manu/Documents/LUXOR/Git_Repos/yt
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
cp .env.example .env
# Edit .env and add your API key:
echo "ANTHROPIC_API_KEY=your_key_here" >> .env
```

### 3. Test It!

```bash
# Replace with any YouTube URL
python -m src.cli "https://youtube.com/watch?v=dQw4w9WgXcQ"
```

**Output**: `summaries/VIDEO_ID.md`

## Common Commands

```bash
# Quick summary
python -m src.cli "VIDEO_URL" --format concise

# Detailed summary (default)
python -m src.cli "VIDEO_URL"

# Academic notes
python -m src.cli "VIDEO_URL" --format academic

# Multiple videos
python -m src.cli URL1 URL2 URL3 --batch

# Deep analysis
python -m src.cli "VIDEO_URL" --extended-thinking

# Custom output
python -m src.cli "VIDEO_URL" -o my-summary.md
```

## What Happens?

1. **Extracts** transcript from YouTube
2. **Chunks** intelligently (if needed)
3. **Summarizes** with Claude
4. **Saves** Markdown summary to `summaries/`

## Output Format

```markdown
# Video Summary: [Title]

## Metadata
- Video ID, URL, Channel, Duration

## Executive Summary
[2-3 sentence overview]

## Key Points
- [Point 1 with timestamp]
- [Point 2 with timestamp]
...

## Detailed Summary
[Comprehensive breakdown]

## Topics Covered
- [Topic 1]
...

## Notable Quotes
> "[Quote]" — [timestamp]

## Resources Mentioned
- [Resource 1]
...
```

## Troubleshooting

### "No transcript available"
Video doesn't have captions. Try another video.

### "API key not set"
```bash
# Check .env file exists
cat .env

# Should show: ANTHROPIC_API_KEY=sk-...
```

## Next Steps

- **Full Guide**: See [USAGE_GUIDE.md](USAGE_GUIDE.md)
- **Deep Dive**: See [README.md](README.md)
- **Research**: See [docs/LANGCHAIN_RESEARCH.md](docs/LANGCHAIN_RESEARCH.md)

## Example Session

```bash
$ python -m src.cli "https://youtube.com/watch?v=example"

🚀 YouTube Video Summarizer
==================================================

📹 Processing: https://youtube.com/watch?v=example
  └─ Extracting transcript...
  └─ ✓ Title: Introduction to Python
  └─ ✓ Duration: 15:30
  └─ ✓ Language: en
  └─ Chunking strategy: recursive
  └─ Created 3 chunks
  └─ Summarizing with Claude...
  └─ ✓ Summary generated
  └─ ✓ Saved to: summaries/example.md
  └─ ✅ Complete!

==================================================
✨ All done!
```

---

**Ready to summarize!** 🎬 → 📝
