"""Minimal validation test for MetaDatRegistry and provider methods.

This test validates the core functionality without requiring full project dependencies.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test that the module can be parsed and key classes exist
def test_module_structure():
    """Verify the meta.py module has correct structure."""
    import ast
    
    meta_py_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "drivers", "providers", "meta.py"
    )
    
    with open(meta_py_path, 'r') as f:
        tree = ast.parse(f.read())
    
    # Find all class definitions
    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    
    # Verify MetaDatRegistry exists
    assert "MetaDatRegistry" in classes, "MetaDatRegistry class should exist"
    
    # Verify MetaRayBanProvider exists
    assert "MetaRayBanProvider" in classes, "MetaRayBanProvider class should exist"
    
    # Find all function definitions in MetaDatRegistry
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "MetaDatRegistry":
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            assert "set_frame" in methods, "MetaDatRegistry should have set_frame method"
            assert "get_latest_frame" in methods, "MetaDatRegistry should have get_latest_frame method"
            assert "set_audio" in methods, "MetaDatRegistry should have set_audio method"
            assert "get_latest_audio_buffer" in methods, "MetaDatRegistry should have get_latest_audio_buffer method"
            assert "clear_session" in methods, "MetaDatRegistry should have clear_session method"
            assert "list_sessions" in methods, "MetaDatRegistry should have list_sessions method"
    
    # Find all function definitions in MetaRayBanProvider
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "MetaRayBanProvider":
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            assert "has_display" in methods, "MetaRayBanProvider should have has_display method"
            assert "get_latest_frame" in methods, "MetaRayBanProvider should have get_latest_frame method"
            assert "get_latest_audio_buffer" in methods, "MetaRayBanProvider should have get_latest_audio_buffer method"
    
    print("✓ All structure checks passed")


def test_module_imports():
    """Verify key symbols are in __all__."""
    import ast
    
    meta_py_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "drivers", "providers", "meta.py"
    )
    
    with open(meta_py_path, 'r') as f:
        content = f.read()
        tree = ast.parse(content)
    
    # Find __all__ assignment
    all_exports = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, ast.List):
                        all_exports = [elt.value for elt in node.value.elts if isinstance(elt, ast.Constant)]
    
    assert all_exports is not None, "__all__ should be defined"
    assert "MetaDatRegistry" in all_exports, "MetaDatRegistry should be exported"
    assert "MetaRayBanProvider" in all_exports, "MetaRayBanProvider should be exported"
    
    print("✓ All export checks passed")


def test_documentation():
    """Verify documentation is present."""
    meta_py_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "drivers", "providers", "meta.py"
    )
    
    with open(meta_py_path, 'r') as f:
        content = f.read()
    
    # Check for DAT-related documentation
    assert "Meta Wearables Device Access Toolkit" in content or "Meta DAT" in content, \
        "Should mention Meta DAT in documentation"
    assert "docs/meta_dat_integration.md" in content, \
        "Should reference meta_dat_integration.md"
    assert "HTTP ingestion" in content or "HTTP handler" in content, \
        "Should mention HTTP handlers"
    assert "thread-safe" in content.lower() or "Thread Safety" in content, \
        "Should document thread safety"
    
    print("✓ All documentation checks passed")


if __name__ == "__main__":
    print("Running validation tests...")
    test_module_structure()
    test_module_imports()
    test_documentation()
    print("\n✓ All validation tests passed!")
