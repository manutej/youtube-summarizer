# YouTube Video Summarizer

Transform YouTube videos into LLM-friendly summaries using Claude and LangChain.

## Features

- **📹 Transcript Extraction**: Automatic transcript extraction from YouTube videos
- **🧠 Claude-Powered Summarization**: Uses Claude Sonnet 4 with long-context optimization
- **✂️ Intelligent Chunking**: Multiple chunking strategies (recursive, semantic, timestamp-based)
- **📝 Multiple Formats**: Concise, detailed, academic, and bullet-point summaries
- **⚡ Batch Processing**: Process multiple videos or entire playlists
- **🎯 Extended Thinking**: Optional deep analysis mode for complex content
- **📦 LangChain Integration**: Leverages LangChain for document loading and processing

## Installation

1. Clone the repository:
```bash
cd /Users/manu/Documents/LUXOR/Git_Repos/yt
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## Quick Start

### Basic Usage

```bash
# Summarize a single video
python -m src.cli "https://youtube.com/watch?v=VIDEO_ID"

# Specify output file
python -m src.cli "https://youtube.com/watch?v=VIDEO_ID" -o summaries/my-video.md

# Choose format
python -m src.cli "https://youtube.com/watch?v=VIDEO_ID" --format concise
```

### Advanced Usage

```bash
# Use semantic chunking for long videos
python -m src.cli "https://youtube.com/watch?v=VIDEO_ID" --chunking semantic

# Enable extended thinking for deep analysis
python -m src.cli "https://youtube.com/watch?v=VIDEO_ID" --extended-thinking

# Batch process multiple videos
python -m src.cli URL1 URL2 URL3 --batch

# Academic format with custom chunking
python -m src.cli "https://youtube.com/watch?v=VIDEO_ID" \
  --format academic \
  --chunking semantic \
  --chunk-size 1500
```

## Summary Formats

### Concise
- Executive summary (2-3 sentences)
- Key takeaways (5-7 points)
- Main topics
- Target audience

### Detailed (Default)
- Executive summary
- Key points with timestamps
- Comprehensive breakdown
- Topics covered
- Notable quotes
- Resources mentioned
- Target audience

### Academic
- Abstract-style overview
- Main concepts with definitions
- Methodology/approach
- Practical applications
- Key findings
- Resources & references
- Discussion points

### Bullet Points
- TL;DR (one sentence)
- Rapid-fire key points (15-20 items)
- Topics list
- Resources

## Chunking Strategies

### Auto (Recommended)
Automatically selects best strategy based on video length:
- **< 10 min**: No chunking (full context)
- **< 30 min**: Recursive chunking
- **> 30 min**: Semantic chunking (if available)

### None
Uses full transcript in single pass. Best for short videos with Claude's 200K context window.

### Recursive
Splits on natural boundaries (paragraphs → sentences → words).
Good for general content.

### Semantic
Splits based on semantic similarity using embeddings.
**Best for topic-based content like lectures**.
Requires: `pip install langchain-experimental langchain-openai`

### Timestamp
Splits by time intervals (default: 5 minutes).
Preserves temporal structure.

## Architecture

### Tech Stack
- **LangChain**: Document loading and text splitting
- **Anthropic Claude**: LLM summarization with long-context optimization
- **youtube-transcript-api**: Transcript extraction
- **Pydantic**: Data validation and models

### Workflow

```
1. Extract Transcript
   ├─ Use LangChain's YoutubeLoader
   ├─ Fetch metadata (title, channel, duration)
   └─ Get timestamped segments

2. Chunk (if needed)
   ├─ Recommend strategy based on video length
   ├─ Apply RecursiveCharacterTextSplitter or SemanticChunker
   └─ Preserve metadata and timestamps

3. Summarize with Claude
   ├─ Optimize prompt (transcript at top)
   ├─ Use XML structure for organization
   ├─ Request quote extraction first (grounding)
   └─ Generate structured summary

4. Output
   ├─ Parse Claude's response
   ├─ Format as Markdown
   └─ Save to summaries/ directory
