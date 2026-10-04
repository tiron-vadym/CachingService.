from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import (
    PayloadCreateRequest,
    PayloadCreateResponse,
    PayloadReadResponse,
)
from app.services import get_or_create_payload, get_payload_by_id

router = APIRouter(prefix="/payload", tags=["Payloads"])


@router.post(
    "",
    response_model=PayloadCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or reuse generated payload",
    description=(
        "Transforms input strings using a simulated external transformer, "
        "interleaves them, and caches intermediate results. "
        "If an identical payload has been generated before, its existing identifier is reused."
    ),
)
async def create_payload(
    request: PayloadCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> PayloadCreateResponse:
    payload_id, is_reused = await get_or_create_payload(
        session=session,
        list_1=request.list_1,
        list_2=request.list_2,
    )

    message = (
        "Payload already exists; reused existing identifier"
        if is_reused
        else "Payload generated and stored successfully"
    )

    return PayloadCreateResponse(id=payload_id, message=message)


@router.get(
    "/{payload_id}",
    response_model=PayloadReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Read generated payload output",
    description="Retrieve the generated interleaved transformed payload by identifier.",
)
async def read_payload(
    payload_id: str,
    session: AsyncSession = Depends(get_session),
) -> PayloadReadResponse:
    payload = await get_payload_by_id(session=session, payload_id=payload_id)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payload with identifier '{payload_id}' was not found.",
        )

    return PayloadReadResponse(output=payload.output)
