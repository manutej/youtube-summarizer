"""Command-line interface for YouTube video summarizer."""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .chunkers import ChunkingStrategy, TranscriptChunker, recommend_chunking_strategy
from .config import config
from .extractors import BatchTranscriptExtractor, TranscriptExtractor, YouTubeURLParser
from .models import VideoMetadata
from .summarizer import ClaudeSummarizer

# Initialize rich console
console = Console()


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

    # Generate markdown content
    markdown_content = summary.to_markdown(format_type=args.format)

    # Display in console with rich formatting
    console.print("\n")
    console.print(Panel(
        Markdown(markdown_content),
        title=f"📺 [bold cyan]{title}[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print("\n")

    # Save to file
    output_path = determine_output_path(args, transcript.metadata)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"  └─ ✓ Saved to: {output_path}")
    print(f"  └─ ✅ Complete!")


def create_playlist_index(
    playlist_title: str,
    playlist_url: str,
    video_summaries: list[tuple[Path, VideoMetadata]],
    output_dir: Path,
) -> Path:
    """Create a playlist index/table of contents."""
    index_path = output_dir / f"_PLAYLIST_INDEX_{sanitize_filename(playlist_title)}.md"

    lines = [
        f"# {playlist_title}",
        "",
        f"**Playlist URL**: {playlist_url}",
        f"**Total Videos**: {len(video_summaries)}",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## Video Summaries",
        "",
    ]

    for idx, (file_path, metadata) in enumerate(video_summaries, 1):
        title = metadata.title or metadata.video_id
        duration = metadata.duration_formatted or "Unknown"
        relative_path = file_path.name

        lines.append(f"### {idx}. {title}")
        lines.append(f"- **Duration**: {duration}")
        lines.append(f"- **Video URL**: {metadata.url}")
        lines.append(f"- **Summary**: [{relative_path}](./{relative_path})")
        lines.append("")

    lines.extend([
        "---",
        "",
        f"**Index Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "**Generated with**: [Claude Code](https://claude.com/claude-code)",
    ])

    with open(index_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    return index_path


def process_playlist(
    playlist_url: str,
    extractor: TranscriptExtractor,
    summarizer: ClaudeSummarizer,
    args,
) -> None:
    """Process an entire playlist."""
    print(f"\n📺 Processing Playlist: {playlist_url}")

    # Extract playlist info using yt-dlp
    try:
        import yt_dlp

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)
            playlist_title = playlist_info.get('title', 'Unknown Playlist')
            playlist_count = len(playlist_info.get('entries', []))

        print(f"  └─ Playlist: {playlist_title}")
        print(f"  └─ Videos: {playlist_count}")

    except Exception as e:
        print(f"  └─ ⚠️  Could not fetch playlist metadata: {e}")
        playlist_title = "Unknown Playlist"

    # Extract transcripts from playlist
    print(f"  └─ Extracting transcripts...")
    batch_extractor = BatchTranscriptExtractor(extractor)

    try:
        results = batch_extractor.extract_from_playlist(playlist_url, continue_on_error=True)
    except Exception as e:
        print(f"  └─ ❌ Failed to process playlist: {e}")
        return

    # Process each video
    successful = 0
    failed = 0
    video_summaries = []

    for video_url, result in results.items():
        if isinstance(result, Exception):
            print(f"\n  ❌ Failed: {video_url}")
            print(f"     Error: {result}")
            failed += 1
            continue

        try:
            # Process transcript
            transcript = result
            video_id = transcript.metadata.video_id
            title = transcript.metadata.title or video_id

            print(f"\n  📹 Processing: {title}")

            # Determine chunking
            chunking_strategy = determine_chunking_strategy(args, transcript)

            # Generate summary
            if chunking_strategy == ChunkingStrategy.NONE:
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

            # Save individual video summary
            output_path = determine_output_path(args, transcript.metadata)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            markdown_content = summary.to_markdown(format_type=args.format)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            print(f"     └─ ✓ Saved: {output_path}")
            video_summaries.append((output_path, transcript.metadata))
            successful += 1

        except Exception as e:
            print(f"     └─ ❌ Error: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            failed += 1

    # Create playlist index
    if video_summaries:
        output_dir = video_summaries[0][0].parent
        index_path = create_playlist_index(playlist_title, playlist_url, video_summaries, output_dir)
        print(f"\n  📋 Created playlist index: {index_path}")

    # Summary
    print(f"\n  {'='*50}")
    print(f"  📊 Playlist Summary:")
    print(f"     ✅ Successful: {successful}")
    print(f"     ❌ Failed: {failed}")
    print(f"     📁 Total: {successful + failed}")


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

    # Check if any URL is a playlist
    playlist_urls = [url for url in args.urls if YouTubeURLParser.is_playlist_url(url)]
    video_urls = [url for url in args.urls if not YouTubeURLParser.is_playlist_url(url)]

    # Process playlists
    for playlist_url in playlist_urls:
        process_playlist(playlist_url, extractor, summarizer, args)

    # Process videos
    if video_urls:
        if args.batch or len(video_urls) > 1:
            print(f"\n📦 Batch processing {len(video_urls)} videos")
            batch_extractor = BatchTranscriptExtractor(extractor)

            for url in video_urls:
                try:
                    process_single_video(url, extractor, summarizer, args)
                except Exception as e:
                    print(f"  └─ ❌ Error processing {url}: {e}")
                    if args.verbose:
                        import traceback

                        traceback.print_exc()
        else:
            # Single video
            process_single_video(video_urls[0], extractor, summarizer, args)

    print("\n" + "=" * 50)
    print("✨ All done!")


if __name__ == '__main__':
    main()
