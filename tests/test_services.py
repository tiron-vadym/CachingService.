import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import normalize_database_url
from app.services import (
    compute_payload_hash,
    get_or_create_payload,
    get_payload_by_id,
    interleave_strings,
)
from app.transformer import TransformerService


def test_normalize_database_url():
    assert normalize_database_url("sqlite:///app.db") == "sqlite+aiosqlite:///app.db"
    assert normalize_database_url("sqlite+aiosqlite:///app.db") == "sqlite+aiosqlite:///app.db"
    assert (
        normalize_database_url("postgresql://user:pass@localhost/db")
        == "postgresql+asyncpg://user:pass@localhost/db"
    )
    assert (
        normalize_database_url("postgresql+asyncpg://user:pass@localhost/db")
        == "postgresql+asyncpg://user:pass@localhost/db"
    )



def test_compute_payload_hash():
    l1 = ["a", "b"]
    l2 = ["c", "d"]
    hash1 = compute_payload_hash(l1, l2)
    hash2 = compute_payload_hash(l1, l2)
    assert hash1 == hash2

    hash3 = compute_payload_hash(l2, l1)
    assert hash1 != hash3


def test_interleave_strings():
    l1 = ["FIRST STRING", "SECOND STRING", "THIRD STRING"]
    l2 = ["OTHER STRING", "ANOTHER STRING", "LAST STRING"]
    expected = "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"
    assert interleave_strings(l1, l2) == expected

    assert interleave_strings([], []) == ""
    assert interleave_strings(["ONE"], ["TWO"]) == "ONE, TWO"


@pytest.mark.asyncio
async def test_get_or_create_payload_caching(
    test_session: AsyncSession,
    fresh_transformer: TransformerService,
):
    l1 = ["first string", "second string", "third string"]
    l2 = ["other string", "another string", "last string"]

    # 1. First call: 6 unique strings, so transformer must be called 6 times
    payload_id_1, is_reused_1 = await get_or_create_payload(
        session=test_session,
        list_1=l1,
        list_2=l2,
        transformer_svc=fresh_transformer,
    )

    assert is_reused_1 is False
    assert fresh_transformer.call_count == 6

    # 2. Second call with exact same inputs: must reuse payload identifier
    # and NOT make any new transformer calls
    payload_id_2, is_reused_2 = await get_or_create_payload(
        session=test_session,
        list_1=l1,
        list_2=l2,
        transformer_svc=fresh_transformer,
    )

    assert is_reused_2 is True
    assert payload_id_1 == payload_id_2
    assert fresh_transformer.call_count == 6  # Zero additional calls!

    # 3. Third call: new payload, but partially uses already cached strings
    # "first string" is cached, "brand new string" is not cached
    l3 = ["first string"]
    l4 = ["brand new string"]
    payload_id_3, is_reused_3 = await get_or_create_payload(
        session=test_session,
        list_1=l3,
        list_2=l4,
        transformer_svc=fresh_transformer,
    )

    assert is_reused_3 is False
    assert payload_id_3 != payload_id_1
    # Only 1 additional call for "brand new string" because "first string" is in cache!
    assert fresh_transformer.call_count == 7


@pytest.mark.asyncio
async def test_get_or_create_payload_deduplication_within_request(
    test_session: AsyncSession,
    fresh_transformer: TransformerService,
):
    # Both lists contain repeated identical strings
    l1 = ["repeat", "repeat"]
    l2 = ["repeat", "different"]

    # Unique strings: {"repeat", "different"} (2 strings)
    payload_id, is_reused = await get_or_create_payload(
        session=test_session,
        list_1=l1,
        list_2=l2,
        transformer_svc=fresh_transformer,
    )

    assert is_reused is False
    # Verifies transformer was called only 2 times instead of 4
    assert fresh_transformer.call_count == 2

    # Verify retrieved payload output
    record = await get_payload_by_id(test_session, payload_id)
    assert record is not None
    assert record.output == "REPEAT, REPEAT, REPEAT, DIFFERENT"


@pytest.mark.asyncio
async def test_get_payload_by_id(
    test_session: AsyncSession,
    fresh_transformer: TransformerService,
):
    l1 = ["alpha"]
    l2 = ["beta"]
    payload_id, _ = await get_or_create_payload(
        session=test_session,
        list_1=l1,
        list_2=l2,
        transformer_svc=fresh_transformer,
    )

    record = await get_payload_by_id(test_session, payload_id)
    assert record is not None
    assert record.id == payload_id
    assert record.output == "ALPHA, BETA"

    missing = await get_payload_by_id(test_session, "non-existent-uuid")
    assert missing is None
