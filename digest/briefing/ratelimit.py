import asyncio


class AsyncRateLimiter:
    """Spaces out request starts to stay under a requests-per-minute cap.

    Groq free-tier limits for llama-3.3-70b-versatile are 30 RPM / 12K TPM.
    Our classification calls are tiny (~250 tokens), so RPM is the binding
    constraint — this limiter paces request starts to respect it.
    """

    def __init__(self, rpm: int):
        self._min_interval = 60.0 / rpm
        self._lock = asyncio.Lock()
        self._next_allowed = 0.0

    async def acquire(self) -> None:
        async with self._lock:
            now = asyncio.get_event_loop().time()
            wait = self._next_allowed - now
            if wait > 0:
                await asyncio.sleep(wait)
                now = asyncio.get_event_loop().time()
            self._next_allowed = now + self._min_interval
