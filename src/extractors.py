"""Transcript extraction using LangChain and youtube-transcript-api."""

import re
from typing import Optional
from urllib.parse import parse_qs, urlparse

from langchain_community.document_loaders import YoutubeLoader
from langchain_core.documents import Document

from .config import config
from .models import TranscriptSegment, VideoMetadata, VideoTranscript


class YouTubeURLParser:
    """Parse YouTube URLs to extract video IDs and playlist IDs."""

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """
        Extract video ID from various YouTube URL formats.

        Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/v/VIDEO_ID
        """
        # Handle direct video ID
        if len(url) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url

        # Parse URL
        parsed_url = urlparse(url)

        # Standard watch URL
        if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
            if parsed_url.path == '/watch':
                query = parse_qs(parsed_url.query)
                return query.get('v', [None])[0]
            # Embed format
            elif parsed_url.path.startswith('/embed/'):
                return parsed_url.path.split('/')[2]
            # /v/ format
            elif parsed_url.path.startswith('/v/'):
                return parsed_url.path.split('/')[2]

        # Shortened URL
        elif parsed_url.hostname in ['youtu.be']:
            return parsed_url.path.lstrip('/')

        return None

    @staticmethod
    def extract_playlist_id(url: str) -> Optional[str]:
        """
        Extract playlist ID from YouTube playlist URL.

        Supports:
        - https://www.youtube.com/playlist?list=PLAYLIST_ID
        - https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID
        """
        parsed_url = urlparse(url)

        if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
            query = parse_qs(parsed_url.query)
            return query.get('list', [None])[0]

        return None

    @staticmethod
    def is_playlist_url(url: str) -> bool:
        """Check if URL is a playlist URL."""
        playlist_id = YouTubeURLParser.extract_playlist_id(url)
        return playlist_id is not None


