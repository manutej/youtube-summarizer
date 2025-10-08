"""Command-line interface for YouTube video summarizer."""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

from .chunkers import ChunkingStrategy, TranscriptChunker, recommend_chunking_strategy
from .config import config
from .extractors import BatchTranscriptExtractor, TranscriptExtractor
from .models import VideoMetadata
from .summarizer import ClaudeSummarizer


def setup_argparser() -> argparse.ArgumentParser:
    """Set up command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="YouTube Video Summarizer - Transform videos into LLM-friendly summaries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Summarize single video
  python -m src.cli https://youtube.com/watch?v=VIDEO_ID

  # Detailed format with output file
  python -m src.cli https://youtube.com/watch?v=VIDEO_ID --format detailed --output summaries/video.md

  # Multiple videos
  python -m src.cli URL1 URL2 URL3 --batch

  # Use semantic chunking for long video
  python -m src.cli https://youtube.com/watch?v=VIDEO_ID --chunking semantic

  # Enable extended thinking
  python -m src.cli https://youtube.com/watch?v=VIDEO_ID --extended-thinking
        """,
    )

    # Positional arguments
    parser.add_argument(
        'urls',
        nargs='+',
        help='YouTube video URL(s) or video ID(s)',
    )

    # Output options
    parser.add_argument(
        '-o',
        '--output',
        type=str,
        help='Output file path (default: summaries/<video_id>.md)',
    )

    parser.add_argument(
        '-f',
        '--format',
        choices=['concise', 'detailed', 'academic', 'bullet_points'],
        default='detailed',
        help='Summary format (default: detailed)',
    )

    # Processing options
    parser.add_argument(
        '--chunking',
        choices=['none', 'recursive', 'semantic', 'timestamp', 'auto'],
        default='auto',
        help='Chunking strategy (default: auto - recommends based on video length)',
    )

    parser.add_argument(
        '--chunk-size',
        type=int,
        default=1000,
        help='Chunk size in tokens (default: 1000)',
    )

    parser.add_argument(
        '--chunk-overlap',
        type=int,
        default=200,
        help='Chunk overlap in tokens (default: 200)',
    )

    # LLM options
    parser.add_argument(
        '--model',
        type=str,
        default=None,
        help=f'Claude model to use (default: {config.claude_model})',
    )

    parser.add_argument(
        '--extended-thinking',
        action='store_true',
        help='Enable extended thinking mode for deeper analysis',
    )

    parser.add_argument(
        '--thinking-budget',
        type=int,
        default=4096,
        help='Token budget for extended thinking (default: 4096)',
    )

    # Transcript options
    parser.add_argument(
        '--language',
        nargs='+',
        default=['en'],
        help='Preferred transcript languages (default: en)',
    )

    parser.add_argument(
        '--translation',
        type=str,
        help='Translate transcript to this language',
    )

    # Batch processing
    parser.add_argument(
        '--batch',
        action='store_true',
        help='Process multiple videos (continue on error)',
    )

    # Verbosity
    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        help='Verbose output',
    )

    return parser


def determine_chunking_strategy(args, transcript) -> ChunkingStrategy:
    """Determine chunking strategy from args."""
    if args.chunking == 'auto':
        return recommend_chunking_strategy(transcript)
    else:
        return ChunkingStrategy(args.chunking)


def sanitize_filename(text: str) -> str:
    """Sanitize text for use in filename."""
    # Remove or replace invalid filename characters
    text = re.sub(r'[<>:"/\\|?*]', '', text)
    # Replace spaces and multiple dashes with single dash
    text = re.sub(r'[\s_]+', '-', text)
    # Remove leading/trailing dashes and dots
    text = text.strip('.-')
    # Limit length
    return text[:100]


