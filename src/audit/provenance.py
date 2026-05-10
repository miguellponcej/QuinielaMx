"""Traceability records required before any prediction is emitted."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODEL_VERSION = "QuinielaPredictor MX v0.1.0"


class TraceValidationError(ValueError):
    """Raised when prediction traceability is incomplete."""


@dataclass(frozen=True)
class SourceRecord:
    """One internal or external source consulted for a prediction run."""

    name: str
    location: str
    source_type: str
    status: str
    updated_at: str | None = None
    consulted_at: str | None = None
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return serializable source record."""

        return asdict(self)


@dataclass(frozen=True)
class PredictionTrace:
    """Complete traceability context for a prediction run."""

    model_version: str = MODEL_VERSION
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    internal_files: list[SourceRecord] = field(default_factory=list)
    web_sources: list[SourceRecord] = field(default_factory=list)
    fresh_data: list[str] = field(default_factory=list)
    incomplete_data: list[str] = field(default_factory=list)
    discarded_data: list[str] = field(default_factory=list)
    model_variables: list[str] = field(default_factory=list)
    recalibration_status: str = "No recalibrado: datos insuficientes o no solicitados."

    def validate_ready(self) -> None:
        """Block predictions when traceability is incomplete."""

        if not self.internal_files:
            raise TraceValidationError("Prediction blocked: no internal files were registered.")
        if not self.web_sources:
            raise TraceValidationError("Prediction blocked: no web sources were registered.")
        if not self.model_variables:
            raise TraceValidationError("Prediction blocked: no model variables were registered.")
        if not self.model_version:
            raise TraceValidationError("Prediction blocked: model version is missing.")
        if any(not source.name or not source.location or not source.status for source in self.internal_files):
            raise TraceValidationError("Prediction blocked: at least one internal source is incomplete.")
        if any(not source.name or not source.location or not source.status for source in self.web_sources):
            raise TraceValidationError("Prediction blocked: at least one web source is incomplete.")

    def as_dict(self) -> dict[str, Any]:
        """Return serializable trace."""

        return {
            "model_version": self.model_version,
            "generated_at": self.generated_at,
            "internal_files": [source.as_dict() for source in self.internal_files],
            "web_sources": [source.as_dict() for source in self.web_sources],
            "fresh_data": self.fresh_data,
            "incomplete_data": self.incomplete_data,
            "discarded_data": self.discarded_data,
            "model_variables": self.model_variables,
            "recalibration_status": self.recalibration_status,
        }

    def compact_summary(self) -> dict[str, Any]:
        """Return compact trace fields for tabular outputs."""

        return {
            "version_modelo": self.model_version,
            "fecha_hora_prediccion": self.generated_at,
            "archivos_usados": "; ".join(source.name for source in self.internal_files),
            "fuentes_web_consultadas": "; ".join(source.name for source in self.web_sources),
            "datos_actualizados": "; ".join(self.fresh_data) if self.fresh_data else "No confirmado",
            "datos_incompletos": "; ".join(self.incomplete_data) if self.incomplete_data else "Sin faltantes registrados",
            "datos_descartados": "; ".join(self.discarded_data) if self.discarded_data else "Ninguno",
            "variables_modelo": "; ".join(self.model_variables),
            "estado_recalibracion": self.recalibration_status,
        }


def build_manual_trace(
    internal_file_paths: list[str | Path],
    web_locations: list[str],
    fresh_data: list[str] | None = None,
    incomplete_data: list[str] | None = None,
    discarded_data: list[str] | None = None,
    model_variables: list[str] | None = None,
    recalibration_status: str = "No recalibrado: datos insuficientes para ajuste robusto.",
) -> PredictionTrace:
    """Build a trace for manual/local prediction workflows."""

    now = datetime.now(timezone.utc).isoformat()
    internal_files = [
        SourceRecord(
            name=Path(path).name,
            location=str(path),
            source_type="internal_file",
            status="cargado",
            consulted_at=now,
        )
        for path in internal_file_paths
    ]
    web_sources = [
        SourceRecord(
            name=location,
            location=location,
            source_type="web",
            status="registrada/consultar antes de pronostico real",
            consulted_at=now,
            notes="Fuente oficial o de mercado que debe verificarse para una corrida en tiempo real.",
        )
        for location in web_locations
    ]
    return PredictionTrace(
        generated_at=now,
        internal_files=internal_files,
        web_sources=web_sources,
        fresh_data=fresh_data or [],
        incomplete_data=incomplete_data or [],
        discarded_data=discarded_data or [],
        model_variables=model_variables
        or [
            "probabilidades_modelo",
            "probabilidades_mercado_si_existen",
            "entropia",
            "brecha_top1_top2",
            "riesgo",
        ],
        recalibration_status=recalibration_status,
    )

