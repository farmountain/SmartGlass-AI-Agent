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
    def __init__(self, base_path: Path | None = None, route_name: str = "unit_price") -> None:
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
        self._template = (self._templates_dir / self._config["respond"]["template"]).read_text().strip()
        self._unit = self._config["respond"].get("unit", "/100g")
        self._formula = self._config["respond"].get("formula", "{price} / ({weight}/100)")
        self._low_conf_tip = self._config["respond"].get(
            "low_confidence_tip", "Tip: ensure price and weight are visible."
        )
        self._steady_message = self._config["respond"].get("steady_message", "Confidence steady.")
        self._missing_message = self._config["respond"].get("missing_message", "Data missing")

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
            unit_price = price_value / (grams / 100)
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
        unit = match.group("unit").lower()
        grams = self._to_grams(value, unit)
        if grams is None:
            return None, None
        label = f"{grams:.0f}g" if grams >= 100 else f"{grams:.2f}g"
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
    def _to_grams(value: float, unit: str) -> Optional[float]:
        unit = unit.lower()
        if unit.startswith("kg") or "kilogram" in unit:
            return value * 1000
        if unit == "g":
            return value
        if unit.startswith("oz"):
            return value * 28.3495
        if unit.startswith("lb") or "pound" in unit:
            return value * 453.592
        return None

    @staticmethod
    def _infer_currency(text: str, raw_value: str) -> str:
        if "€" in text or "," in raw_value:
            return "€"
        return "$"
