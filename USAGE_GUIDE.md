# YouTube Video Summarizer - Usage Guide

Complete guide to using the YouTube Video Summarizer tool.

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Basic Usage](#basic-usage)
4. [Advanced Features](#advanced-features)
5. [Understanding Formats](#understanding-formats)
6. [Chunking Strategies](#chunking-strategies)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

---

## Installation

### Step 1: Prerequisites

- Python 3.8 or higher
- Anthropic API key ([get one here](https://console.anthropic.com/))
- (Optional) OpenAI API key for semantic chunking

### Step 2: Set Up Environment

```bash
# Navigate to project directory
cd /Users/manu/Documents/LUXOR/Git_Repos/yt

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure API Keys

```bash
# Copy environment template
cp .env.example .env

# Edit .env file and add your API key
# ANTHROPIC_API_KEY=your_api_key_here
```

---

## Configuration

### Environment Variables

Edit `.env` file:

```bash
# Required
ANTHROPIC_API_KEY=your_api_key_here

# Optional
CLAUDE_MODEL=claude-sonnet-4-20250514  # Default model
OUTPUT_DIR=summaries  # Output directory
MAX_TOKENS=4096  # Max tokens for summary

# For semantic chunking (optional)
OPENAI_API_KEY=your_openai_key_here
```

### Directory Structure

The tool creates these directories automatically:
- `summaries/` - Generated video summaries
- `docs/` - Documentation and research notes

---

## Basic Usage

### Summarize a Single Video

```bash
# Using YouTube URL
python -m src.cli "https://youtube.com/watch?v=dQw4w9WgXcQ"

# Using video ID directly
python -m src.cli "dQw4w9WgXcQ"
```

**Output**: `summaries/VIDEO_ID.md`

### Specify Output Location

```bash
python -m src.cli "https://youtube.com/watch?v=VIDEO_ID" \
  --output "my-summaries/interesting-talk.md"
```

### Choose Summary Format

```bash
# Concise format (quick overview)
python -m src.cli "VIDEO_URL" --format concise

# Detailed format (comprehensive, default)
python -m src.cli "VIDEO_URL" --format detailed

# Academic format (structured notes)
python -m src.cli "VIDEO_URL" --format academic

# Bullet points (rapid-fire takeaways)
python -m src.cli "VIDEO_URL" --format bullet_points
```

---

## Advanced Features

### Extended Thinking Mode

Enable Claude's extended thinking for deeper analysis:

```bash
python -m src.cli "VIDEO_URL" --extended-thinking

# With custom thinking budget
python -m src.cli "VIDEO_URL" \
  --extended-thinking \
  --thinking-budget 8192
```

**Use when**:
- Video has complex technical content
- Need deep reasoning and analysis
- Want transparent thought process

### Custom Claude Model

```bash
python -m src.cli "VIDEO_URL" --model claude-opus-4-20250514
```

### Language Options

```bash
# Prefer Spanish transcript, fallback to English
python -m src.cli "VIDEO_URL" --language es en

# Translate to English
python -m src.cli "VIDEO_URL" --translation en
```

### Batch Processing

```bash
# Process multiple videos
python -m src.cli \
  "https://youtube.com/watch?v=video1" \
  "https://youtube.com/watch?v=video2" \
  "https://youtube.com/watch?v=video3" \
  --batch

# Continue on errors
python -m src.cli URL1 URL2 URL3 --batch --verbose
```

---

## Understanding Formats

### Concise Format

**Best for**: Quick overview, deciding if video is worth watching

**Includes**:
- Executive summary (2-3 sentences)
- 5-7 key takeaways
- Main topics (3-5 items)
- Target audience

**Example output**:
```markdown
# Video Summary: Introduction to Machine Learning

## Executive Summary
This video provides a beginner-friendly introduction to machine learning...

## Key Takeaways
- Machine learning enables computers to learn from data
- Three main types: supervised, unsupervised, reinforcement
- ...

## Main Topics
- Supervised Learning
- Neural Networks
- Real-world Applications

## Target Audience
Beginners with basic programming knowledge
```

### Detailed Format (Default)

**Best for**: Comprehensive understanding, reference material

**Includes**:
- Executive summary
- 8-12 key points with timestamps
- Detailed section-by-section breakdown
- All topics covered
- Notable quotes with timestamps
- Resources and references mentioned
- Target audience

**Example**:
```markdown
# Video Summary: Advanced React Patterns

## Metadata
- Video ID: abc123
- URL: https://youtube.com/watch?v=abc123
- Channel: React Experts
- Duration: 45:30
- Published: 2025-01-15

## Executive Summary
This talk explores advanced React patterns including render props...

## Key Points
- **[00:05:23]** - Introduction to render props pattern
- **[00:12:45]** - Higher-order components vs hooks
- ...

## Detailed Summary

### Introduction ([00:00:00] - [00:05:00])
Speaker introduces the motivation for advanced patterns...

### Render Props Pattern ([00:05:00] - [00:15:30])
Detailed explanation of render props...

## Notable Quotes
> "Composition is better than inheritance in React" — [00:18:30]

## Resources Mentioned
- React Documentation (https://react.dev)
- Kent C. Dodds blog
```

### Academic Format

**Best for**: Course notes, technical learning, research

**Includes**:
- Abstract-style overview
- Main concepts with definitions
- Methodology/approach analysis
- Practical applications
- Key findings/insights
- Resources & references
- Discussion points for further exploration

**Example**:
```markdown
# Course Notes: Quantum Computing Fundamentals

## Overview
This lecture covers the foundational principles of quantum computing...

## Main Concepts

### Concept 1: Superposition
- **Definition**: A quantum state existing in multiple states simultaneously
- **Timestamp**: [00:08:15]
- **Explanation**: Unlike classical bits which are either 0 or 1...
- **Example**: Schrödinger's cat thought experiment

### Concept 2: Entanglement
...

## Practical Applications
- Cryptography ([00:25:00])
- Drug discovery ([00:32:15])

## Discussion Points
- How does decoherence limit quantum computers?
- What are the implications for current encryption standards?
```

### Bullet Points Format

**Best for**: Quick reference, time-constrained review

**Includes**:
- One-sentence TL;DR
- 15-20 concise bullet points
- Topics list
- Resources

**Example**:
```markdown
# Docker Tutorial - Quick Summary

**TL;DR**: Complete guide to Docker containerization from basics to deployment.

## Main Points
- Docker solves "works on my machine" problem ([00:02:30])
- Container vs VM: containers share OS kernel ([00:05:15])
- Dockerfile defines container image ([00:12:00])
- docker-compose.yml for multi-container apps ([00:25:40])
- ...

## Topics
- Containers
- Images
- Volumes
- Networks

## Resources
- Docker Hub
- Official Documentation
```

---

## Chunking Strategies

### When to Use Each Strategy

| Video Length | Recommended Strategy | Reasoning |
|--------------|---------------------|-----------|
| < 10 minutes | `none` | Fits in Claude's context window |
| 10-30 minutes | `recursive` or `auto` | Balanced approach |
| 30+ minutes | `semantic` or `auto` | Topic-based segmentation |
| Structured lectures | `semantic` | Preserves topic boundaries |
| Interviews/podcasts | `recursive` | Natural conversation flow |

### Auto Strategy (Recommended)

```bash
python -m src.cli "VIDEO_URL" --chunking auto
```

Automatically selects best strategy based on video length.

### No Chunking

```bash
python -m src.cli "VIDEO_URL" --chunking none
```

Uses full transcript in single pass. Best for:
- Short videos (< 10 minutes)
- Videos that fit in 200K context window
- When you want Claude to see full context

### Recursive Chunking

```bash
python -m src.cli "VIDEO_URL" \
  --chunking recursive \
  --chunk-size 1000 \
  --chunk-overlap 200
```

Splits on natural boundaries (paragraphs → sentences → words).

**Parameters**:
- `--chunk-size`: Maximum tokens per chunk (default: 1000)
- `--chunk-overlap`: Overlap between chunks (default: 200)

**Best for**:
- General content
- Interviews and discussions
- Medium-length videos (10-30 min)

### Semantic Chunking

```bash
python -m src.cli "VIDEO_URL" --chunking semantic
```

Splits based on semantic similarity (topic changes).

**Requirements**:
```bash
pip install langchain-experimental langchain-openai
# Set OPENAI_API_KEY in .env
```

**Best for**:
- Structured lectures
- Technical tutorials
- Long videos with distinct topics
- Educational content

**Note**: Uses OpenAI embeddings to determine topic boundaries.

### Timestamp Chunking

```bash
python -m src.cli "VIDEO_URL" --chunking timestamp
```

Splits by time intervals (default: 5 minutes).

**Best for**:
- Very long videos (> 1 hour)
- When you want time-based navigation
- Consistent chunk sizes

---

## Best Practices

### 1. Choose the Right Format

- **Quick decision**: Use `concise`
- **Deep learning**: Use `academic`
- **General reference**: Use `detailed`
- **Rapid review**: Use `bullet_points`

### 2. Leverage Auto Chunking

Start with `--chunking auto` and only override if needed:
```bash
python -m src.cli "VIDEO_URL" --chunking auto
```

### 3. Use Extended Thinking for Complex Content

Enable for:
- Technical talks
- Scientific presentations
- Complex analysis

```bash
python -m src.cli "VIDEO_URL" \
  --format academic \
  --extended-thinking \
  --chunking semantic
```

### 4. Batch Process Related Videos

```bash
# Create a video list file
echo "https://youtube.com/watch?v=video1" > videos.txt
echo "https://youtube.com/watch?v=video2" >> videos.txt

# Process all
cat videos.txt | xargs python -m src.cli --batch
```

### 5. Organize Outputs

```bash
# Organize by topic
python -m src.cli "VIDEO_URL" -o summaries/machine-learning/intro.md

# Organize by date
python -m src.cli "VIDEO_URL" -o summaries/2025-10/react-talk.md
```

---

## Troubleshooting

### Problem: "No transcript available"

**Cause**: Video doesn't have captions

**Solutions**:
1. Check if video has captions (click CC button on YouTube)
2. Try different language: `--language en es fr`
3. Some videos are region-locked or age-restricted

### Problem: "ANTHROPIC_API_KEY not set"

**Cause**: API key not configured

**Solution**:
```bash
# Create .env file
cp .env.example .env

# Edit .env and add key
echo "ANTHROPIC_API_KEY=your_key_here" >> .env
```

### Problem: Semantic chunking fails

**Cause**: Missing optional dependencies or API key

**Solution**:
```bash
# Install dependencies
pip install langchain-experimental langchain-openai

# Add OpenAI key to .env
echo "OPENAI_API_KEY=your_key_here" >> .env

# Or use different chunking
python -m src.cli "VIDEO_URL" --chunking recursive
```

### Problem: Summary quality is poor

**Causes & Solutions**:
1. **Auto-generated captions**: Poor quality transcript
   - Check if manual captions available
   - Note: Tool will indicate if auto-generated

2. **Wrong chunking**: Lost context between chunks
   - Try: `--chunking none` for full context
   - Try: `--chunking semantic` for topic preservation

3. **Wrong format**: Format doesn't match use case
   - Use `detailed` for comprehensive summaries
   - Use `academic` for structured learning

4. **Complex content**: Needs deeper analysis
   - Add: `--extended-thinking`
   - Increase: `--thinking-budget 8192`

### Problem: Rate limits

**Cause**: Too many API calls

**Solutions**:
1. Add delays between batch videos
2. Use `--chunking none` to reduce API calls
3. Check Anthropic dashboard for rate limits

### Problem: Out of memory

**Cause**: Very long video with no chunking

**Solution**:
```bash
# Force chunking
python -m src.cli "VIDEO_URL" --chunking semantic

# Or use smaller chunks
python -m src.cli "VIDEO_URL" \
  --chunking recursive \
  --chunk-size 500
```

---

## Example Workflows

### Workflow 1: Research Paper Summary

```bash
# Academic paper video
python -m src.cli "https://youtube.com/watch?v=paper_talk" \
  --format academic \
  --chunking semantic \
  --extended-thinking \
  -o docs/research/paper-summary.md
```

### Workflow 2: Tutorial Series

```bash
# Process entire tutorial series
python -m src.cli \
  "URL1" "URL2" "URL3" "URL4" "URL5" \
  --batch \
  --format detailed \
  --chunking auto
```

### Workflow 3: Conference Talk

```bash
# 45-minute tech conference talk
python -m src.cli "https://youtube.com/watch?v=conf_talk" \
  --format detailed \
  --chunking semantic \
  --chunk-size 1500 \
  -o summaries/conferences/pycon-2025-talk.md
```

### Workflow 4: Quick Video Screening

```bash
# Decide if worth watching
python -m src.cli "https://youtube.com/watch?v=video" \
  --format concise \
  --chunking none
```

### Workflow 5: Multilingual Content

```bash
# Spanish video, translate to English
python -m src.cli "https://youtube.com/watch?v=spanish_vid" \
  --language es \
  --translation en \
  --format detailed
```

---

## Tips & Tricks

### Tip 1: Create Aliases

Add to `.bashrc` or `.zshrc`:
```bash
alias ytsum='python -m src.cli'
alias ytsum-quick='python -m src.cli --format concise'
alias ytsum-deep='python -m src.cli --format academic --extended-thinking'
```

Usage:
```bash
ytsum-quick "VIDEO_URL"
ytsum-deep "VIDEO_URL"
```

### Tip 2: Automate with Scripts

Create `summarize_playlist.sh`:
```bash
#!/bin/bash
# Summarize all videos in a list
while read url; do
    python -m src.cli "$url" --batch --format detailed
    sleep 2  # Rate limiting
done < video_urls.txt
```

### Tip 3: Compare Formats

```bash
# Generate multiple formats
for format in concise detailed academic bullet_points; do
    python -m src.cli "VIDEO_URL" \
      --format $format \
      -o "summaries/${format}-summary.md"
done
```

### Tip 4: Use Verbose Mode for Debugging

```bash
python -m src.cli "VIDEO_URL" --verbose
```

---

## Next Steps

1. **Explore Examples**: Try different formats and chunking strategies
2. **Read Research**: Check `docs/LANGCHAIN_RESEARCH.md` for deep dive
3. **Customize**: Modify `src/summarizer.py` for custom prompts
4. **Contribute**: See README for contribution guidelines

---

**Need help?** Check the [README](README.md) or create an issue on GitHub.

**Generated with**: [Claude Code](https://claude.com/claude-code)
