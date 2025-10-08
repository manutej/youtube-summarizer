"""Text chunking strategies for transcript processing."""

from enum import Enum
from typing import Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from langchain_experimental.text_splitter import SemanticChunker
    from langchain_openai.embeddings import OpenAIEmbeddings

    SEMANTIC_CHUNKING_AVAILABLE = True
except ImportError:
    SEMANTIC_CHUNKING_AVAILABLE = False

from .config import config
from .models import VideoTranscript


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""

    NONE = "none"  # No chunking, use full transcript
    RECURSIVE = "recursive"  # Recursive character-based splitting
    SEMANTIC = "semantic"  # Semantic similarity-based splitting
    TIMESTAMP = "timestamp"  # Split by timestamp intervals


class TranscriptChunker:
    """Chunk video transcripts using various strategies."""

    def __init__(
        self,
        strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """
        Initialize chunker.

        Args:
            strategy: Chunking strategy to use
            chunk_size: Maximum tokens per chunk
            chunk_overlap: Overlap between chunks (tokens)
        """
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Initialize splitters based on strategy
        self._init_splitters()

    def _init_splitters(self):
        """Initialize text splitters based on strategy."""
        if self.strategy == ChunkingStrategy.RECURSIVE:
            self.recursive_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n", "\n", " ", ""],
                length_function=len,
            )

        elif self.strategy == ChunkingStrategy.SEMANTIC:
            if not SEMANTIC_CHUNKING_AVAILABLE:
                raise ImportError(
                    "Semantic chunking requires: pip install langchain-experimental langchain-openai"
                )

            # Use OpenAI embeddings for semantic chunking
            self.semantic_splitter = SemanticChunker(
                OpenAIEmbeddings(),
                breakpoint_threshold_type="percentile",
                breakpoint_threshold_amount=95,
            )

    def chunk_transcript(
        self, transcript: VideoTranscript
    ) -> list[Document] | Document:
        """
        Chunk transcript using configured strategy.

        Args:
            transcript: VideoTranscript to chunk

        Returns:
            List of Document chunks or single Document if no chunking
        """
        if self.strategy == ChunkingStrategy.NONE:
            return self._no_chunking(transcript)
        elif self.strategy == ChunkingStrategy.RECURSIVE:
            return self._recursive_chunking(transcript)
        elif self.strategy == ChunkingStrategy.SEMANTIC:
            return self._semantic_chunking(transcript)
        elif self.strategy == ChunkingStrategy.TIMESTAMP:
            return self._timestamp_chunking(transcript)
        else:
            raise ValueError(f"Unknown chunking strategy: {self.strategy}")

    def _no_chunking(self, transcript: VideoTranscript) -> Document:
        """Return full transcript as single document."""
        return Document(
            page_content=transcript.full_text_with_timestamps,
            metadata={
                "video_id": transcript.metadata.video_id,
                "title": transcript.metadata.title,
                "channel": transcript.metadata.channel,
                "duration": transcript.metadata.duration,
                "language": transcript.language,
                "is_auto_generated": transcript.is_auto_generated,
                "url": transcript.metadata.url,
            },
        )

    def _recursive_chunking(self, transcript: VideoTranscript) -> list[Document]:
        """Chunk using recursive character text splitter."""
        # Create base document
        base_doc = self._no_chunking(transcript)

        # Split
        chunks = self.recursive_splitter.split_documents([base_doc])

        # Add chunk metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata['chunk_index'] = i
            chunk.metadata['total_chunks'] = len(chunks)
            chunk.metadata['chunking_strategy'] = 'recursive'

        return chunks

    def _semantic_chunking(self, transcript: VideoTranscript) -> list[Document]:
        """Chunk using semantic similarity."""
        if not SEMANTIC_CHUNKING_AVAILABLE:
            raise ImportError(
                "Semantic chunking requires: pip install langchain-experimental langchain-openai"
            )

        # Get full text without timestamps for better semantic analysis
        full_text = transcript.full_text

        # Create documents using semantic chunker
        chunks = self.semantic_splitter.create_documents([full_text])

        # Add metadata to each chunk
        base_metadata = {
            "video_id": transcript.metadata.video_id,
            "title": transcript.metadata.title,
            "channel": transcript.metadata.channel,
            "duration": transcript.metadata.duration,
            "language": transcript.language,
            "is_auto_generated": transcript.is_auto_generated,
            "url": transcript.metadata.url,
            "chunking_strategy": "semantic",
        }

        for i, chunk in enumerate(chunks):
            chunk.metadata = {
                **base_metadata,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }

        return chunks

    def _timestamp_chunking(
        self, transcript: VideoTranscript, interval_seconds: int = 300
    ) -> list[Document]:
        """
        Chunk by timestamp intervals (e.g., every 5 minutes).

        Args:
            transcript: VideoTranscript to chunk
            interval_seconds: Chunk interval in seconds (default: 300 = 5 min)

        Returns:
            List of Document chunks
        """
        chunks = []
        current_chunk_segments = []
        current_chunk_start = 0.0

        for segment in transcript.segments:
            # Check if we should start a new chunk
            if segment.start >= current_chunk_start + interval_seconds:
                if current_chunk_segments:
                    # Create chunk from accumulated segments
                    chunk = self._create_chunk_from_segments(
                        current_chunk_segments,
                        transcript,
                        len(chunks),
                    )
                    chunks.append(chunk)

                # Start new chunk
                current_chunk_segments = []
                current_chunk_start = segment.start

            # Add segment to current chunk
            current_chunk_segments.append(segment)

        # Add final chunk
        if current_chunk_segments:
            chunk = self._create_chunk_from_segments(
                current_chunk_segments, transcript, len(chunks)
            )
            chunks.append(chunk)

        # Update total_chunks metadata
        for chunk in chunks:
            chunk.metadata['total_chunks'] = len(chunks)

        return chunks

    def _create_chunk_from_segments(
        self,
        segments: list,
        transcript: VideoTranscript,
        chunk_index: int,
    ) -> Document:
        """Create a Document chunk from transcript segments."""
        # Combine segment texts with timestamps
        chunk_text = "\n".join(
            f"[{seg.start_timestamp}] {seg.text}" for seg in segments
        )

        # Get time range
        start_time = segments[0].start
        end_time = segments[-1].end

        return Document(
            page_content=chunk_text,
            metadata={
                "video_id": transcript.metadata.video_id,
                "title": transcript.metadata.title,
                "channel": transcript.metadata.channel,
                "duration": transcript.metadata.duration,
                "language": transcript.language,
                "is_auto_generated": transcript.is_auto_generated,
                "url": transcript.metadata.url,
                "chunk_index": chunk_index,
                "start_time": start_time,
                "end_time": end_time,
                "chunking_strategy": "timestamp",
            },
        )


def recommend_chunking_strategy(
    transcript: VideoTranscript,
) -> ChunkingStrategy:
    """
    Recommend chunking strategy based on video characteristics.

    Args:
        transcript: VideoTranscript to analyze

    Returns:
        Recommended ChunkingStrategy
    """
    duration = transcript.metadata.duration or 0

    # Short videos: no chunking needed
    if duration < 600:  # < 10 minutes
        return ChunkingStrategy.NONE

    # Medium videos: recursive chunking
    elif duration < 1800:  # < 30 minutes
        return ChunkingStrategy.RECURSIVE

    # Long videos: semantic or timestamp chunking
    else:
        # Prefer semantic if available, otherwise timestamp
        if SEMANTIC_CHUNKING_AVAILABLE:
            return ChunkingStrategy.SEMANTIC
        else:
            return ChunkingStrategy.TIMESTAMP
