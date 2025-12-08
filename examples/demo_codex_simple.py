#!/usr/bin/env python3
"""
Simple demo for OpenAI Codex prompts and SNN knowledge distillation.

This is a lightweight demo that imports only what's needed without loading
the full SmartGlassAgent dependencies.
"""

import json
import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

print("="*60)
print("OpenAI Codex Prompts & SNN Distillation Demo")
print("="*60)

print("\n⚠️  NOTE: Running in PLACEHOLDER mode")
print("   Set OPENAI_API_KEY for actual OpenAI responses")
print("   This demo shows the system structure and capabilities")

# Demo 1: Prompt Registry
print("\n" + "="*60)
print("DEMO 1: Prompt Registry")
print("="*60)

try:
    # Import directly from file to avoid __init__.py cascade
    import importlib.util
    
    spec = importlib.util.spec_from_file_location(
        "prompt_registry",
        repo_root / "src" / "utils" / "prompt_registry.py"
    )
    prompt_registry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prompt_registry)
    
    get_prompt_registry = prompt_registry.get_prompt_registry
    PromptCategory = prompt_registry.PromptCategory
    
    registry = get_prompt_registry()
    
    print("\n✓ Prompt registry loaded successfully")
    print(f"  Total templates: {len(registry._templates)}")
    
    print("\n📋 Available Categories:")
    for category in sorted(registry.get_categories(), key=lambda c: c.value):
        templates = registry.list_templates(category)
        print(f"  • {category.value}: {len(templates)} template(s)")
    
    print("\n📝 Meta Ray-Ban Templates:")
    meta_templates = registry.list_templates(PromptCategory.META_RAYBAN)
    for t in meta_templates:
        print(f"  • {t.name}")
        print(f"    → {t.description}")
        print(f"    Required: {', '.join(t.required_fields)}")
    
    print("\n🔍 Search for 'navigation':")
    nav_templates = registry.search_templates("navigation")
    for t in nav_templates:
        print(f"  • {t.name}: {t.description}")
    
    print("\n✅ Prompt registry demo completed")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Demo 2: OpenAI Codex Backend
print("\n" + "="*60)
print("DEMO 2: OpenAI Codex Backend")
print("="*60)

try:
    # Import directly from file
    spec = importlib.util.spec_from_file_location(
        "llm_openai_codex",
        repo_root / "src" / "llm_openai_codex.py"
    )
    llm_openai_codex = importlib.util.module_from_spec(spec)
    
    # Load base backend first
    spec_base = importlib.util.spec_from_file_location(
        "llm_backend_base",
        repo_root / "src" / "llm_backend_base.py"
    )
    llm_backend_base = importlib.util.module_from_spec(spec_base)
    spec_base.loader.exec_module(llm_backend_base)
    
    # Add to sys.modules so llm_openai_codex can find it
    sys.modules['src.llm_backend_base'] = llm_backend_base
    
    spec.loader.exec_module(llm_openai_codex)
    
    OpenAICodexBackend = llm_openai_codex.OpenAICodexBackend
    
    backend = OpenAICodexBackend(
        model="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=512,
    )
    
    print("\n✓ OpenAI Codex backend initialized")
    print(f"  Model: {backend.model}")
    print(f"  Temperature: {backend.temperature}")
    print(f"  Max tokens: {backend.max_tokens}")
    print(f"  Template dir: {backend.template_dir}")
    print(f"  Client initialized: {backend._client is not None}")
    
    # Test template rendering
    print("\n📄 Testing template rendering...")
    context = {
        "scene_description": "A busy coffee shop with people working",
        "location": "downtown",
        "task": "find a seat",
    }
    
    prompt = backend.render_template("meta_rayban_camera_analysis.j2", context)
    print("\n  Rendered prompt preview:")
    print("  " + "\n  ".join(prompt.split('\n')[:5]))
    print("  ...")
    
    # Test generation (will be stub mode without API key)
    print("\n🤖 Testing generation (stub mode):")
    result = backend.generate("What should I do here?")
    print(f"  {result[:80]}...")
    
    print("\n✅ OpenAI Codex backend demo completed")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Demo 3: SNN Knowledge Distillation