class TranscriptExtractor:
    """Extract transcripts from YouTube videos using LangChain."""

    def __init__(
        self,
        add_video_info: bool = True,
        language: Optional[list[str]] = None,
        translation: Optional[str] = None,
        cookies_file: Optional[str] = None,
    ):
        """
        Initialize transcript extractor.

        Args:
            add_video_info: Include video metadata
            language: Preferred transcript languages (default: ['en'])
            translation: Translate transcript to this language
            cookies_file: Path to cookies file for YouTube authentication (bypasses IP blocks)
        """
        self.add_video_info = add_video_info
        self.language = language or config.preferred_languages
        self.translation = translation
        self.cookies_file = cookies_file

    def extract_from_url(self, url: str) -> VideoTranscript:
        """
        Extract transcript from YouTube URL.

        Args:
            url: YouTube video URL or video ID

        Returns:
            VideoTranscript with metadata and segments

        Raises:
            ValueError: If video ID cannot be extracted or transcript unavailable
        """
        video_id = YouTubeURLParser.extract_video_id(url)
        if not video_id:
            raise ValueError(f"Could not extract video ID from URL: {url}")

        return self.extract_from_video_id(video_id)

    def extract_from_video_id(self, video_id: str) -> VideoTranscript:
        """
        Extract transcript from YouTube video ID.

        Args:
            video_id: YouTube video ID

        Returns:
            VideoTranscript with metadata and segments

        Raises:
            ValueError: If transcript is unavailable
        """
        # Try yt-dlp first (more reliable, bypasses IP blocks)
        try:
            return self._extract_with_ytdlp(video_id)
        except Exception as ytdlp_error:
            # Fallback to youtube-transcript-api
            try:
                from youtube_transcript_api import YouTubeTranscriptApi

                # Fetch transcript using v1.2.2+ API
                api = YouTubeTranscriptApi()
                transcript_list = api.fetch(video_id, languages=self.language)

                if not transcript_list:
                    raise ValueError(f"No transcript found for video: {video_id}")

                # Extract segments (returns FetchedTranscriptSnippet objects)
                segments = [
                    TranscriptSegment(
                        text=item.text,
                        start=item.start,
                        duration=item.duration,
                    )
                    for item in transcript_list
                ]

                # Get metadata
                metadata = self._extract_metadata_simple(video_id)

                # Detect language from first segment or use default
                language = self.language[0] if self.language else 'en'

                # Simple heuristic for auto-generated detection
                is_auto_generated = True  # Most transcripts are auto-generated

                return VideoTranscript(
                    metadata=metadata,
                    segments=segments,
                    language=language,
                    is_auto_generated=is_auto_generated,
                )

            except Exception as api_error:
                raise ValueError(f"Failed to extract transcript for {video_id} using both methods. yt-dlp error: {ytdlp_error}, API error: {api_error}")

    def _extract_with_ytdlp(self, video_id: str) -> VideoTranscript:
        """Extract transcript using yt-dlp (more reliable, bypasses IP blocks)."""
        import yt_dlp
        import tempfile
        import os
        import json

        url = f"https://www.youtube.com/watch?v={video_id}"

        # Create temp directory for subtitle download
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': self.language or ['en'],
                'subtitlesformat': 'json3',
                'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
            }

            # Add cookies if provided
            if self.cookies_file:
                ydl_opts['cookiefile'] = self.cookies_file

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # Download subtitles
                ydl.download([url])

                # Find the downloaded subtitle file
                lang_key = self.language[0] if self.language else 'en'
                subtitle_file = os.path.join(tmpdir, f"{video_id}.{lang_key}.json3")

                # Try variations
                if not os.path.exists(subtitle_file):
                    # Try without language code
                    subtitle_file = os.path.join(tmpdir, f"{video_id}.json3")

                if not os.path.exists(subtitle_file):
                    # Look for any json3 file
                    files = [f for f in os.listdir(tmpdir) if f.endswith('.json3')]
                    if files:
                        subtitle_file = os.path.join(tmpdir, files[0])
                    else:
                        raise ValueError(f"No subtitle file downloaded for {video_id}")

                # Read and parse subtitle file
                with open(subtitle_file, 'r', encoding='utf-8') as f:
                    subtitle_json = json.load(f)

                # Parse segments from JSON3 format
                segments = []
                for event in subtitle_json.get('events', []):
                    if 'segs' in event:
                        text = ''.join(seg.get('utf8', '') for seg in event['segs'])
                        if text.strip():
                            segments.append(TranscriptSegment(
                                text=text.strip(),
                                start=event.get('tStartMs', 0) / 1000.0,
                                duration=event.get('dDurationMs', 0) / 1000.0,
                            ))

                if not segments:
                    raise ValueError(f"No transcript segments found for {video_id}")

                # Get metadata
                metadata = VideoMetadata(
                    video_id=video_id,
                    title=info.get('title'),
                    channel=info.get('uploader') or info.get('channel'),
                    duration=info.get('duration'),
                    publish_date=info.get('upload_date'),
                    view_count=info.get('view_count'),
                    description=info.get('description'),
                    url=url,
                )

                return VideoTranscript(
                    metadata=metadata,
                    segments=segments,
                    language=lang_key,
                    is_auto_generated=True,
                )

    def _extract_metadata_simple(self, video_id: str) -> VideoMetadata:
        """Extract video metadata using yt-dlp."""
        try:
            import yt_dlp

            # Configure yt-dlp for fast metadata extraction only
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
            }

            url = f"https://www.youtube.com/watch?v={video_id}"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                return VideoMetadata(
                    video_id=video_id,
                    title=info.get('title'),
                    channel=info.get('uploader') or info.get('channel'),
                    duration=info.get('duration'),  # seconds
                    publish_date=info.get('upload_date'),  # YYYYMMDD format
                    view_count=info.get('view_count'),
                    description=info.get('description'),
                    url=url,
                )
        except Exception as e:
            # Fallback to basic metadata if yt-dlp fails
            return VideoMetadata(
                video_id=video_id,
                title=f"YouTube Video {video_id}",
                channel=None,
                duration=None,
                publish_date=None,
                view_count=None,
                description=None,
                url=f"https://www.youtube.com/watch?v={video_id}",
            )

    def _extract_segments(self, doc: Document) -> list[TranscriptSegment]:
        """
        Extract transcript segments from document.

        Note: LangChain's YoutubeLoader returns full transcript as single text.
        To get timestamped segments, we need to use youtube-transcript-api directly.
        """
        # Import here to avoid circular dependency issues
        from youtube_transcript_api import YouTubeTranscriptApi

        video_id = doc.metadata.get('source', '').split('=')[-1]

        try:
            # Get raw transcript with timestamps using v1.2.2+ API
            api = YouTubeTranscriptApi()
            transcript_list = api.fetch(video_id, languages=self.language)

            segments = [
                TranscriptSegment(
                    text=item.text,
                    start=item.start,
                    duration=item.duration,
                )
                for item in transcript_list
            ]

            return segments

        except Exception:
            # Fallback: create single segment from full text
            return [
                TranscriptSegment(
                    text=doc.page_content,
                    start=0.0,
                    duration=doc.metadata.get('length', 0.0),
                )
            ]

    def _is_auto_generated(self, doc: Document) -> bool:
        """Determine if transcript is auto-generated."""
        # Check metadata or transcript characteristics
        # LangChain doesn't expose this directly, so we infer
        source = doc.metadata.get('source', '')
        description = doc.metadata.get('description', '')

        # Heuristic: check for common auto-generated indicators
        return 'auto-generated' in description.lower() or 'automatic' in source.lower()


