"""Price scan route that reads OCR text and surfaces shelf pricing."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

@dataclass
class PriceResult:
    response: str
    word_count: int
    latencies: Dict[str, int]
    value: Optional[float]
    formatted: Optional[str]
    confidence: float
    cer: Optional[float]
    matched: bool


class PriceScanRoute:
    """Route runner for price extraction using declarative schema."""

    def __init__(self, base_path: Path | None = None, route_name: str = "price_scan") -> None:
        self._root = base_path or Path(__file__).resolve().parents[2]
        self._routes_dir = self._root / "config" / "routes"
        self._templates_dir = self._root / "templates"
        self._schemas_dir = self._root / "schemas"
        self._config = self._load_route(route_name)
        self._schema = self._load_schema(self._config["extract"]["schema"])
        self._pattern = re.compile(self._schema["pattern"])
        self._min_conf = float(self._config["extract"].get("min_confidence", 0.0))
        self._precision_target = float(self._config["extract"].get("precision_target", 1.0))
        self._template = (self._templates_dir / self._config["respond"]["template"]).read_text().strip()
        self._low_conf_tip = self._config["respond"].get(
            "low_confidence_tip", "Tip: rescan to confirm pricing."
        )
        self._steady_message = self._config["respond"].get("steady_message", "Confidence steady.")
        self._no_price_message = self._config["respond"].get("no_price_message", "No price found")

    def _load_route(self, route_name: str) -> Dict[str, Any]:
        with (self._routes_dir / f"{route_name}.yaml").open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _load_schema(self, schema_name: str) -> Dict[str, Any]:
        with (self._schemas_dir / schema_name).open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def run(self, fixture: Dict[str, Any]) -> PriceResult:
        ocr_text = fixture["ocr_text"]
        confidence = float(fixture.get("confidence", self._min_conf))
        match = self._pattern.search(ocr_text)
        formatted: Optional[str] = None
        value: Optional[float] = None
        cer: Optional[float] = None
        matched = False

        if match:
            if match.group("value") is not None:
                raw_value = match.group("value")
                currency = match.group("currency") or self._infer_currency(ocr_text, raw_value)
            else:
                raw_value = match.group("plain")
                currency = self._infer_currency(ocr_text, raw_value)
            value = self._to_float(raw_value)
            formatted = f"{currency}{value:.2f}" if value is not None else None
            matched = value is not None
            if matched and fixture.get("expected"):
                cer = self._cer(fixture["expected"], formatted)
        else:
            confidence = min(confidence, 0.2)

        tail = self._steady_message if confidence >= self._min_conf and matched else self._low_conf_tip
        label = formatted if matched and formatted else self._no_price_message
        top_pct = int(round(confidence * 100))
        response = self._template.format(
            top1_label=label,
            top1_pct=str(top_pct),
            alt1_label="Confidence",
            alt1_pct=str(top_pct),
            alt2_label="Regex precision",
            alt2_pct=str(int(round(self._precision_target * 100))),
            tail=tail,
        )

        word_count = len(response.split())
        if word_count > int(self._config["respond"].get("max_words", 35)):
            raise ValueError("Response exceeded HUD word budget")

        latencies = self._compute_latencies(fixture.get("timings", {}))

        return PriceResult(
            response=response,
            word_count=word_count,
            latencies=latencies,
            value=value,
            formatted=formatted,
            confidence=confidence,
            cer=cer,
            matched=matched,
        )

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
    def _cer(reference: str, hypothesis: str) -> float:
        ref = reference
        hyp = hypothesis
        dp = [[0] * (len(hyp) + 1) for _ in range(len(ref) + 1)]
        for i in range(len(ref) + 1):
            dp[i][0] = i
        for j in range(len(hyp) + 1):
            dp[0][j] = j
        for i in range(1, len(ref) + 1):
            for j in range(1, len(hyp) + 1):
                cost = 0 if ref[i - 1] == hyp[j - 1] else 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,
                    dp[i][j - 1] + 1,
                    dp[i - 1][j - 1] + cost,
                )
        return dp[len(ref)][len(hyp)] / max(1, len(ref))

    @staticmethod
    def _infer_currency(text: str, value_str: str) -> str:
        if "€" in text or "," in value_str:
            return "€"
        return "$"
