"""Unit price route combining price and weight extractions."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class UnitPriceResult:
    response: str
    word_count: int
    latencies: Dict[str, int]
    unit_price: Optional[float]
    price_label: Optional[str]
    weight_label: Optional[str]
    confidence: float
    matched: bool


class UnitPriceRoute:
    def __init__(
        self,
        base_path: Path | None = None,
        route_name: str = "unit_price",
        unit_mode: str | None = None,
    ) -> None:
        self._root = base_path or Path(__file__).resolve().parents[2]
        self._routes_dir = self._root / "config" / "routes"
        self._templates_dir = self._root / "templates"
        self._schemas_dir = self._root / "schemas"
        self._config = self._load_route(route_name)
        self._price_schema = self._load_schema(self._config["extract"]["price_schema"])
        self._weight_schema = self._load_schema(self._config["extract"]["weight_schema"])
        self._price_pattern = re.compile(self._price_schema["pattern"])
        self._weight_pattern = re.compile(self._weight_schema["pattern"], re.IGNORECASE)
        self._min_conf = float(self._config["extract"].get("min_confidence", 0.0))
        respond_cfg = self._config["respond"]
        self._template = (self._templates_dir / respond_cfg["template"]).read_text().strip()
        self._unit_modes = respond_cfg.get("unit_modes", {})
        self._unit_mode = unit_mode or respond_cfg.get("unit_mode")
        self._unit = respond_cfg.get("unit", "/100g")
        self._reference_grams = float(respond_cfg.get("reference_grams", 100.0))
        self._formula = respond_cfg.get("formula", "{price} / ({weight}/100)")
        if self._unit_modes:
            if not self._unit_mode or self._unit_mode not in self._unit_modes:
                self._unit_mode = next(iter(self._unit_modes))
            mode_cfg = self._unit_modes.get(self._unit_mode, {})
            if isinstance(mode_cfg, dict):
                self._unit = mode_cfg.get("unit", self._unit)
                if "reference_grams" in mode_cfg:
                    self._reference_grams = float(mode_cfg["reference_grams"])
                else:
                    self._reference_grams = float(mode_cfg.get("reference_grams", self._reference_grams))
                self._formula = mode_cfg.get("formula", self._formula)
            else:
                self._unit = str(mode_cfg)
        self._low_conf_tip = respond_cfg.get(
            "low_confidence_tip", "Tip: ensure price and weight are visible."
        )
        self._steady_message = respond_cfg.get("steady_message", "Confidence steady.")
        self._missing_message = respond_cfg.get("missing_message", "Data missing")

    def _load_route(self, route_name: str) -> Dict[str, Any]:
        with (self._routes_dir / f"{route_name}.yaml").open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _load_schema(self, schema_name: str) -> Dict[str, Any]:
        with (self._schemas_dir / schema_name).open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def run(self, fixture: Dict[str, Any]) -> UnitPriceResult:
        price_text = fixture.get("price_text") or fixture.get("ocr_text", "")
        weight_text = fixture.get("weight_text") or fixture.get("ocr_text", "")
        price_conf = float(fixture.get("price_confidence", self._min_conf))
        weight_conf = float(fixture.get("weight_confidence", self._min_conf))

        price_label, price_value = self._extract_price(price_text)
        weight_label, grams = self._extract_weight(weight_text)

        matched = price_value is not None and grams is not None
        combined_conf = min(price_conf, weight_conf)

        unit_price: Optional[float] = None
        result_label: Optional[str] = None
        if matched:
            reference = self._reference_grams if self._reference_grams else 100.0
            unit_price = price_value / (grams / reference)
            currency_symbol = price_label[0] if price_label else "$"
            result_label = f"{currency_symbol}{unit_price:.2f}{self._unit}"

        tail = self._steady_message if matched and combined_conf >= self._min_conf else self._low_conf_tip
        label_result = result_label if result_label else self._missing_message

        response = self._template.format(
            result=label_result,
            price_label=price_label or "price?",
            weight_label=weight_label or "weight?",
            tail=tail,
        )

        word_count = len(response.split())
        if word_count > int(self._config["respond"].get("max_words", 35)):
            raise ValueError("Response exceeded HUD budget")

        latencies = self._compute_latencies(fixture.get("timings", {}))

        return UnitPriceResult(
            response=response,
            word_count=word_count,
            latencies=latencies,
            unit_price=round(unit_price, 2) if unit_price is not None else None,
            price_label=price_label,
            weight_label=weight_label,
            confidence=combined_conf,
            matched=matched,
        )

    def _extract_price(self, text: str) -> tuple[Optional[str], Optional[float]]:
        match = self._price_pattern.search(text)
        if not match:
            return None, None
        if match.group("value") is not None:
            raw_value = match.group("value")
            currency = match.group("currency") or self._infer_currency(text, raw_value)
        else:
            raw_value = match.group("plain")
            currency = self._infer_currency(text, raw_value)
        value = self._to_float(raw_value)
        if value is None:
            return None, None
        return f"{currency}{value:.2f}", value

    def _extract_weight(self, text: str) -> tuple[Optional[str], Optional[float]]:
        match = self._weight_pattern.search(text)
        if not match:
            return None, None
        value = float(match.group("value").replace(",", "."))
        unit = match.group("unit")
        grams, label = self._to_grams(value, unit, match.group(0))
        if grams is None or label is None:
            return None, None
        return label, grams

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

    @staticmethod
    def _to_float(value_str: str) -> Optional[float]:
        cleaned = value_str.replace(" ", "")
        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "")
                cleaned = cleaned.replace(",", ".")
        elif "," in cleaned and "." not in cleaned:
            cleaned = cleaned.replace(".", "")
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def _to_grams(value: float, unit: str, raw_label: str | None = None) -> tuple[Optional[float], Optional[str]]:
        normalized_unit = unit.lower()
        original_label = UnitPriceRoute._clean_label(raw_label) if raw_label else None
        default_label = original_label or UnitPriceRoute._clean_label(
            f"{UnitPriceRoute._format_value(value)} {UnitPriceRoute._canonical_unit(normalized_unit)}"
        )

        if normalized_unit.startswith("kg") or "kilogram" in normalized_unit:
            grams = value * 1000
            grams_label = UnitPriceRoute._format_grams_label(grams)
            return grams, UnitPriceRoute._clean_label(f"{default_label} ({grams_label})")
        if normalized_unit in {"g", "gram", "grams"}:
            grams = value
            return grams, default_label
        if normalized_unit.startswith("oz") or "ounce" in normalized_unit:
            grams = value * 28.3495
            grams_label = UnitPriceRoute._format_grams_label(grams)
            return grams, UnitPriceRoute._clean_label(f"{default_label} ({grams_label})")
        if normalized_unit.startswith("lb") or "pound" in normalized_unit:
            grams = value * 453.592
            grams_label = UnitPriceRoute._format_grams_label(grams)
            return grams, UnitPriceRoute._clean_label(f"{default_label} ({grams_label})")
        return None, original_label

    @staticmethod
    def _format_value(value: float) -> str:
        if float(value).is_integer():
            return f"{int(value)}"
        formatted = f"{value:.2f}".rstrip("0").rstrip(".")
        return formatted

    @staticmethod
    def _format_grams_label(grams: float) -> str:
        if abs(grams - round(grams)) < 1e-2:
            return f"{round(grams):.0f}g"
        precision = "{:.2f}" if grams < 100 else "{:.1f}"
        formatted = precision.format(grams)
        trimmed = formatted.rstrip("0").rstrip(".")
        return f"{trimmed}g"

    @staticmethod
    def _canonical_unit(unit: str) -> str:
        mapping = {
            "grams": "g",
            "gram": "g",
            "kilogram": "kg",
            "kilograms": "kg",
            "ounce": "oz",
            "ounces": "oz",
            "pound": "lb",
            "pounds": "lb",
            "lbs": "lb",
        }
        return mapping.get(unit, unit)

    @staticmethod
    def _clean_label(label: str) -> str:
        return re.sub(r"\s+", " ", label.strip())

    @staticmethod
    def _infer_currency(text: str, raw_value: str) -> str:
        if "€" in text or "," in raw_value:
            return "€"
        return "$"
