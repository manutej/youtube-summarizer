# Error Handling and Retry Logic

This document describes the error handling and retry mechanisms implemented in the YouTube Summarizer to handle API rate limiting and transient failures.

## Overview

YouTube's API can return various errors, including rate limiting (429/401 errors) when too many requests are made in a short period. To provide a smooth user experience, the application implements exponential backoff retry logic for handling these transient failures.

## Exponential Backoff

### What is Exponential Backoff?

Exponential backoff is a retry strategy where the wait time between retries increases exponentially. This approach:
- Gives the API time to recover
- Reduces the chance of continued rate limiting
- Prevents overwhelming the server with retry requests

### Configuration

The retry logic is configured with the following parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_retries` | 3 | Maximum number of retry attempts |
| `base_delay` | 2.0 seconds | Initial delay before first retry |
| `max_delay` | 60.0 seconds | Maximum delay cap |
| `exponential_base` | 2.0 | Multiplier for exponential growth |
| `jitter` | true | Add random variation to prevent thundering herd |

### Delay Calculation

The delay for each retry is calculated as:
```
delay = min(base_delay * (exponential_base ^ attempt), max_delay) + jitter
```

For example, with default settings:
- Attempt 1: ~2 seconds (2 * 2^0)
- Attempt 2: ~4 seconds (2 * 2^1)
- Attempt 3: ~8 seconds (2 * 2^2)

## Retryable Errors

The following errors are automatically retried:

### YouTube API Errors
- **TooManyRequests**: Rate limiting from YouTube
- **YouTubeRequestFailed** with:
  - HTTP 401 (Unauthorized - often rate limiting)
  - HTTP 429 (Too Many Requests)
  - HTTP 500/502/503/504 (Server errors)
  - Messages containing "throttle" or "rate limit"

### Non-Retryable Errors
These errors are NOT retried as they indicate permanent failures:
- **NoTranscriptFound**: Video doesn't have a transcript
- **TranscriptsDisabled**: Transcripts are disabled for the video
- **InvalidVideoId**: The video ID is malformed
- **VideoUnavailable**: The video doesn't exist or is private

## Usage Examples

### Using the Decorator

```python
from src.retry import with_retry, RetryConfig

@with_retry(config=RetryConfig(max_retries=5))
def fetch_transcript(video_id):
    # This function will be retried on retryable errors
    return api.fetch(video_id)
```

### Using the Function

```python
from src.retry import retry_with_backoff, RetryConfig

result = retry_with_backoff(
    func=lambda: api.fetch(video_id),
    config=RetryConfig(max_retries=3),
    on_retry=lambda e, attempt, delay: print(f"Retrying in {delay}s...")
)
```

### Custom Retry Logic

```python
from src.retry import RetryConfig, retry_with_backoff

# Custom configuration for aggressive retries
config = RetryConfig(
    max_retries=5,
    base_delay=1.0,
    max_delay=120.0,
    exponential_base=3.0,
    jitter=True,
)

# Custom retryable check
def is_retryable(error):
    return isinstance(error, (RateLimitError, TimeoutError))

result = retry_with_backoff(
    func=my_api_call,
    config=config,
    retryable_check=is_retryable,
)
```

## User Feedback

When errors occur, users receive clear feedback:

### Throttling Messages
```
⚠️ YouTube is temporarily limiting requests. Tried 3 time(s). 
Please wait a moment and try again.
```

### Retry Progress
During retries, the CLI shows:
```
└─ ⚠️  Request throttled (attempt 1). Retrying in 2.5s...
└─ ⚠️  Request throttled (attempt 2). Retrying in 5.2s...
```

### Final Failure
If all retries are exhausted:
```
❌ Failed after 3 attempt(s): YouTube is throttling requests for video ABC123
```

## Error Classes

### RetryableError
Base class for errors that can be retried:
```python
from src.retry import RetryableError

error = RetryableError(
    message="API error",
    original_error=original_exception,
    attempts_made=3,
    is_throttled=True,
)
```

### YouTubeThrottledError
Specific error for YouTube throttling:
```python
from src.retry import YouTubeThrottledError

raise YouTubeThrottledError(
    message="Rate limited by YouTube",
    original_error=original_exception,
    attempts_made=3,
)
```

## Best Practices

1. **Don't disable retries**: The retry logic is designed to handle transient failures gracefully.

2. **Monitor retry logs**: If you see many retries, consider:
   - Reducing request frequency
   - Adding longer delays between videos
   - Using batch processing with delays

3. **Handle final failures gracefully**: After retries are exhausted, provide useful error messages to users.

4. **Use appropriate retry limits**: For user-facing operations, 3 retries is usually sufficient. For background jobs, you might want more.

## Troubleshooting

### Too Many Retries
If you're seeing excessive retries:
- YouTube may be rate limiting your IP
- Consider waiting between processing multiple videos
- Check if you're processing the same video multiple times

### Retries Not Helping
If errors persist after retries:
- The error might not be transient
- Check your network connection
- Verify the video exists and has transcripts enabled

### Delays Too Long
If delays feel too long:
```python
# Use a more aggressive configuration
config = RetryConfig(
    max_retries=2,
    base_delay=0.5,
    max_delay=10.0,
)
```

## Related Files

- `src/retry.py`: Retry utilities implementation
- `src/extractors.py`: Transcript extraction with retry logic
- `tests/test_retry.py`: Unit tests for retry functionality
