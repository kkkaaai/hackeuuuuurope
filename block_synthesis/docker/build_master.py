#!/usr/bin/env python3
"""Build master Docker image with all packages from the codebase.

This script:
1. Scans the codebase for all Python imports used in blocks
2. Maps imports to pip package names
3. Builds a Docker image with all discovered packages

Usage:
    python build_master.py                    # Build master image
    python build_master.py --scan-only        # Just list discovered packages
    python build_master.py --no-cache         # Build without Docker cache
    python build_master.py --push             # Build and push to registry
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path


# Mapping from import names to pip package names
IMPORT_TO_PACKAGE = {
    # Standard library (skip these)
    "os": None,
    "sys": None,
    "json": None,
    "re": None,
    "uuid": None,
    "logging": None,
    "datetime": None,
    "pathlib": None,
    "typing": None,
    "io": None,
    "traceback": None,
    "operator": None,
    "socket": None,
    "ipaddress": None,
    "urllib": None,
    "base64": None,
    "shutil": None,
    "subprocess": None,
    "tempfile": None,
    "collections": None,
    "itertools": None,
    "functools": None,
    "statistics": None,
    "random": None,
    "hashlib": None,
    "math": None,
    "__future__": None,
    "abc": None,
    "asyncio": None,
    "argparse": None,
    "ast": None,
    "dataclasses": None,
    "enum": None,
    "glob": None,
    "importlib": None,
    "tarfile": None,
    "time": None,
    "resource": None,
    
    # Third-party mappings
    "httpx": "httpx",
    "requests": "requests",
    "aiohttp": "aiohttp",
    "bs4": "beautifulsoup4",
    "BeautifulSoup": "beautifulsoup4",
    "lxml": "lxml",
    "numpy": "numpy",
    "np": "numpy",
    "pandas": "pandas",
    "pd": "pandas",
    "PIL": "pillow",
    "pillow": "pillow",
    "openpyxl": "openpyxl",
    "xlrd": "xlrd",
    "scipy": "scipy",
    "sklearn": "scikit-learn",
    "cv2": "opencv-python-headless",
    "opencv": "opencv-python-headless",
    "matplotlib": "matplotlib",
    "seaborn": "seaborn",
    "statsmodels": "statsmodels",
    "anthropic": "anthropic",
    "openai": "openai",
    "google": "google-generativeai",
    "genai": "google-generativeai",
    "stripe": "stripe",
    "sendgrid": "sendgrid",
    "elevenlabs": "elevenlabs",
    "yaml": "pyyaml",
    "pyyaml": "pyyaml",
    "dotenv": "python-dotenv",
    "jsonschema": "jsonschema",
    "pydantic": "pydantic",
    "pydantic_settings": "pydantic-settings",
    "docker": "docker",
}

# Core packages to always include (even if not discovered by scanning)
CORE_PACKAGES = {
    "httpx",
    "requests",
    "aiohttp",
    "beautifulsoup4",
    "lxml",
    "numpy",
    "pandas",
    "pillow",
    "pyyaml",
    "python-dotenv",
    "jsonschema",
    "pydantic",
}


def extract_imports_from_file(filepath: Path) -> set[str]:
    """Extract all import names from a Python file."""
    imports = set()
    
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
    except (SyntaxError, UnicodeDecodeError):
        pass
    
    return imports


def scan_directory_for_imports(root: Path, patterns: list[str]) -> set[str]:
    """Scan directories matching patterns for all imports."""
    all_imports = set()
    
    for pattern in patterns:
        for filepath in root.glob(pattern):
            if filepath.is_file() and filepath.suffix == ".py":
                imports = extract_imports_from_file(filepath)
                all_imports.update(imports)
    
    return all_imports


def map_imports_to_packages(imports: set[str]) -> set[str]:
    """Map import names to pip package names."""
    packages = set()
    
    for imp in imports:
        if imp in IMPORT_TO_PACKAGE:
            pkg = IMPORT_TO_PACKAGE[imp]
            if pkg is not None:
                packages.add(pkg)
        else:
            packages.add(imp)
    
    return packages


def discover_packages(project_root: Path) -> set[str]:
    """Discover all packages used in blocks across the codebase."""
    patterns = [
        "Demo/backend/blocks/**/*.py",
        "Kai/app/blocks/**/*.py",
        "Alex/**/*.py",
        "block_synthesis/**/*.py",
    ]
    
    imports = scan_directory_for_imports(project_root, patterns)
    packages = map_imports_to_packages(imports)
    packages.update(CORE_PACKAGES)
    
    # Filter out internal project modules
    internal_patterns = {
        "app", "engine", "storage", "llm", "api", "registry",
        "config", "settings", "database", "memory", "blocks",
        # Project-specific modules
        "block_synthesis", "block_retriever", "block_executor",
        "flow_creator", "flow_executor", "prompt_injector",
        "model_tiers", "task_id_manager", "tier_selector",
        "synthesizer", "run_synthesis", "io_decomposition",
        "clean_dd_requests",
    }
    packages = {p for p in packages if p not in internal_patterns}
    
    return packages


def generate_dockerfile(packages: set[str], output_path: Path) -> None:
    """Generate a Dockerfile with all discovered packages."""
    packages_sorted = sorted(packages)
    
    dockerfile_content = '''# Auto-generated Master Docker Image
# Contains ALL packages discovered from block implementations
# Generated by build_master.py

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    libgl1-mesa-glx \\
    libglib2.0-0 \\
    libffi-dev \\
    libssl-dev \\
    && rm -rf /var/lib/apt/lists/*

# Create sandbox user
RUN useradd -m -s /bin/bash sandbox && \\
    mkdir -p /output /tmp /app && \\
    chown sandbox:sandbox /output /tmp /app && \\
    chmod 1777 /output /tmp

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install all discovered packages
RUN pip install --no-cache-dir \\
'''
    
    for pkg in packages_sorted:
        dockerfile_content += f"    {pkg} \\\n"
    
    dockerfile_content = dockerfile_content.rstrip(" \\\n") + "\n"
    
    dockerfile_content += '''
WORKDIR /app
USER sandbox
CMD ["sleep", "infinity"]
'''
    
    output_path.write_text(dockerfile_content, encoding="utf-8")
    print(f"Generated Dockerfile: {output_path}")


def build_image(
    dockerfile_dir: Path,
    image_name: str = "block-sandbox-master",
    no_cache: bool = False,
    push: bool = False,
) -> bool:
    """Build the Docker image."""
    dockerfile = dockerfile_dir / "master.Dockerfile"
    
    cmd = [
        "docker", "build",
        "-f", str(dockerfile),
        "-t", f"{image_name}:latest",
    ]
    
    if no_cache:
        cmd.append("--no-cache")
    
    cmd.append(str(dockerfile_dir))
    
    print(f"\n{'='*60}")
    print(f"Building {image_name}:latest")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✓ Successfully built {image_name}:latest")
        
        if push:
            push_cmd = ["docker", "push", f"{image_name}:latest"]
            print(f"Pushing {image_name}:latest...")
            subprocess.run(push_cmd, check=True)
            print(f"✓ Successfully pushed {image_name}:latest")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Build master Docker image")
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Only scan and list packages, don't build",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate Dockerfile from discovered packages",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Build without Docker cache",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push image to registry after building",
    )
    parser.add_argument(
        "--image-name",
        type=str,
        default="block-sandbox-master",
        help="Name for the Docker image",
    )
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    print("Scanning codebase for packages...")
    packages = discover_packages(project_root)
    
    print(f"\nDiscovered {len(packages)} packages:")
    for pkg in sorted(packages):
        print(f"  - {pkg}")
    
    if args.scan_only:
        return
    
    if args.regenerate:
        generate_dockerfile(packages, script_dir / "master.Dockerfile")
    
    success = build_image(
        dockerfile_dir=script_dir,
        image_name=args.image_name,
        no_cache=args.no_cache,
        push=args.push,
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
