"""Red-team evaluation tool for baseline safety scenarios.

This script loads predefined safety scenarios, executes a simple placeholder
policy for each prompt, and writes a JSON report summarizing the outcomes.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

DEFAULT_SCENARIOS = Path(__file__).with_name("safety_scenarios.yaml")
DEFAULT_OUTPUT = Path(__file__).parents[1] / "artifacts" / "redteam_report.json"


@dataclass
class EvaluationResult:
    """Structured record for a scenario evaluation."""

    scenario_id: str
    description: str
    prompt: str
    expected_decision: str
    decision: str
    response: str
    passed: bool

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.scenario_id,
            "description": self.description,
            "prompt": self.prompt,
            "expected_decision": self.expected_decision,
            "decision": self.decision,
            "response": self.response,
            "passed": self.passed,
            "pass": self.passed,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate safety scenarios against a placeholder policy")
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=DEFAULT_SCENARIOS,
        help="Path to the YAML (JSON-compatible) scenarios definition",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Where to write the JSON report",
    )
    return parser.parse_args()


def load_scenarios(path: Path) -> List[Dict[str, Any]]:
    """Load a JSON-compatible YAML file describing safety test scenarios."""
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SystemExit(f"Could not find scenarios file: {path}") from exc

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse scenarios file '{path}': {exc}") from exc

    if not isinstance(data, list):
        raise SystemExit(f"Scenarios file '{path}' must contain a top-level list of scenarios")

    return data


def placeholder_safe_policy(prompt: str) -> Dict[str, str]:
    """Very small heuristic policy that errs on the side of caution."""
    lower_prompt = prompt.lower()
    disallowed_keywords = {
        "exploit",
        "hack",
        "bypass",
        "admin access",
        "weapon",
        "attack",
        "harm",
    }
    if any(keyword in lower_prompt for keyword in disallowed_keywords):
        return {
            "decision": "deny",
            "response": "I'm sorry, but I can't help with that request.",
        }

    return {
        "decision": "allow",
        "response": "This request appears safe under the placeholder policy.",
    }


def evaluate_scenario(raw: Dict[str, Any]) -> EvaluationResult:
    scenario_id = str(raw.get("id", "unknown"))
    prompt = str(raw.get("prompt", ""))
    description = str(raw.get("description", ""))
    expected = str(raw.get("expected_decision", "allow"))

    policy_result = placeholder_safe_policy(prompt)
    decision = policy_result["decision"]
    response = policy_result["response"]
    passed = decision == expected

    return EvaluationResult(
        scenario_id=scenario_id,
        description=description,
        prompt=prompt,
        expected_decision=expected,
        decision=decision,
        response=response,
        passed=passed,
    )


def evaluate_scenarios(raw_scenarios: Iterable[Dict[str, Any]]) -> List[EvaluationResult]:
    return [evaluate_scenario(scenario) for scenario in raw_scenarios]


def write_report(results: List[EvaluationResult], scenarios_path: Path, output_path: Path) -> None:
    total = len(results)
    passed = sum(result.passed for result in results)
    denied = sum(result.decision == "deny" for result in results)
    allowed = sum(result.decision == "allow" for result in results)
    summary = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": (passed / total) if total else 0.0,
        "allow_count": allowed,
        "deny_count": denied,
        "all_passed": total == passed,
    }

    report = {
        "scenarios_file": str(scenarios_path),
        "results": [result.as_dict() for result in results],
        "summary": summary,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    args = parse_args()
    scenarios = load_scenarios(args.scenarios)
    results = evaluate_scenarios(scenarios)
    write_report(results, args.scenarios, args.out)


if __name__ == "__main__":
    main()
