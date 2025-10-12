# Documentation

This directory contains project documentation and research.

## Files

- **LANGCHAIN_RESEARCH.md**: Comprehensive research on LangChain integration for YouTube video processing
  - YouTube document loaders
  - Text splitting strategies
  - Claude integration
  - Summarization workflows
  - Best practices and recommendations

- **YT_COMMAND_REFERENCE.md**: Quick reference guide for the `/yt` Claude Code slash command
  - Command syntax and examples
  - Flag combinations and workflows
  - Troubleshooting tips
  - Performance and cost considerations

## Research Topics

### LangChain Components
- YoutubeLoader for transcript extraction
- RecursiveCharacterTextSplitter for general chunking
- SemanticChunker for topic-based segmentation
- ChatAnthropic for Claude integration

### Summarization Strategies
- Stuff method (simple, single call)
- Map-Reduce method (scalable, parallel)
- Refine method (iterative improvement)

### Claude Optimization
- Long-context best practices (200K tokens)
- Prompt engineering techniques
- Extended thinking mode
- Structured output

## Contributing

When adding new documentation:
1. Use clear Markdown formatting
2. Include code examples where relevant
3. Link to official documentation sources
4. Update this README with new files
