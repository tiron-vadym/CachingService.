import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field as PydanticField, model_validator
from sqlmodel import Field, SQLModel


class TransformedStringCache(SQLModel, table=True):
    """Database model for caching outcomes of the transformer function."""

    __tablename__ = "transformed_string_cache"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_text: str = Field(index=True, unique=True, nullable=False)
    transformed_text: str = Field(nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class PayloadRecord(SQLModel, table=True):
    """Database model for storing generated payloads."""

    __tablename__ = "payload_records"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        index=True,
    )
    input_hash: str = Field(index=True, unique=True, nullable=False)
    output: str = Field(nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# --- API Request and Response Schemas ---


class PayloadCreateRequest(BaseModel):
    """Request schema for creating a new generated payload."""

    list_1: list[str] = PydanticField(
        ...,
        description="First list of strings",
        examples=[["first string", "second string", "third string"]],
    )
    list_2: list[str] = PydanticField(
        ...,
        description="Second list of strings of identical length",
        examples=[["other string", "another string", "last string"]],
    )

    @model_validator(mode="after")
    def validate_equal_lengths(self) -> "PayloadCreateRequest":
        if len(self.list_1) != len(self.list_2):
            raise ValueError(
                f"list_1 (length {len(self.list_1)}) and list_2 (length {len(self.list_2)}) must have the exact same length"
            )
        return self


class PayloadCreateResponse(BaseModel):
    """Confirmation message with the identifier of the generated payload."""

    id: str = PydanticField(..., description="Unique identifier for the payload")
    message: str = PydanticField(..., description="Confirmation message")


class PayloadReadResponse(BaseModel):
    """Response schema containing the generated payload output."""

    output: str = PydanticField(..., description="Interleaved transformed payload string")


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    database: str
