"""Tests for exponential backoff retry utilities."""

import time
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.retry import (
    RetryConfig,
    calculate_delay,
    is_retryable_youtube_error,
    with_retry,
    retry_with_backoff,
    RetryableError,
    YouTubeThrottledError,
    DEFAULT_YOUTUBE_RETRY_CONFIG,
)


class TestRetryConfig:
    """Tests for RetryConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=3.0,
            jitter=False,
        )
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_base == 3.0
        assert config.jitter is False


class TestCalculateDelay:
    """Tests for calculate_delay function."""

    def test_exponential_growth(self):
        """Test that delay grows exponentially without jitter."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=60.0,
            jitter=False,
        )

        assert calculate_delay(0, config) == 1.0   # 1 * 2^0 = 1
        assert calculate_delay(1, config) == 2.0   # 1 * 2^1 = 2
        assert calculate_delay(2, config) == 4.0   # 1 * 2^2 = 4
        assert calculate_delay(3, config) == 8.0   # 1 * 2^3 = 8
        assert calculate_delay(4, config) == 16.0  # 1 * 2^4 = 16

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(
            base_delay=10.0,
            exponential_base=2.0,
            max_delay=50.0,
            jitter=False,
        )

        # 10 * 2^3 = 80, but should be capped at 50
        assert calculate_delay(3, config) == 50.0

    def test_jitter_adds_randomness(self):
        """Test that jitter adds random component to delay."""
        config = RetryConfig(
            base_delay=10.0,
            exponential_base=2.0,
            max_delay=60.0,
            jitter=True,
        )

        # With jitter, delay should be between base and base + 50%
        delays = [calculate_delay(0, config) for _ in range(100)]

        # All delays should be >= base_delay
        assert all(d >= 10.0 for d in delays)

        # At least some delays should be > base_delay (due to jitter)
        assert any(d > 10.0 for d in delays)

        # All delays should be <= base_delay * 1.5 (max 50% jitter)
        assert all(d <= 15.0 for d in delays)


class TestIsRetryableYouTubeError:
    """Tests for is_retryable_youtube_error function."""

    def test_too_many_requests_error(self):
        """Test that TooManyRequests is retryable."""
        from youtube_transcript_api._errors import TooManyRequests

        error = TooManyRequests("test_video_id")
        assert is_retryable_youtube_error(error) is True

    def test_youtube_request_failed_401(self):
        """Test that YouTubeRequestFailed with 401 is retryable."""
        from youtube_transcript_api._errors import YouTubeRequestFailed

        error = YouTubeRequestFailed("test_video", Exception("HTTP 401 Unauthorized"))
        assert is_retryable_youtube_error(error) is True

    def test_youtube_request_failed_429(self):
        """Test that YouTubeRequestFailed with 429 is retryable."""
        from youtube_transcript_api._errors import YouTubeRequestFailed

        error = YouTubeRequestFailed("test_video", Exception("HTTP 429 Too Many Requests"))
        assert is_retryable_youtube_error(error) is True

    def test_youtube_request_failed_throttle(self):
        """Test that throttle messages are retryable."""
        from youtube_transcript_api._errors import YouTubeRequestFailed

        error = YouTubeRequestFailed("test_video", Exception("Request throttled by YouTube"))
        assert is_retryable_youtube_error(error) is True

    def test_non_retryable_error(self):
        """Test that generic errors are not retryable."""
        error = ValueError("Some error")
        assert is_retryable_youtube_error(error) is False

    def test_non_retryable_youtube_error(self):
        """Test that non-throttle YouTube errors are not retryable."""
        from youtube_transcript_api._errors import NoTranscriptFound

        error = NoTranscriptFound("test_video_id", [], None)
        assert is_retryable_youtube_error(error) is False


class TestWithRetryDecorator:
    """Tests for with_retry decorator."""

    def test_successful_call_no_retry(self):
        """Test that successful calls don't trigger retries."""
        call_count = 0

        @with_retry()
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_retryable_error(self):
        """Test that retryable errors trigger retries."""
        from youtube_transcript_api._errors import TooManyRequests

        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        call_count = 0

        @with_retry(config=config)
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TooManyRequests("test_video")
            return "success"

        result = failing_func()
        assert result == "success"
        assert call_count == 3  # 1 initial + 2 retries

    def test_exhausted_retries_raises(self):
        """Test that exhausted retries raise the last exception."""
        from youtube_transcript_api._errors import TooManyRequests

        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)

        @with_retry(config=config)
        def always_fails():
            raise TooManyRequests("test_video")

        with pytest.raises(TooManyRequests):
            always_fails()

    def test_non_retryable_error_not_retried(self):
        """Test that non-retryable errors are not retried."""
        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        call_count = 0

        @with_retry(config=config)
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            raises_value_error()

        assert call_count == 1  # No retries for non-retryable errors

    def test_custom_retryable_exceptions(self):
        """Test custom retryable exceptions tuple."""
        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        call_count = 0

        @with_retry(config=config, retryable_exceptions=(ValueError,))
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Custom retryable")
            return "success"

        result = raises_value_error()
        assert result == "success"
        assert call_count == 3

    def test_on_retry_callback_called(self):
        """Test that on_retry callback is called on each retry."""
        from youtube_transcript_api._errors import TooManyRequests

        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        retry_attempts = []

        def on_retry(error, attempt):
            retry_attempts.append(attempt)

        @with_retry(config=config, on_retry=on_retry)
        def fails_twice():
            if len(retry_attempts) < 2:
                raise TooManyRequests("test_video")
            return "success"

        result = fails_twice()
        assert result == "success"
        assert retry_attempts == [0, 1]


