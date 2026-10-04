import asyncio
import time
import pytest
from app.transformer import TransformerService
from app.config import get_settings


@pytest.mark.asyncio
async def test_transformer_uppercase():
    svc = TransformerService()
    result = await svc.transform("hello world")
    assert result == "HELLO WORLD"
    assert svc.call_count == 1


@pytest.mark.asyncio
async def test_transformer_call_counter():
    svc = TransformerService()
    assert svc.call_count == 0
    await svc.transform("first")
    await svc.transform("second")
    assert svc.call_count == 2
    svc.reset_call_count()
    assert svc.call_count == 0


@pytest.mark.asyncio
async def test_transformer_delay():
    settings = get_settings()
    original_delay = settings.TRANSFORMER_DELAY_SECONDS
    settings.TRANSFORMER_DELAY_SECONDS = 0.05
    try:
        svc = TransformerService()
        start = time.perf_counter()
        await svc.transform("delay test")
        duration = time.perf_counter() - start
        assert duration >= 0.04
    finally:
        settings.TRANSFORMER_DELAY_SECONDS = original_delay
