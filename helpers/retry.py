import asyncio
import random
from functools import wraps
from typing import Callable, TypeVar, Any, List, Tuple

T = TypeVar('T')


def async_retry(
    retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_on: List[Tuple[Any, str]] = None
):
    """
    Decorator for async functions to retry with exponential backoff.
    
    Args:
        retries: Maximum number of retries
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        retry_on: List of (exception class, message pattern) tuples to retry on
                  If None, retry on all exceptions
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(retries + 1):  # +1 for the initial attempt
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Check if we should retry on this exception
                    should_retry = False
                    if retry_on is None:
                        # Retry on all exceptions
                        should_retry = True
                    else:
                        for exc_class, msg_pattern in retry_on:
                            if isinstance(e, exc_class) and (msg_pattern is None or msg_pattern in str(e)):
                                should_retry = True
                                break
                    
                    # If not retryable or last attempt, re-raise
                    if not should_retry or attempt == retries:
                        raise
                    
                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 0.1 * base_delay), max_delay)
                    
                    # Log retry
                    print(f"Retry {attempt + 1}/{retries} after {delay:.2f}s due to: {e}")
                    
                    # Wait before retrying
                    await asyncio.sleep(delay)
            
            # We should never get here, but just in case
            raise last_exception
        
        return wrapper
    
    return decorator