class TestRetryWithBackoff:
    """Tests for retry_with_backoff function."""

    def test_successful_call(self):
        """Test successful function call."""
        result = retry_with_backoff(
            func=lambda: "success",
            config=RetryConfig(max_retries=3),
        )
        assert result == "success"

    def test_retry_on_failure(self):
        """Test retry on retryable failure."""
        from youtube_transcript_api._errors import TooManyRequests

        call_count = 0

        def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TooManyRequests("test_video")
            return "success"

        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        result = retry_with_backoff(
            func=sometimes_fails,
            config=config,
        )

        assert result == "success"
        assert call_count == 2

    def test_custom_retryable_check(self):
        """Test custom retryable check function."""
        call_count = 0

        def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Custom error")
            return "success"

        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        result = retry_with_backoff(
            func=sometimes_fails,
            config=config,
            retryable_check=lambda e: isinstance(e, RuntimeError),
        )

        assert result == "success"
        assert call_count == 2

    def test_on_retry_callback(self):
        """Test on_retry callback is called with correct arguments."""
        from youtube_transcript_api._errors import TooManyRequests

        callback_args = []

        def on_retry(error, attempt, delay):
            callback_args.append((type(error).__name__, attempt, delay > 0))

        def fails_once():
            if len(callback_args) < 1:
                raise TooManyRequests("test_video")
            return "success"

        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        result = retry_with_backoff(
            func=fails_once,
            config=config,
            on_retry=on_retry,
        )

        assert result == "success"
        assert len(callback_args) == 1
        assert callback_args[0][0] == "TooManyRequests"
        assert callback_args[0][1] == 0  # First retry attempt
        assert callback_args[0][2] is True  # Delay > 0


class TestRetryableError:
    """Tests for RetryableError class."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = RetryableError("Test error")
        assert str(error) == "Test error"
        assert error.original_error is None
        assert error.attempts_made == 0
        assert error.is_throttled is False

    def test_error_with_metadata(self):
        """Test error with metadata."""
        original = ValueError("Original error")
        error = RetryableError(
            "Wrapper error",
            original_error=original,
            attempts_made=3,
            is_throttled=True,
        )
        assert error.original_error is original
        assert error.attempts_made == 3
        assert error.is_throttled is True

    def test_user_message_throttled(self):
        """Test user-friendly message for throttled errors."""
        error = RetryableError(
            "Rate limited",
            attempts_made=3,
            is_throttled=True,
        )
        message = error.get_user_message()
        assert "⚠️" in message
        assert "throttle" in message.lower() or "limiting" in message.lower()
        assert "3" in message

    def test_user_message_non_throttled(self):
        """Test user-friendly message for non-throttled errors."""
        error = RetryableError(
            "Generic error",
            attempts_made=2,
            is_throttled=False,
        )
        message = error.get_user_message()
        assert "❌" in message
        assert "2" in message


class TestYouTubeThrottledError:
    """Tests for YouTubeThrottledError class."""

    def test_default_message(self):
        """Test default error message."""
        error = YouTubeThrottledError()
        assert "throttling" in str(error).lower()
        assert error.is_throttled is True

    def test_custom_message(self):
        """Test custom error message."""
        error = YouTubeThrottledError(
            message="Custom throttle message",
            attempts_made=5,
        )
        assert "Custom throttle message" in str(error)
        assert error.attempts_made == 5

    def test_with_original_error(self):
        """Test error with original exception."""
        from youtube_transcript_api._errors import TooManyRequests

        original = TooManyRequests("test_video")
        error = YouTubeThrottledError(
            message="Throttled",
            original_error=original,
        )
        assert error.original_error is original


class TestDefaultConfig:
    """Tests for default configuration."""

    def test_default_youtube_retry_config(self):
        """Test default YouTube retry configuration values."""
        config = DEFAULT_YOUTUBE_RETRY_CONFIG
        assert config.max_retries == 3
        assert config.base_delay == 2.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
