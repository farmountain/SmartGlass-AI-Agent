"""Helpers for importing the vision keyframe utilities without side-effects."""

from __future__ import annotations

import sys
from importlib import util
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parents[1] / "src" / "perception" / "vision_keyframe.py"
    spec = util.spec_from_file_location("_vision_keyframe", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load vision_keyframe module")
    module = util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


vision_keyframe = _load_module()

select_keyframes = vision_keyframe.select_keyframes
frames_from_camera = vision_keyframe.frames_from_camera
VQEncoder = vision_keyframe.VQEncoder