class BatchTranscriptExtractor:
    """Extract transcripts from multiple videos."""

    def __init__(self, extractor: Optional[TranscriptExtractor] = None):
        """
        Initialize batch extractor.

        Args:
            extractor: TranscriptExtractor instance (creates default if None)
        """
        self.extractor = extractor or TranscriptExtractor()

    def extract_from_urls(
        self, urls: list[str], continue_on_error: bool = True
    ) -> dict[str, VideoTranscript | Exception]:
        """
        Extract transcripts from multiple URLs.

        Args:
            urls: List of YouTube URLs
            continue_on_error: Continue processing if a video fails

        Returns:
            Dict mapping URL to VideoTranscript or Exception
        """
        results = {}

        for url in urls:
            try:
                transcript = self.extractor.extract_from_url(url)
                results[url] = transcript
            except Exception as e:
                if continue_on_error:
                    results[url] = e
                else:
                    raise

        return results

    def extract_from_playlist(
        self, playlist_url: str, continue_on_error: bool = True
    ) -> dict[str, VideoTranscript | Exception]:
        """
        Extract transcripts from all videos in a playlist.

        Args:
            playlist_url: YouTube playlist URL
            continue_on_error: Continue processing if a video fails

        Returns:
            Dict mapping video URL to VideoTranscript or Exception
        """
        try:
            import yt_dlp
        except ImportError:
            raise ImportError("yt-dlp is required for playlist support. Install with: pip install yt-dlp")

        # Extract playlist information
        playlist_id = YouTubeURLParser.extract_playlist_id(playlist_url)
        if not playlist_id:
            raise ValueError(f"Could not extract playlist ID from URL: {playlist_url}")

        # Configure yt-dlp to extract playlist entries
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Don't download, just get URLs
            'skip_download': True,
        }

        video_urls = []

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)

                if 'entries' not in playlist_info:
                    raise ValueError(f"No videos found in playlist: {playlist_url}")

                # Extract video URLs from playlist
                for entry in playlist_info['entries']:
                    if entry and 'id' in entry:
                        video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                        video_urls.append(video_url)

        except Exception as e:
            raise ValueError(f"Failed to extract playlist information: {e}")

        if not video_urls:
            raise ValueError(f"No videos found in playlist: {playlist_url}")

        # Use existing batch extraction
        return self.extract_from_urls(video_urls, continue_on_error=continue_on_error)
