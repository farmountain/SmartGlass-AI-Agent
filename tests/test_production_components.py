"""
Integration Tests for Production Architecture Components

Tests CLIPWorldModel, SQLiteContextStore, and RuleBasedPlanner in isolation
by running them as standalone scripts.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent


class TestCLIPWorldModel:
    """Test CLIP world model by running its __main__ block."""

    def test_clip_world_model_standalone(self):
        """Run CLIPWorldModel as module."""
        result = subprocess.run(
            [sys.executable, "-m", "src.clip_world_model"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=60
        )
        assert result.returncode == 0, f"CLIPWorldModel failed:\n{result.stderr}"
        assert "CLIPWorldModel Demonstration" in result.stdout


class TestSQLiteContextStore:
    """Test SQLite context store by running its __main__ block."""

    def test_sqlite_context_store_standalone(self):
        """Run SQLiteContextStore as module."""
        result = subprocess.run(
            [sys.executable, "-m", "src.sqlite_context_store"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"SQLiteContextStore failed:\n{result.stderr}"
        assert "SQLiteContextStore Demonstration" in result.stdout


class TestRuleBasedPlanner:
    """Test rule-based planner by running its __main__ block."""

    def test_rule_based_planner_standalone(self):
        """Run RuleBasedPlanner as module."""
        result = subprocess.run(
            [sys.executable, "-m", "src.rule_based_planner"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"RuleBasedPlanner failed:\n{result.stderr}"
        assert "RuleBasedPlanner Demonstration" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
