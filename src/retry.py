"""Exponential backoff retry utilities for handling API throttling and errors."""

import time
import random
import logging
from functools import wraps
from typing import Callable, Optional, Type, TypeVar, Any

# Set up logging
logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Initial delay in seconds (default: 1.0)
            max_delay: Maximum delay cap in seconds (default: 60.0)
            exponential_base: Base for exponential calculation (default: 2.0)
            jitter: Add random jitter to prevent thundering herd (default: True)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


# Default configuration for YouTube API calls
DEFAULT_YOUTUBE_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=2.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
)


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay for a given attempt using exponential backoff.

    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    # Exponential backoff: base_delay * (exponential_base ^ attempt)
    delay = config.base_delay * (config.exponential_base ** attempt)

    # Cap at max_delay
    delay = min(delay, config.max_delay)

    # Add jitter to prevent thundering herd problem
    if config.jitter:
        # Add random jitter of 0-50% of the delay
        jitter_amount = delay * 0.5 * random.random()
        delay += jitter_amount

    return delay


def is_retryable_youtube_error(error: Exception) -> bool:
    """
    Check if an error from YouTube API is retryable.

    Args:
        error: The exception to check

    Returns:
        True if the error is retryable (rate limiting, temporary failure)
    """
    # Import here to avoid circular imports
    try:
        from youtube_transcript_api._errors import (
            TooManyRequests,
            YouTubeRequestFailed,
        )
    except ImportError:
        # Fallback if import fails
        return False

    # TooManyRequests is always retryable (rate limiting)
    if isinstance(error, TooManyRequests):
        return True

    # YouTubeRequestFailed might be retryable for certain HTTP errors
    if isinstance(error, YouTubeRequestFailed):
        error_str = str(error).lower()
        # Check for common retryable HTTP status codes
        retryable_patterns = [
            '401',  # Unauthorized (often rate limiting)
            '429',  # Too Many Requests
            '500',  # Internal Server Error
            '502',  # Bad Gateway
            '503',  # Service Unavailable
            '504',  # Gateway Timeout
            'throttle',
            'rate limit',
            'too many requests',
        ]
        return any(pattern in error_str for pattern in retryable_patterns)

    return False


def with_retry(
    config: Optional[RetryConfig] = None,
    retryable_exceptions: Optional[tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to add exponential backoff retry logic to a function.

    Args:
        config: Retry configuration (uses DEFAULT_YOUTUBE_RETRY_CONFIG if None)
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Callback function called on each retry (exception, attempt)

    Returns:
        Decorated function with retry logic
    """
    if config is None:
        config = DEFAULT_YOUTUBE_RETRY_CONFIG

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Check if we should retry this exception
                    should_retry = False
                    if retryable_exceptions:
                        should_retry = isinstance(e, retryable_exceptions)
                    else:
                        # Default: check if it's a retryable YouTube error
                        should_retry = is_retryable_youtube_error(e)

                    # Don't retry if not retryable or we've exhausted retries
                    if not should_retry or attempt >= config.max_retries:
                        raise

                    # Calculate delay
                    delay = calculate_delay(attempt, config)

                    # Log the retry
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )

                    # Call the on_retry callback if provided
                    if on_retry:
                        on_retry(e, attempt)

                    # Wait before retrying
                    time.sleep(delay)

            # This shouldn't be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Retry logic error: no exception captured")

        return wrapper

    return decorator


def retry_with_backoff(
    func: Callable[..., T],
    args: tuple = (),
    kwargs: Optional[dict] = None,
    config: Optional[RetryConfig] = None,
    retryable_check: Optional[Callable[[Exception], bool]] = None,
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
) -> T:
    """
    Execute a function with exponential backoff retry logic.

    This is a non-decorator version for more flexibility.

    Args:
        func: Function to execute
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
        config: Retry configuration (uses DEFAULT_YOUTUBE_RETRY_CONFIG if None)
        retryable_check: Custom function to check if an error is retryable
        on_retry: Callback function called on each retry (exception, attempt, delay)

    Returns:
        Result of the function

    Raises:
        The last exception if all retries are exhausted
    """
    if config is None:
        config = DEFAULT_YOUTUBE_RETRY_CONFIG
    if kwargs is None:
        kwargs = {}
    if retryable_check is None:
        retryable_check = is_retryable_youtube_error

    last_exception: Optional[Exception] = None

    for attempt in range(config.max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e

            # Check if we should retry this exception
            if not retryable_check(e) or attempt >= config.max_retries:
                raise

            # Calculate delay
            delay = calculate_delay(attempt, config)

            # Log the retry
            logger.warning(
                f"Attempt {attempt + 1}/{config.max_retries + 1} failed: {e}. "
                f"Retrying in {delay:.2f} seconds..."
            )

            # Call the on_retry callback if provided
            if on_retry:
                on_retry(e, attempt, delay)

            # Wait before retrying
            time.sleep(delay)

    # This shouldn't be reached, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry logic error: no exception captured")


class RetryableError(Exception):
    """Base class for retryable errors with user-friendly messages."""

    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        attempts_made: int = 0,
        is_throttled: bool = False,
    ):
        """
        Initialize retryable error.

        Args:
            message: User-friendly error message
            original_error: The original exception that caused this error
            attempts_made: Number of retry attempts made
            is_throttled: Whether the error was due to throttling/rate limiting
        """
        super().__init__(message)
        self.original_error = original_error
        self.attempts_made = attempts_made
        self.is_throttled = is_throttled

    def get_user_message(self) -> str:
        """Get a user-friendly message for display."""
        if self.is_throttled:
            return (
                f"⚠️ YouTube is temporarily limiting requests. "
                f"Tried {self.attempts_made} time(s). "
                f"Please wait a moment and try again.\n"
                f"Detail: {self}"
            )
        return f"❌ Failed after {self.attempts_made} attempt(s): {self}"


class YouTubeThrottledError(RetryableError):
    """Specific error for YouTube throttling/rate limiting."""

    def __init__(
        self,
        message: str = "YouTube is throttling requests",
        original_error: Optional[Exception] = None,
        attempts_made: int = 0,
    ):
        super().__init__(
            message=message,
            original_error=original_error,
            attempts_made=attempts_made,
            is_throttled=True,
        )
