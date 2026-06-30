"""Stable I/O contracts. New version suffix (V2) for breaking changes — never overload V1."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Shared column types
# ---------------------------------------------------------------------------

class SeriesColumnV1(BaseModel):
    name: str = Field(description="Pollutant or metric name, e.g. CO2, PM2.5, nox")
    unit: str = Field(description="Unit string, e.g. ppm, µg/m³, ppb")
    values: list[float | None]


class SeriesMetaV1(BaseModel):
    source: Literal["file", "aurn", "europe", "adms", "aurn_csv", "json_export", "other"] = "other"
    site: str | None = None
    timezone: str | None = None
    lat: float | None = None
    lon: float | None = None


# ---------------------------------------------------------------------------
# Public input contracts (one per tool group)
# ---------------------------------------------------------------------------

class SeriesV1(BaseModel):
    """Generic time series input. Used by all non-wind plot and stats tools."""

    timestamps: list[str] = Field(
        description="ISO-8601 datetimes (UTC preferred), same length as each series column"
    )
    series: list[SeriesColumnV1]
    meta: SeriesMetaV1 | None = None

    @field_validator("series")
    @classmethod
    def at_least_one_series(cls, v: list[SeriesColumnV1]) -> list[SeriesColumnV1]:
        if not v:
            raise ValueError("At least one series column is required")
        return v


class WindSeriesV1(BaseModel):
    """Time series with wind data. Required by all polar/directional tools."""

    timestamps: list[str] = Field(description="ISO-8601 datetimes")
    series: list[SeriesColumnV1] = Field(description="Pollutant columns (at least one)")
    ws: list[float] = Field(description="Wind speed (m/s), same length as timestamps")
    wd: list[float] = Field(description="Wind direction (degrees, 0–360), same length as timestamps")
    meta: SeriesMetaV1 | None = None

    @field_validator("series")
    @classmethod
    def at_least_one_series(cls, v: list[SeriesColumnV1]) -> list[SeriesColumnV1]:
        if not v:
            raise ValueError("At least one pollutant series is required")
        return v


class TrajSeriesV1(BaseModel):
    """HYSPLIT back-trajectory data. Required by traj_* tools."""

    date: list[str] = Field(description="Reception datetime for each trajectory point (ISO-8601)")
    lat: list[float] = Field(description="Latitude of trajectory point")
    lon: list[float] = Field(description="Longitude of trajectory point")
    height: list[float] = Field(description="Trajectory height (m AGL)")
    pressure: list[float | None] = Field(description="Pressure (hPa), may be null")
    hour_inc: list[int] = Field(description="Hours back from reception time (negative integers)")
    traj_id: list[int | None] | None = Field(
        default=None,
        description="Optional trajectory identifier for multi-trajectory datasets"
    )
    meta: SeriesMetaV1 | None = None


class ImportParamsV1(BaseModel):
    """Parameters for data import from public networks (AURN, Europe, etc.)."""

    site: str | list[str] = Field(
        description="Site code(s) to import, e.g. 'MY1' for Marylebone Road"
    )
    start_date: str = Field(description="Start date YYYY-MM-DD")
    end_date: str = Field(description="End date YYYY-MM-DD")
    pollutants: list[str] | None = Field(
        default=None,
        description="Pollutant codes to import. None = all available."
    )
    network: Literal["aurn", "aqe", "saqn", "waqn", "ni", "europe"] = "aurn"
    resolution: Literal["hour", "day", "month", "year"] = "hour"


class ImportFileParamsV1(BaseModel):
    """Parameters for importing openair-native file formats from server disk."""

    path: str = Field(description="Absolute or relative path on the MCP server host")
    format: Literal["adms", "aurn_csv"] = Field(description="Import format: ADMS or UK AURN CSV")
    adms_file_type: Literal["unknown", "bgd", "met", "mop", "pst"] = "unknown"
    simplify_names: bool = Field(
        default=True,
        description="Map column names to openair conventions (importADMS / importAURNCsv)",
    )
    site: str | None = Field(default=None, description="Optional site label for SeriesV1 meta")
    timezone: str | None = Field(default=None, description="Optional IANA timezone for meta")


# ---------------------------------------------------------------------------
# Internal R→Python bridge contract (not exposed directly as MCP output)
# ---------------------------------------------------------------------------

class ArtifactV1(BaseModel):
    """Internal contract: what R scripts return to Python for plot tools."""

    artifact: str = Field(description="Absolute file path to the rendered PNG")
    type: Literal["png", "svg"] = "png"
    summary: str
    tool: str | None = None
    extra: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Public output contracts
# ---------------------------------------------------------------------------

class StatsResultV1(BaseModel):
    """Output from numeric/stats tools (aq_stats, time_average, etc.)."""

    stats: dict[str, Any] = Field(description="Named statistics as key-value pairs")
    summary: str = Field(description="One-line human-readable summary")
    tool: str | None = None
    meta: dict[str, Any] | None = None