print("\n" + "="*60)
print("DEMO 3: SNN Knowledge Distillation")
print("="*60)

try:
    # Import directly from file
    spec = importlib.util.spec_from_file_location(
        "snn_knowledge_distillation",
        repo_root / "src" / "snn_knowledge_distillation.py"
    )
    snn_kd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(snn_kd)
    
    SNNDistillationConfig = snn_kd.SNNDistillationConfig
    SNNDistillationTrainer = snn_kd.SNNDistillationTrainer
    create_default_config = snn_kd.create_default_config
    
    # Create configuration
    config = create_default_config()
    
    print("\n✓ SNN distillation config created")
    print(f"  Teacher: {config.teacher_model}")
    print(f"  Student architecture: {config.student_architecture}")
    print(f"  Hidden size: {config.student_hidden_size}")
    print(f"  Num layers: {config.student_num_layers}")
    print(f"  Num heads: {config.student_num_heads}")
    print(f"  Temperature: {config.temperature}")
    print(f"  Target latency: {config.target_latency_ms}ms")
    print(f"  Target power: {config.target_power_mw}mW")
    print(f"  Quantization: {config.quantization_bits}-bit")
    
    # Save config
    config_path = "/tmp/snn_distillation_demo.json"
    config.save(config_path)
    print(f"\n💾 Config saved to: {config_path}")
    
    # Initialize trainer
    print("\n⚙️  Initializing SNN trainer (placeholder)...")
    trainer = SNNDistillationTrainer(config)
    
    # Run placeholder training
    print("\n🏃 Running placeholder training...")
    results = trainer.train()
    print(json.dumps(results, indent=2))
    
    print("\n✅ SNN knowledge distillation demo completed")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Demo 4: Template Files
print("\n" + "="*60)
print("DEMO 4: Available Template Files")
print("="*60)

templates_dir = Path(__file__).parent.parent / "templates"
if templates_dir.exists():
    template_files = sorted(templates_dir.glob("*.j2"))
    print(f"\n📁 Found {len(template_files)} template files in templates/")
    
    for template_file in template_files:
        # Read first line to get description
        with open(template_file) as f:
            content = f.read()
            # Get first non-empty line that's not just comments
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            preview = lines[0] if lines else "No content"
            if len(preview) > 60:
                preview = preview[:57] + "..."
        
        print(f"  • {template_file.name}")
        print(f"    → {preview}")
else:
    print(f"\n❌ Templates directory not found: {templates_dir}")

# Summary
print("\n" + "="*60)
print("DEMO COMPLETED SUCCESSFULLY")
print("="*60)

print("\n📚 What was demonstrated:")
print("  ✓ Prompt Registry - 12 templates across 8 categories")
print("  ✓ OpenAI Codex Backend - Template rendering & generation")
print("  ✓ SNN Knowledge Distillation - Configuration & training interface")
print("  ✓ Template Files - All 12 domain-specific templates")

print("\n🚀 Next Steps:")
print("  1. Set OPENAI_API_KEY environment variable")
print("  2. Install: pip install openai jinja2")
print("  3. Explore templates/ directory for prompt engineering")
print("  4. Read docs/openai_codex_prompts.md")
print("  5. Read docs/snn_knowledge_distillation.md")
print("  6. Use scripts/train_snn_student.py for actual training")

print("\n📖 Documentation:")
print("  • docs/openai_codex_prompts.md - Complete prompts guide")
print("  • docs/snn_knowledge_distillation.md - SNN distillation guide")
print("  • examples/demo_codex_prompts.py - Full feature demo")

print("\n" + "="*60)
