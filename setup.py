"""
Setup configuration for SmartGlass AI Agent
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="smartglass-ai-agent",
    version="0.1.0",
    author="SmartGlass AI Team",
    description="A multimodal AI assistant for smart glasses using Whisper, CLIP, and GPT-2",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/farmountain/SmartGlass-AI-Agent",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    keywords="smart-glasses ai multimodal whisper clip gpt2 meta-rayban",
    project_urls={
        "Bug Reports": "https://github.com/farmountain/SmartGlass-AI-Agent/issues",
        "Source": "https://github.com/farmountain/SmartGlass-AI-Agent",
    },
)
