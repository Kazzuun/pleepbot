from datetime import datetime, timedelta
from typing import Awaitable, Callable, Optional


def memoize_async(*, ttl: Optional[timedelta] = None):
    """
    Decorator for in-memory caching for asynchronous functions.

    Parameters
    ----------
    ttl : timedelta, default=None
        The time to live for the memoized data (the default is None, 
        which implies data is cached indefinitely)
    """
    cache = {}
    def decorator(func: Callable[..., Awaitable]):
        async def wrapper(*args, **kwargs):
            if args in cache:
                result, expiration_time = cache[args]
                if (ttl and datetime.utcnow() > expiration_time) or kwargs.get("force"):
                    del cache[args]
                else:
                    if isinstance(result, list):
                        return result.copy()
                    return result

            result = await func(*args, **kwargs)
            expiration_time = datetime.utcnow() + ttl if ttl else None
            cache[args] = (result, expiration_time)
            if isinstance(result, list):
                return result.copy()
            return result

        return wrapper
    return decorator
