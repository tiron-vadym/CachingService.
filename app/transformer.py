import asyncio
from app.config import get_settings


class TransformerService:
    """Simulates an external transformation service.
    
    Transforms strings (e.g., to uppercase) while simulating network/processing delay.
    Maintains call counters to verify caching efficiency and call minimization.
    """

    def __init__(self) -> None:
        self._call_count: int = 0

    @property
    def call_count(self) -> int:
        """Total number of times the transformation service was invoked."""
        return self._call_count

    def reset_call_count(self) -> None:
        """Reset call counter to zero (useful for tests and metrics)."""
        self._call_count = 0

    async def transform(self, text: str) -> str:
        """Transform an input string to simulated external service output.
        
        Args:
            text: Input string to transform.
            
        Returns:
            Transformed string (uppercase).
        """
        self._call_count += 1
        settings = get_settings()
        if settings.TRANSFORMER_DELAY_SECONDS > 0:
            await asyncio.sleep(settings.TRANSFORMER_DELAY_SECONDS)
        return text.upper()


# Global default transformer service instance
transformer = TransformerService()
