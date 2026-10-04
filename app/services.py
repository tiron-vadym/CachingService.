import hashlib
import json
import uuid
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import PayloadRecord, TransformedStringCache
from app.transformer import transformer, TransformerService


def compute_payload_hash(list_1: list[str], list_2: list[str]) -> str:
    """Compute deterministic SHA-256 fingerprint for input lists.
    
    Args:
        list_1: First list of strings.
        list_2: Second list of strings.
        
    Returns:
        Hexadecimal SHA-256 string.
    """
    serialized = json.dumps(
        {"list_1": list_1, "list_2": list_2},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def interleave_strings(list_1: list[str], list_2: list[str]) -> str:
    """Interleave two lists of strings and join with a comma.
    
    Args:
        list_1: First list of strings.
        list_2: Second list of strings.
        
    Returns:
        Interleaved string joined by ', '.
    """
    interleaved: list[str] = []
    for item1, item2 in zip(list_1, list_2):
        interleaved.append(item1)
        interleaved.append(item2)
    return ", ".join(interleaved)


async def get_or_create_payload(
    session: AsyncSession,
    list_1: list[str],
    list_2: list[str],
    transformer_svc: TransformerService = transformer,
) -> Tuple[str, bool]:
    """Retrieve existing payload ID or generate and cache a new payload.
    
    Minimizes transformer calls by:
    1. Reusing payload identifier if exact payload was already generated before.
    2. Deduplicating distinct strings across both lists within the request.
    3. Reusing cached string transformation outcomes from database cache.
    4. Only calling external transformer function for uncached distinct strings.
    
    Args:
        session: Database async session.
        list_1: First list of strings.
        list_2: Second list of strings.
        transformer_svc: Transformer service to use.
        
    Returns:
        Tuple of (payload_id, is_reused).
    """
    input_hash = compute_payload_hash(list_1, list_2)

    # 1. Check if payload with this input hash was already generated before
    stmt_payload = select(PayloadRecord).where(PayloadRecord.input_hash == input_hash)
    result_payload = await session.execute(stmt_payload)
    existing_payload = result_payload.scalars().first()

    if existing_payload is not None:
        return existing_payload.id, True

    # 2. Collect unique strings across both input lists
    unique_strings = set(list_1) | set(list_2)

    # 3. Retrieve already cached transformations from database
    cache_map: dict[str, str] = {}
    if unique_strings:
        stmt_cache = select(TransformedStringCache).where(
            TransformedStringCache.source_text.in_(unique_strings)
        )
        result_cache = await session.execute(stmt_cache)
        cached_items = result_cache.scalars().all()
        for item in cached_items:
            cache_map[item.source_text] = item.transformed_text

    # 4. Transform uncached strings and save them into the cache
    new_cache_entries: list[TransformedStringCache] = []
    for text in unique_strings:
        if text not in cache_map:
            transformed_val = await transformer_svc.transform(text)
            cache_map[text] = transformed_val
            new_cache_entries.append(
                TransformedStringCache(
                    source_text=text,
                    transformed_text=transformed_val,
                )
            )

    if new_cache_entries:
        session.add_all(new_cache_entries)

    # 5. Build interleaved transformed output
    transformed_1 = [cache_map[s] for s in list_1]
    transformed_2 = [cache_map[s] for s in list_2]
    output_str = interleave_strings(transformed_1, transformed_2)

    # 6. Save newly generated payload record
    payload_id = str(uuid.uuid4())
    payload_record = PayloadRecord(
        id=payload_id,
        input_hash=input_hash,
        output=output_str,
    )
    session.add(payload_record)
    await session.commit()

    return payload_id, False


async def get_payload_by_id(
    session: AsyncSession,
    payload_id: str,
) -> Optional[PayloadRecord]:
    """Retrieve payload record by unique identifier.
    
    Args:
        session: Database async session.
        payload_id: Unique payload identifier.
        
    Returns:
        PayloadRecord if found, None otherwise.
    """
    stmt = select(PayloadRecord).where(PayloadRecord.id == payload_id)
    result = await session.execute(stmt)
    return result.scalars().first()
