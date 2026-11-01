"""Schemas for health and hardware diagnostic endpoints."""
from pydantic import BaseModel, Field


class VRAMInfo(BaseModel):
    """VRAM memory statistics in megabytes."""

    used_mb: float = Field(0.0, description="VRAM reserved/used by allocator in MB")
    free_mb: float = Field(0.0, description="Remaining free VRAM in MB")
    total_mb: float = Field(0.0, description="Total VRAM available on default device in MB")
    allocated_mb: float = Field(0.0, description="VRAM actively allocated to PyTorch tensors in MB")


class HealthResponse(BaseModel):
    """Response payload for GET /health liveness and hardware probe."""

    status: str = Field("ok", description="Server operational status")
    device: str = Field(..., description="Active compute device ('cuda' or 'cpu')")
    vram: VRAMInfo = Field(..., description="VRAM memory usage breakdown")
    vram_allocated_mb: float = Field(0.0, description="VRAM actively allocated to PyTorch tensors in MB")
    vram_total_mb: float = Field(0.0, description="Total VRAM available on default device in MB")
