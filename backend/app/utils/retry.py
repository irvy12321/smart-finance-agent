import asyncio
import functools
from collections.abc import Callable

from app.utils.logger import get_logger

logger = get_logger("retry")


def async_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    exclude: tuple[type[Exception], ...] = (),
):
    """Retry an async callable on failure.

    ``exclude`` lists exception types that must NOT be retried (e.g. auth or
    bad-request errors, where retrying only wastes calls); they are re-raised
    immediately.
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            current_delay = delay
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exclude:
                    raise
                except exceptions as e:
                    last_exc = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}"
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_retries} retries exhausted for {func.__name__}: {e}"
                        )
            raise last_exc

        return wrapper

    return decorator
