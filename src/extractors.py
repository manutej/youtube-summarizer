"""Transcript extraction using LangChain and youtube-transcript-api."""

import re
from typing import Optional
from urllib.parse import parse_qs, urlparse

from langchain_community.document_loaders import YoutubeLoader
from langchain_core.documents import Document

from .config import config
from .models import TranscriptSegment, VideoMetadata, VideoTranscript


class YouTubeURLParser:
    """Parse YouTube URLs to extract video IDs."""

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


class TranscriptExtractor:
    """Extract transcripts from YouTube videos using LangChain."""

    def __init__(
        self,
        add_video_info: bool = True,
        language: Optional[list[str]] = None,
        translation: Optional[str] = None,
    ):
        """
        Initialize transcript extractor.

        Args:
            add_video_info: Include video metadata
            language: Preferred transcript languages (default: ['en'])
            translation: Translate transcript to this language
        """
        self.add_video_info = add_video_info
        self.language = language or config.preferred_languages
        self.translation = translation

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
        try:
            # Use youtube-transcript-api directly (more reliable than LangChain + pytube)
            from youtube_transcript_api import YouTubeTranscriptApi

            # Fetch transcript
            api = YouTubeTranscriptApi()
            transcript_list = api.fetch(video_id, languages=self.language)

            if not transcript_list:
                raise ValueError(f"No transcript found for video: {video_id}")

            # Extract segments
            segments = [
                TranscriptSegment(
                    text=item.text,
                    start=item.start,
                    duration=item.duration,
                )
                for item in transcript_list
            ]

            # Get metadata (simple version without pytube which is currently broken)
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

        except Exception as e:
            raise ValueError(f"Failed to extract transcript for {video_id}: {e}")

    def _extract_metadata_simple(self, video_id: str) -> VideoMetadata:
        """Extract basic video metadata without pytube (which currently has issues)."""
        return VideoMetadata(
            video_id=video_id,
            title=f"YouTube Video {video_id}",  # Could enhance with yt-dlp or WebFetch
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
            # Get raw transcript with timestamps using new API
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

    def extract_from_playlist(self, playlist_url: str) -> dict[str, VideoTranscript | Exception]:
        """
        Extract transcripts from all videos in a playlist.

        Args:
            playlist_url: YouTube playlist URL

        Returns:
            Dict mapping video URL to VideoTranscript or Exception

        Note: Requires additional implementation for playlist parsing
        """
        # TODO: Implement playlist parsing
        # Could use pytube or yt-dlp for playlist extraction
        raise NotImplementedError("Playlist support coming soon")