```

### Long-Context Optimization

Following [Anthropic's best practices](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/long-context-tips):

1. **Transcript Placement**: Placed at TOP of prompt (30% quality improvement)
2. **XML Structure**: Organized with `<documents>` tags
3. **Quote Grounding**: Requests key quotes before summarization
4. **200K Context**: Leverages Claude's full context window

## CLI Reference

```
usage: python -m src.cli [-h] [-o OUTPUT] [-f {concise,detailed,academic,bullet_points}]
                         [--chunking {none,recursive,semantic,timestamp,auto}]
                         [--chunk-size CHUNK_SIZE] [--chunk-overlap CHUNK_OVERLAP]
                         [--model MODEL] [--extended-thinking]
                         [--thinking-budget THINKING_BUDGET]
                         [--language LANGUAGE [LANGUAGE ...]]
                         [--translation TRANSLATION] [--batch] [-v]
                         urls [urls ...]

Arguments:
  urls                  YouTube video URL(s) or video ID(s)

Output Options:
  -o, --output          Output file path (default: summaries/<video_id>.md)
  -f, --format          Summary format: concise, detailed, academic, bullet_points

Processing Options:
  --chunking            Chunking strategy: none, recursive, semantic, timestamp, auto
  --chunk-size          Chunk size in tokens (default: 1000)
  --chunk-overlap       Chunk overlap in tokens (default: 200)

LLM Options:
  --model               Claude model to use (default: claude-sonnet-4-20250514)
  --extended-thinking   Enable extended thinking mode
  --thinking-budget     Token budget for thinking (default: 4096)

Transcript Options:
  --language            Preferred transcript languages (default: en)
  --translation         Translate transcript to this language

Other:
  --batch               Process multiple videos (continue on error)
  -v, --verbose         Verbose output
```

## Examples

### Example 1: Technical Tutorial
```bash
python -m src.cli "https://youtube.com/watch?v=dQw4w9WgXcQ" \
  --format detailed \
  --chunking recursive \
  -o docs/react-tutorial.md
```

### Example 2: Long Conference Talk
```bash
python -m src.cli "https://youtube.com/watch?v=example" \
  --format academic \
  --chunking semantic \
  --extended-thinking \
  -o docs/conference-talk.md
```

### Example 3: Batch Processing
```bash
python -m src.cli \
  "https://youtube.com/watch?v=video1" \
  "https://youtube.com/watch?v=video2" \
  "https://youtube.com/watch?v=video3" \
  --batch \
  --format concise
```

## Project Structure

```
yt/
├── src/
│   ├── __init__.py           # Package initialization
│   ├── cli.py                # Command-line interface
│   ├── config.py             # Configuration management
│   ├── models.py             # Pydantic data models
│   ├── extractors.py         # Transcript extraction (LangChain)
│   ├── chunkers.py           # Text chunking strategies
│   └── summarizer.py         # Claude-powered summarization
├── docs/                     # Documentation and research
│   └── LANGCHAIN_RESEARCH.md # LangChain integration research
├── summaries/                # Generated summaries (gitignored)
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## Development

### Research Documentation

See [docs/LANGCHAIN_RESEARCH.md](docs/LANGCHAIN_RESEARCH.md) for comprehensive research on:
- LangChain YouTube loaders
- Text splitting strategies
- Claude integration best practices
- Summarization workflows

### Adding New Features

1. **New Output Format**: Modify `summarizer.py::_get_task_instructions()`
2. **New Chunking Strategy**: Add to `chunkers.py::ChunkingStrategy` enum
3. **Playlist Support**: Implement in `extractors.py::BatchTranscriptExtractor`

## Limitations

- Requires YouTube videos to have transcripts (auto-generated or manual)
- Age-restricted videos may not be accessible
- Some videos may have poor auto-generated captions
- Semantic chunking requires OpenAI API key for embeddings
- Rate limits apply to both YouTube and Claude APIs

## Troubleshooting

### "No transcript available"
- Video may not have captions
- Try different language with `--language en es fr`
- Check if video is age-restricted or private

### "ANTHROPIC_API_KEY not set"
- Create `.env` file from `.env.example`
- Add your API key: `ANTHROPIC_API_KEY=your_key_here`

### Semantic chunking not working
- Install optional dependencies:
  ```bash
  pip install langchain-experimental langchain-openai
  ```
- Set `OPENAI_API_KEY` in `.env`

## Contributing

Contributions welcome! Areas for improvement:
- Playlist support
- Better transcript parsing for speaker detection
- Custom prompt templates
- Output format customization
- Caching for repeated videos

## License

MIT

## Acknowledgments

- Built with [LangChain](https://python.langchain.com/)
- Powered by [Anthropic Claude](https://www.anthropic.com/claude)
- Uses [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)

---

**Generated with**: [Claude Code](https://claude.com/claude-code)
