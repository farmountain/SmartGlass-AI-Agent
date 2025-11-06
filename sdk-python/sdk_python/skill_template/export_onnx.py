"""Mock ONNX export routine."""
from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass

LOGGER = logging.getLogger(__name__)


@dataclass
class ExportConfig:
    output_path: str = "model.onnx"
    validation_seconds: float = 0.05


class MockExporter:
    """Pretend exporter that writes a dummy ONNX file."""

    def __init__(self, config: ExportConfig | None = None) -> None:
        self.config = config or ExportConfig()
        LOGGER.debug("MockExporter initialized with config: %s", self.config)

    def export(self) -> str:
        LOGGER.info("Validating model prior to export...")
        time.sleep(self.config.validation_seconds)
        LOGGER.info("Writing placeholder ONNX model to %s", self.config.output_path)
        with open(self.config.output_path, "w", encoding="utf-8") as handle:
            handle.write("mock onnx data\n")
        LOGGER.debug("Export complete")
        return self.config.output_path


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output",
        default="model.onnx",
        help="Destination ONNX file (default: model.onnx).",
    )
    parser.add_argument(
        "--validation-seconds",
        type=float,
        default=0.05,
        help="Duration of mock validation before export.",
    )


def run(args: argparse.Namespace) -> int:
    config = ExportConfig(
        output_path=args.output,
        validation_seconds=args.validation_seconds,
    )
    exporter = MockExporter(config)
    exporter.export()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the mock model to ONNX.")
    add_arguments(parser)
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
