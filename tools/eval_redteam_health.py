#!/usr/bin/env python3
"""Red-team evaluation tool for health skills scenarios.

This script loads health-related test scenarios from redteam/health.yaml,
evaluates them using heuristics or model stubs, and emits a JSON report
showing which tests passed/failed. Critical failures cause non-zero exit.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
except ImportError:
    # Fallback to json if yaml not available
    yaml = None  # type: ignore


@dataclass
class TestResult:
    """Structured record for a health scenario test result."""

    test_id: str
    skill: str
    category: str
    description: str
    input_text: str
    expected: str
    actual: str
    passed: bool
    severity: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.test_id,
            "skill": self.skill,
            "category": self.category,
            "description": self.description,
            "input": self.input_text,
            "expected": self.expected,
            "actual": self.actual,
            "passed": self.passed,
            "severity": self.severity,
        }


def load_health_scenarios(yaml_path: Path) -> List[Dict[str, Any]]:
    """Load health test scenarios from YAML file."""
    if not yaml_path.exists():
        raise SystemExit(f"Scenarios file not found: {yaml_path}")

    content = yaml_path.read_text(encoding="utf-8")

    # Try YAML first, fallback to JSON
    if yaml is not None:
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise SystemExit(f"Failed to parse YAML: {exc}") from exc
    else:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Failed to parse JSON (pyyaml not available): {exc}") from exc

    if not isinstance(data, list):
        raise SystemExit("Health scenarios file must contain a list of tests")

    return data


def heuristic_health_policy(input_text: str, skill: str, category: str) -> str:
    """Simple heuristic policy to evaluate health-related requests.
    
    Returns 'deny' for dangerous patterns, 'allow' for safe requests.
    """
    lower_input = input_text.lower()
    
    # Critical patterns that should be denied
    dangerous_keywords = {
        "diagnose", "diagnosis", "do i have", "tell me if",
        "my friend", "my coworker", "another person", "without asking",
        "blood pressure medication", "drug interaction", "aspirin with",
        "going to fall", "fall risk",
    }
    
    # Check for dangerous patterns
    for keyword in dangerous_keywords:
        if keyword in lower_input:
            return "deny"
    
    # Patterns suggesting third-party monitoring without consent
    if any(word in lower_input for word in ["friend's", "coworker's", "their", "them"]):
        if not any(safe in lower_input for safe in ["my own", "myself", "my"]):
            return "deny"
    
    # Safe patterns that should be allowed
    safe_patterns = ["remind me", "my own", "during my", "monitor my own"]
    if any(pattern in lower_input for pattern in safe_patterns):
        return "allow"
    
    # Default to deny for health-critical categories
    if category in ["diagnosis", "medication-interaction"]:
        return "deny"
    
    return "allow"


def evaluate_scenario(scenario: Dict[str, Any]) -> TestResult:
    """Evaluate a single health scenario."""
    test_id = str(scenario.get("id", "unknown"))
    skill = str(scenario.get("skill", "unknown"))
    category = str(scenario.get("category", "unknown"))
    description = str(scenario.get("description", ""))
    input_text = str(scenario.get("input", ""))
    expected = str(scenario.get("expected", "deny"))
    severity = str(scenario.get("severity", "medium"))
    
    # Evaluate using heuristic policy
    actual = heuristic_health_policy(input_text, skill, category)
    passed = (actual == expected)
    
    return TestResult(
        test_id=test_id,
        skill=skill,
        category=category,
        description=description,
        input_text=input_text,
        expected=expected,
        actual=actual,
        passed=passed,
        severity=severity,
    )


def main() -> int:
    """Main entry point."""
    repo_root = Path(__file__).resolve().parents[1]
    scenarios_path = repo_root / "redteam" / "health.yaml"
    report_path = repo_root / "redteam" / "health_report.json"
    
    # Load and evaluate scenarios
    try:
        scenarios = load_health_scenarios(scenarios_path)
    except SystemExit as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    
    results = [evaluate_scenario(s) for s in scenarios]
    
    # Generate summary
    total = len(results)
    passed = sum(r.passed for r in results)
    failed = total - passed
    critical_failures = [r for r in results if not r.passed and r.severity == "critical"]
    
    # Build report
    report = {
        "scenarios_file": str(scenarios_path),
        "total": total,
        "passed": passed,
        "failed": failed,
        "critical_failures": len(critical_failures),
        "results": [r.as_dict() for r in results],
        "passed_flags": {r.test_id: r.passed for r in results},
    }
    
    # Write report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    
    print(f"Health red-team evaluation complete:")
    print(f"  Total: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Critical failures: {len(critical_failures)}")
    print(f"Report written to: {report_path}")
    
    # Exit with non-zero if critical failures found
    if critical_failures:
        print("\nCritical failures detected:", file=sys.stderr)
        for result in critical_failures:
            print(f"  - {result.test_id}: {result.description}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
