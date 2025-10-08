"""Claude-powered video summarization with long-context optimization."""

from datetime import datetime
from typing import Optional

import anthropic
from langchain_core.documents import Document

from .config import config
from .models import VideoSummary, VideoTranscript


class ClaudeSummarizer:
    """Summarize video transcripts using Claude with long-context optimization."""

    def __init__(
        self,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        use_extended_thinking: bool = False,
        thinking_budget: int = 4096,
    ):
        """
        Initialize Claude summarizer.

        Args:
            model: Claude model to use (defaults to config)
            max_tokens: Maximum tokens for response
            temperature: Sampling temperature (0.0 = deterministic)
            use_extended_thinking: Enable extended thinking mode
            thinking_budget: Token budget for thinking (if enabled)
        """
        if not config.validate_api_key():
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Please set it in .env file."
            )

        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self.model = model or config.claude_model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.use_extended_thinking = use_extended_thinking
        self.thinking_budget = thinking_budget

    def summarize_transcript(
        self,
        transcript: VideoTranscript,
        format_type: str = "detailed",
        custom_prompt: Optional[str] = None,
    ) -> VideoSummary:
        """
        Summarize video transcript using Claude.

        Args:
            transcript: VideoTranscript to summarize
            format_type: Summary format (concise, detailed, academic, bullet_points)
            custom_prompt: Custom prompt to override default

        Returns:
            VideoSummary with structured summary content
        """
        # Build optimized prompt (transcript at top per Anthropic best practices)
        prompt = self._build_prompt(transcript, format_type, custom_prompt)

        # Call Claude API
        response = self._call_claude(prompt)

        # Parse response into structured summary
        summary = self._parse_response(response, transcript, format_type)

        return summary

    def summarize_chunks(
        self,
        chunks: list[Document],
        transcript: VideoTranscript,
        format_type: str = "detailed",
    ) -> VideoSummary:
        """
        Summarize chunked transcript using map-reduce strategy.

        Args:
            chunks: List of document chunks
            transcript: Original VideoTranscript (for metadata)
            format_type: Summary format

        Returns:
            VideoSummary combining insights from all chunks
        """
        # Phase 1: Summarize each chunk (map)
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            chunk_prompt = self._build_chunk_prompt(chunk, i + 1, len(chunks))
            chunk_summary = self._call_claude(chunk_prompt)
            chunk_summaries.append(chunk_summary)

        # Phase 2: Combine summaries (reduce)
        combined_prompt = self._build_reduce_prompt(
            chunk_summaries, transcript, format_type
        )
        final_response = self._call_claude(combined_prompt)

        # Parse final summary
        summary = self._parse_response(final_response, transcript, format_type)

        return summary

    def _build_prompt(
        self,
        transcript: VideoTranscript,
        format_type: str,
        custom_prompt: Optional[str] = None,
    ) -> str:
        """
        Build optimized prompt for Claude.

        Following Anthropic best practices:
        1. Place long documents at TOP of prompt
        2. Use XML structure for organization
        3. Request quote extraction first for grounding
        """
        if custom_prompt:
            return custom_prompt

        # XML-structured document (Anthropic recommendation)
        document_section = f"""<documents>
<document index="1">
<source>{transcript.metadata.title or transcript.metadata.video_id}</source>
<video_metadata>
- Video ID: {transcript.metadata.video_id}
- URL: {transcript.metadata.url}
- Channel: {transcript.metadata.channel or "Unknown"}
- Duration: {transcript.metadata.duration_formatted or "Unknown"}
- Language: {transcript.language}
- Auto-generated: {transcript.is_auto_generated}
</video_metadata>
<document_content>
{transcript.full_text_with_timestamps}
</document_content>
</document>
</documents>"""

        # Task instructions based on format type
        task_instructions = self._get_task_instructions(format_type)

        # Combine: document first (top), then instructions
        return f"""{document_section}

{task_instructions}"""

    def _get_task_instructions(self, format_type: str) -> str:
        """Get task instructions based on summary format."""
        base_instruction = """Analyze the video transcript above and provide a structured summary.

First, identify and quote 3-5 key segments from the transcript that represent the main ideas.

Then provide:"""

        if format_type == "concise":
            return f"""{base_instruction}

1. **Executive Summary** (2-3 sentences capturing the essence)
2. **Key Takeaways** (5-7 bullet points)
3. **Main Topics** (3-5 topics covered)
4. **Target Audience** (who would benefit from this video)

Format your response in clear Markdown."""

        elif format_type == "detailed":
            return f"""{base_instruction}

1. **Executive Summary** (2-3 sentences)
2. **Key Points** (8-12 points with timestamps in [HH:MM:SS] format)
3. **Detailed Summary** (Comprehensive breakdown by section/topic)
4. **Topics Covered** (All major topics discussed)
5. **Notable Quotes** (3-5 memorable or important quotes with timestamps)
6. **Resources Mentioned** (Books, tools, websites, papers referenced)
7. **Target Audience** (Who should watch this)

Format your response in clear Markdown with proper headings and structure."""

        elif format_type == "academic":
            return f"""{base_instruction}

1. **Executive Summary** (Abstract-style overview)
2. **Main Concepts** (Define and explain key concepts with timestamps)
3. **Methodology/Approach** (If applicable: techniques, frameworks discussed)
4. **Practical Applications** (Real-world use cases and examples)
5. **Key Findings/Insights** (Important conclusions or discoveries)
6. **Resources & References** (Citations, further reading)
7. **Discussion Points** (Questions for further exploration)

Format as academic notes with clear structure and technical depth."""

        elif format_type == "bullet_points":
            return f"""{base_instruction}

Provide a rapid-fire list of key takeaways:

**TL;DR** (One sentence)

**Main Points** (15-20 concise bullet points capturing all important information with timestamps)

**Topics** (List of topics covered)

**Resources** (Any tools/books/links mentioned)

Be extremely concise but comprehensive."""

        else:
            # Default to detailed
            return self._get_task_instructions("detailed")

    def _build_chunk_prompt(
        self, chunk: Document, chunk_num: int, total_chunks: int
    ) -> str:
        """Build prompt for individual chunk summarization (map phase)."""
        return f"""<document_chunk>
<chunk_info>
Chunk {chunk_num} of {total_chunks}
Video: {chunk.metadata.get('title', 'Unknown')}
</chunk_info>
<content>
{chunk.page_content}
</content>
</document_chunk>

Summarize the key points from this chunk of the video transcript. Focus on:
- Main topics discussed
- Important statements or claims
- Examples or demonstrations mentioned
- Any resources or references

Provide 3-5 concise bullet points capturing the essence of this segment."""

    def _build_reduce_prompt(
        self,
        chunk_summaries: list[str],
        transcript: VideoTranscript,
        format_type: str,
    ) -> str:
        """Build prompt for combining chunk summaries (reduce phase)."""
        combined_summaries = "\n\n---\n\n".join(
            [f"**Segment {i+1}**:\n{summary}" for i, summary in enumerate(chunk_summaries)]
        )

        task_instructions = self._get_task_instructions(format_type)

        return f"""<video_info>
Title: {transcript.metadata.title or "Unknown"}
Channel: {transcript.metadata.channel or "Unknown"}
Duration: {transcript.metadata.duration_formatted or "Unknown"}
URL: {transcript.metadata.url}
</video_info>

<segment_summaries>
{combined_summaries}
</segment_summaries>

You have been provided with summaries of different segments from a video transcript.
Synthesize these into a comprehensive summary of the entire video.

{task_instructions}"""

    def _call_claude(self, prompt: str) -> str:
        """Call Claude API with optimized settings."""
        # Build message
        message_params = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        # Add extended thinking if enabled
        if self.use_extended_thinking:
            message_params["thinking"] = {
                "type": "enabled",
                "budget_tokens": self.thinking_budget,
            }

        # Call API
        response = self.client.messages.create(**message_params)

        # Extract text from response
        # Handle both thinking and text blocks
        result_text = ""
        for block in response.content:
            if block.type == "text":
                result_text += block.text

        return result_text

    def _parse_response(
        self,
        response: str,
        transcript: VideoTranscript,
        format_type: str,
    ) -> VideoSummary:
        """
        Parse Claude's response into structured VideoSummary.

        Note: This is a simplified parser. Could be enhanced with
        structured output using Pydantic models and Claude's
        structured output feature.
        """
        # Simple parsing - extract sections
        lines = response.split('\n')

        # Initialize fields
        executive_summary = ""
        key_points = []
        detailed_summary = ""
        topics_covered = []
        notable_quotes = []
        resources_mentioned = []
        target_audience = ""

        current_section = None
        current_content = []

        for line in lines:
            line_lower = line.lower().strip()

            # Detect sections
            if 'executive summary' in line_lower or 'tl;dr' in line_lower or line_lower.startswith('**tl;dr'):
                current_section = 'executive'
                continue
            elif 'key point' in line_lower or 'key takeaway' in line_lower or 'main point' in line_lower:
                current_section = 'key_points'
                continue
            elif 'detailed summary' in line_lower or 'comprehensive' in line_lower:
                current_section = 'detailed'
                continue
            elif 'topic' in line_lower:
                current_section = 'topics'
                continue
            elif 'quote' in line_lower:
                current_section = 'quotes'
                continue
            elif 'resource' in line_lower or 'reference' in line_lower:
                current_section = 'resources'
                continue
            elif 'target audience' in line_lower or 'who should watch' in line_lower:
                current_section = 'audience'
                continue

            # Collect content for current section
            if current_section and line.strip():
                if current_section == 'executive':
                    if not line.startswith('#') and not line.startswith('**'):
                        executive_summary += line + " "
                elif current_section == 'key_points':
                    if line.strip().startswith('-') or line.strip().startswith('*') or line.strip().startswith('•'):
                        key_points.append(line.strip().lstrip('-*• '))
                elif current_section == 'detailed':
                    detailed_summary += line + "\n"
                elif current_section == 'topics':
                    if line.strip().startswith('-') or line.strip().startswith('*') or line.strip().startswith('•'):
                        topics_covered.append(line.strip().lstrip('-*• '))
                elif current_section == 'quotes':
                    if line.strip().startswith('>') or line.strip().startswith('"'):
                        notable_quotes.append(line.strip())
                elif current_section == 'resources':
                    if line.strip().startswith('-') or line.strip().startswith('*') or line.strip().startswith('•'):
                        resources_mentioned.append(line.strip().lstrip('-*• '))
                elif current_section == 'audience':
                    if not line.startswith('#') and not line.startswith('**'):
                        target_audience += line + " "

        # Fallbacks
        if not executive_summary:
            executive_summary = response[:200] + "..."

        if not key_points:
            # Extract first few sentences as key points
            sentences = response.split('. ')[:5]
            key_points = [s.strip() + '.' for s in sentences if s.strip()]

        if not detailed_summary:
            detailed_summary = response

        # Create VideoSummary
        return VideoSummary(
            metadata=transcript.metadata,
            executive_summary=executive_summary.strip(),
            key_points=key_points,
            detailed_summary=detailed_summary.strip(),
            topics_covered=topics_covered if topics_covered else ["Not extracted"],
            notable_quotes=notable_quotes if notable_quotes else None,
            resources_mentioned=resources_mentioned if resources_mentioned else None,
            target_audience=target_audience.strip() if target_audience else None,
            generated_at=datetime.now(),
        )
