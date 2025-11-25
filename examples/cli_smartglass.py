"""
Command-line interface for interacting with SmartGlassAgent.

This example supports multimodal queries with optional image context and
switchable language backends (GPT-2 or the SNN placeholder backend).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from pprint import pprint

# Ensure the src directory is importable when running from the repo root
ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gpt2_generator import GPT2Backend  # noqa: E402
from llm_snn_backend import SNNLLMBackend  # noqa: E402
from smartglass_agent import SmartGlassAgent  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive SmartGlass CLI")
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Optional path to an image for visual context",
    )
    parser.add_argument(
        "--backend",
        choices=["gpt2", "snn"],
        default="gpt2",
        help="Language backend to use (default: gpt2)",
    )
    return parser.parse_args()


def initialize_agent(backend_choice: str) -> SmartGlassAgent:
    if not os.environ.get("PROVIDER"):
        os.environ["PROVIDER"] = "mock"

    if backend_choice == "snn":
        llm_backend = SNNLLMBackend()
    else:
        llm_backend = GPT2Backend()

    return SmartGlassAgent(
        whisper_model="base",
        clip_model="openai/clip-vit-base-patch32",
        llm_backend=llm_backend,
    )


def main() -> None:
    args = parse_args()

    image_path: str | None = args.image
    if image_path is not None:
        potential_path = ROOT / image_path
        if potential_path.exists():
            image_path = str(potential_path)
        else:
            print(f"Warning: image path '{image_path}' does not exist; continuing without it.")
            image_path = None

    agent = initialize_agent(args.backend)

    print("\nType your queries below. Press Ctrl+C or send an empty line to exit.")

    try:
        while True:
            user_input = input("You: ").strip()
            if not user_input:
                print("Exiting.")
                break

            result = agent.process_multimodal_query(
                text_query=user_input,
                image_input=image_path,
            )

            response_text = result.get("response", result)
            print(f"Agent: {response_text}")

            actions = result.get("actions") or []
            if actions:
                print("Actions:")
                pprint(actions)
    except KeyboardInterrupt:
        print("\nExiting.")


if __name__ == "__main__":
    main()
