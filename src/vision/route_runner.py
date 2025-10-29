"""Utilities to load declarative routes and produce responses for vision operators."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, List, Any


@dataclass
class Prediction:
    label: str
    confidence: float


@dataclass
class ExplainResult:
    response: str
    word_count: int
    latencies: Dict[str, int]
    predictions: List[Prediction]


class ExplainThisRoute:
    """Route runner for the Explain This vision flow."""

    def __init__(self, base_path: Path | None = None, route_name: str = "explain_this") -> None:
        self._root = base_path or Path(__file__).resolve().parents[2]
        self._routes_dir = self._root / "config" / "routes"
        self._templates_dir = self._root / "templates"
        self._config = self._load_route(route_name)
        self._template = self._load_template(self._config["respond"]["template"])
        (
            self._min_conf_default,
            self._min_conf_environments,
        ) = self._parse_min_confidence(self._config["extract"].get("min_confidence", 0.0))
        self._min_conf = self._min_conf_default
        self._max_words = int(self._config["respond"].get("max_words", 35))
        self._low_conf_tip = self._config["respond"].get(
            "low_confidence_tip", "Tip: rescan for clarity."
        )
        self._steady_message = self._config["respond"].get("steady_message", "Confidence steady.")

    def _load_route(self, route_name: str) -> Dict[str, Any]:
        route_path = self._routes_dir / f"{route_name}.yaml"
        with route_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _load_template(self, template_name: str) -> str:
        template_path = self._templates_dir / template_name
        with template_path.open("r", encoding="utf-8") as handle:
            return handle.read().strip()

    def run(self, fixture: Dict[str, Any]) -> ExplainResult:
        self._min_conf = self._resolve_min_confidence(fixture.get("context"))
        predictions = [
            Prediction(label=item["label"], confidence=float(item["confidence"]))
            for item in fixture["predictions"][:3]
        ]
        top1, alt1, alt2 = predictions
        tail = self._steady_message
        if top1.confidence < self._min_conf:
            tail = self._low_conf_tip

        response = self._template.format(
            top1_label=top1.label,
            top1_pct=self._format_pct(top1.confidence),
            alt1_label=alt1.label,
            alt1_pct=self._format_pct(alt1.confidence),
            alt2_label=alt2.label,
            alt2_pct=self._format_pct(alt2.confidence),
            tail=tail,
        )

        word_count = len(response.split())
        if word_count > self._max_words:
            raise ValueError(
                f"Response exceeded word budget ({word_count} > {self._max_words}): {response}"
            )

        latencies = self._compute_latencies(fixture.get("timings", {}))

        return ExplainResult(
            response=response,
            word_count=word_count,
            latencies=latencies,
            predictions=predictions,
        )

    def _compute_latencies(self, timing_payload: Dict[str, Any]) -> Dict[str, int]:
        capture = int(timing_payload.get("capture", 0))
        perceive = int(timing_payload.get("perceive", 0))
        extract = int(timing_payload.get("extract", 0))
        respond = int(timing_payload.get("respond", 0))
        total = capture + perceive + extract + respond
        return {
            "capture": capture,
            "perceive": perceive,
            "extract": extract,
            "respond": respond,
            "total": total,
        }

    def _parse_min_confidence(self, min_conf_config: Any) -> tuple[float, Dict[str, float]]:
        if isinstance(min_conf_config, dict):
            default = float(min_conf_config.get("default", 0.0))
            environments = {
                key.lower(): float(value)
                for key, value in min_conf_config.items()
                if key != "default"
            }
            return default, environments
        return float(min_conf_config), {}

    def _resolve_min_confidence(self, context: Any) -> float:
        if not isinstance(context, dict):
            return self._min_conf_default
        environment = context.get("environment")
        if isinstance(environment, str):
            key = environment.lower()
            if key in self._min_conf_environments:
                return self._min_conf_environments[key]
        return self._min_conf_default

    @staticmethod
    def _format_pct(confidence: float) -> str:
        return f"{round(confidence * 100):d}"


__all__ = ["ExplainThisRoute", "ExplainResult", "Prediction"]