def determine_output_path(args, metadata: VideoMetadata) -> Path:
    """Determine output file path with channel and title."""
    if args.output:
        return Path(args.output)

    config.ensure_directories()

    # Build filename: {channel}/{title}_{video_id}.md
    video_id = metadata.video_id

    # Sanitize channel name for directory
    if metadata.channel:
        channel_dir = sanitize_filename(metadata.channel)
        base_dir = config.output_dir / channel_dir
    else:
        base_dir = config.output_dir

    # Sanitize title for filename
    if metadata.title and metadata.title != f"YouTube Video {video_id}":
        title_part = sanitize_filename(metadata.title)
        filename = f"{title_part}_{video_id}.md"
    else:
        filename = f"{video_id}.md"

    return base_dir / filename


def process_single_video(
    url: str,
    extractor: TranscriptExtractor,
    summarizer: ClaudeSummarizer,
    args,
) -> None:
    """Process a single video."""
    print(f"\n📹 Processing: {url}")

    # Extract transcript
    print("  └─ Extracting transcript...")
    try:
        transcript = extractor.extract_from_url(url)
    except Exception as e:
        print(f"  └─ ❌ Failed to extract transcript: {e}")
        return

    video_id = transcript.metadata.video_id
    title = transcript.metadata.title or video_id
    duration = transcript.metadata.duration_formatted or "Unknown"

    print(f"  └─ ✓ Title: {title}")
    print(f"  └─ ✓ Duration: {duration}")
    print(f"  └─ ✓ Language: {transcript.language}")

    # Determine chunking strategy
    chunking_strategy = determine_chunking_strategy(args, transcript)
    print(f"  └─ Chunking strategy: {chunking_strategy.value}")

    # Chunk if needed
    if chunking_strategy == ChunkingStrategy.NONE:
        print("  └─ Using full transcript (no chunking)")
        summary = summarizer.summarize_transcript(
            transcript,
            format_type=args.format,
        )
    else:
        chunker = TranscriptChunker(
            strategy=chunking_strategy,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        chunks = chunker.chunk_transcript(transcript)
        num_chunks = len(chunks) if isinstance(chunks, list) else 1
        print(f"  └─ Created {num_chunks} chunks")

        print("  └─ Summarizing with Claude...")
        if isinstance(chunks, list):
            summary = summarizer.summarize_chunks(
                chunks,
                transcript,
                format_type=args.format,
            )
        else:
            summary = summarizer.summarize_transcript(
                transcript,
                format_type=args.format,
            )

    print("  └─ ✓ Summary generated")

    # Save to file
    output_path = determine_output_path(args, transcript.metadata)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    markdown_content = summary.to_markdown(format_type=args.format)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"  └─ ✓ Saved to: {output_path}")
    print(f"  └─ ✅ Complete!")


def main():
    """Main CLI entry point."""
    parser = setup_argparser()
    args = parser.parse_args()

    # Validate API key
    if not config.validate_api_key():
        print("❌ Error: ANTHROPIC_API_KEY not set")
        print("Please set it in .env file or as environment variable")
        sys.exit(1)

    # Initialize components
    print("🚀 YouTube Video Summarizer")
    print("=" * 50)

    extractor = TranscriptExtractor(
        add_video_info=True,
        language=args.language,
        translation=args.translation,
    )

    summarizer = ClaudeSummarizer(
        model=args.model,
        use_extended_thinking=args.extended_thinking,
        thinking_budget=args.thinking_budget,
    )

    # Process videos
    if args.batch or len(args.urls) > 1:
        print(f"\n📦 Batch processing {len(args.urls)} videos")
        batch_extractor = BatchTranscriptExtractor(extractor)

        for url in args.urls:
            try:
                process_single_video(url, extractor, summarizer, args)
            except Exception as e:
                print(f"  └─ ❌ Error processing {url}: {e}")
                if args.verbose:
                    import traceback

                    traceback.print_exc()
    else:
        # Single video
        process_single_video(args.urls[0], extractor, summarizer, args)

    print("\n" + "=" * 50)
    print("✨ All done!")


if __name__ == '__main__':
    main()
