"""Data models for YouTube video summarization."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class TranscriptSegment(BaseModel):
    """A single segment of transcript with timestamp."""

    text: str
    start: float  # seconds
    duration: float  # seconds

    @property
    def end(self) -> float:
        """End time of segment."""
        return self.start + self.duration

    def format_timestamp(self, seconds: float) -> str:
        """Format seconds as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    @property
    def start_timestamp(self) -> str:
        """Formatted start timestamp."""
        return self.format_timestamp(self.start)

    @property
    def end_timestamp(self) -> str:
        """Formatted end timestamp."""
        return self.format_timestamp(self.end)


class VideoMetadata(BaseModel):
    """Metadata about a YouTube video."""

    video_id: str
    title: Optional[str] = None
    channel: Optional[str] = None
    duration: Optional[int] = None  # seconds
    publish_date: Optional[str] = None
    view_count: Optional[int] = None
    description: Optional[str] = None
    url: str

    @property
    def duration_formatted(self) -> Optional[str]:
        """Formatted duration as HH:MM:SS."""
        if self.duration is None:
            return None

        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"


class VideoTranscript(BaseModel):
    """Complete transcript for a video."""

    metadata: VideoMetadata
    segments: list[TranscriptSegment]
    language: str
    is_auto_generated: bool = False

    @property
    def full_text(self) -> str:
        """Full transcript as single text."""
        return " ".join(segment.text for segment in self.segments)

    @property
    def full_text_with_timestamps(self) -> str:
        """Full transcript with timestamps."""
        lines = []
        for segment in self.segments:
            lines.append(f"[{segment.start_timestamp}] {segment.text}")
        return "\n".join(lines)


class SummaryFormat(BaseModel):
    """Format specification for summary output."""

    format_type: str = Field(
        default="detailed",
        description="Type of summary: concise, detailed, academic, bullet_points",
    )
    include_timestamps: bool = True
    include_metadata: bool = True
    include_key_points: bool = True
    include_quotes: bool = True
    include_resources: bool = True


class VideoSummary(BaseModel):
    """Generated summary for a video."""

    metadata: VideoMetadata
    executive_summary: str
    key_points: list[str]
    detailed_summary: str
    topics_covered: list[str]
    notable_quotes: Optional[list[str]] = None
    resources_mentioned: Optional[list[str]] = None
    target_audience: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.now)

    def to_markdown(self, format_type: str = "detailed") -> str:
        """Convert summary to markdown format."""
        lines = [
            f"# Video Summary: {self.metadata.title or self.metadata.video_id}",
            "",
            "## Metadata",
            f"- **Video ID**: {self.metadata.video_id}",
            f"- **URL**: {self.metadata.url}",
        ]

        if self.metadata.channel:
            lines.append(f"- **Channel**: {self.metadata.channel}")
        if self.metadata.duration_formatted:
            lines.append(f"- **Duration**: {self.metadata.duration_formatted}")
        if self.metadata.publish_date:
            lines.append(f"- **Published**: {self.metadata.publish_date}")
        if self.metadata.view_count:
            lines.append(f"- **Views**: {self.metadata.view_count:,}")

        lines.extend(
            [
                "",
                "## Executive Summary",
                self.executive_summary,
                "",
                "## Key Points",
            ]
        )

        for point in self.key_points:
            lines.append(f"- {point}")

        if format_type in ["detailed", "academic"]:
            lines.extend(["", "## Detailed Summary", self.detailed_summary])

        lines.extend(["", "## Topics Covered"])
        for topic in self.topics_covered:
            lines.append(f"- {topic}")

        if self.notable_quotes:
            lines.extend(["", "## Notable Quotes"])
            for quote in self.notable_quotes:
                lines.append(f"> {quote}")
                lines.append("")

        if self.resources_mentioned:
            lines.extend(["", "## Resources Mentioned"])
            for resource in self.resources_mentioned:
                lines.append(f"- {resource}")

        if self.target_audience:
            lines.extend(["", "## Target Audience", self.target_audience])

        lines.extend(
            [
                "",
                "---",
                f"**Summary Generated**: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
                f"**Original Video**: {self.metadata.url}",
            ]
        )

        return "\n".join(lines)
