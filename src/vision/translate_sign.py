"""Translate sign route runner that formats OCR translations for HUD display."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class TranslationResult:
    response: str
    word_count: int
    latencies: Dict[str, int]
    translation: str
    language: str
    confidence: float
    glossary_hits: List[str]
    original_text: str
    is_confident: bool


class TranslateSignRoute:
    """Route runner for translating signage with declarative configuration."""

    def __init__(self, base_path: Path | None = None, route_name: str = "translate_sign") -> None:
        self._root = base_path or Path(__file__).resolve().parents[2]
        self._routes_dir = self._root / "config" / "routes"
        self._templates_dir = self._root / "templates"
        self._schemas_dir = self._root / "schemas"
        self._config = self._load_route(route_name)
        self._template = self._load_template(self._config["respond"]["template"])
        self._schema = self._load_schema(self._config["extract"].get("schema"))
        self._min_conf = float(self._config["extract"].get("min_confidence", 0.0))
        self._max_words = int(self._config["respond"].get("max_words", 35))
        self._low_conf_tip = self._config["respond"].get(
            "low_confidence_tip", "Tip: take another photo."
        )
        self._steady_message = self._config["respond"].get("steady_message", "Confidence steady.")
        self._language_overrides = {
            item.lower(): name
            for item, name in self._config.get("language_names", {}).items()
        }
        self._latency_budgets = self._extract_latency_budgets(self._config)

    def _load_route(self, route_name: str) -> Dict[str, Any]:
        with (self._routes_dir / f"{route_name}.yaml").open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _load_template(self, template_name: str) -> str:
        with (self._templates_dir / template_name).open("r", encoding="utf-8") as handle:
            return handle.read().strip()

    def _load_schema(self, schema_name: str | None) -> Dict[str, Any]:
        if not schema_name:
            return {}
        with (self._schemas_dir / schema_name).open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _extract_latency_budgets(config: Dict[str, Any]) -> Dict[str, int]:
        budgets: Dict[str, int] = {}
        for stage in ("capture", "perceive", "extract", "respond"):
            stage_cfg = config.get(stage, {})
            if isinstance(stage_cfg, dict) and "latency_budget_ms" in stage_cfg:
                budgets[stage] = int(stage_cfg["latency_budget_ms"])
        return budgets

    def run(self, fixture: Dict[str, Any]) -> TranslationResult:
        translation = str(fixture.get("translation", "")).strip()
        original = str(
            fixture.get("original_text")
            or fixture.get("sign_text")
            or fixture.get("ocr_text", "")
        ).strip()
        language_name = self._resolve_language_name(fixture)
        glossary_hits = list(fixture.get("glossary_hits") or [])
        hazard = fixture.get("hazard_level")
        confidence = float(fixture.get("confidence", self._min_conf))
        is_confident = confidence >= self._min_conf
        tail = self._steady_message if is_confident else self._low_conf_tip

        response = self._template.format(
            language=language_name,
            translation=translation,
            original=original or "(unreadable)",
            glossary_sentence=self._format_glossary(glossary_hits),
            hazard_sentence=self._format_hazard(hazard),
            tail=tail,
        )
        response = " ".join(response.split())

        word_count = len(response.split())
        if word_count > self._max_words:
            raise ValueError(
                f"Response exceeded word budget ({word_count} > {self._max_words}): {response}"
            )

        latencies = self._compute_latencies(fixture.get("timings", {}))

        return TranslationResult(
            response=response,
            word_count=word_count,
            latencies=latencies,
            translation=translation,
            language=language_name,
            confidence=confidence,
            glossary_hits=glossary_hits,
            original_text=original,
            is_confident=is_confident,
        )

    @staticmethod
    def _format_glossary(glossary_hits: List[str]) -> str:
        if not glossary_hits:
            return ""
        if len(glossary_hits) == 1:
            return f"Keyword: {glossary_hits[0]}."
        return f"Keywords: {', '.join(glossary_hits)}."

    @staticmethod
    def _format_hazard(hazard: Any) -> str:
        if not hazard:
            return ""
        return f"Hazard: {hazard}."

    @staticmethod
    def _compute_latencies(timing_payload: Dict[str, Any]) -> Dict[str, int]:
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

    def _resolve_language_name(self, fixture: Dict[str, Any]) -> str:
        explicit_name = fixture.get("language_name") or fixture.get("expected_language_name")
        if isinstance(explicit_name, str) and explicit_name.strip():
            return explicit_name.strip()
        language_code = fixture.get("language") or fixture.get("detected_language")
        if isinstance(language_code, str):
            key = language_code.lower()
            if key in self._language_overrides:
                return self._language_overrides[key]
            mapping = {
                "ar": "Arabic",
                "de": "German",
                "en": "English",
                "es": "Spanish",
                "fr": "French",
                "it": "Italian",
                "ja": "Japanese",
                "ko": "Korean",
                "pt": "Portuguese",
                "ru": "Russian",
                "zh": "Chinese",
            }
            if key in mapping:
                return mapping[key]
            return language_code.capitalize()
        return "Unknown"

    @property
    def latency_budgets(self) -> Dict[str, int]:
        return dict(self._latency_budgets)


__all__ = ["TranslateSignRoute", "TranslationResult"]
