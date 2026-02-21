#!/usr/bin/env python3
"""Build script for tiered Docker images.

Builds all tier images in order, with each tier extending the previous.
Can be run locally or in CI/CD pipelines.

Usage:
    python build_tiers.py                  # Build all tiers
    python build_tiers.py --tier tier1     # Build specific tier (and dependencies)
    python build_tiers.py --push           # Build and push to registry
    python build_tiers.py --no-cache       # Build without cache
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


def load_config(config_path: Path) -> dict:
    """Load tier configuration from YAML."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_tier_order(config: dict) -> list[str]:
    """Get tiers in build order (dependencies first)."""
    return list(config.get("tiers", {}).keys())


def build_tier(
    tier_name: str,
    dockerfile_dir: Path,
    registry: str,
    no_cache: bool = False,
    push: bool = False,
) -> bool:
    """Build a single tier image.
    
    Args:
        tier_name: Name of the tier (e.g., 'tier0')
        dockerfile_dir: Path to directory containing Dockerfiles
        registry: Registry prefix for image tags
        no_cache: Whether to build without Docker cache
        push: Whether to push to registry after building
        
    Returns:
        True if build succeeded, False otherwise
    """
    dockerfile = dockerfile_dir / f"{tier_name}.Dockerfile"
    if not dockerfile.exists():
        print(f"ERROR: Dockerfile not found: {dockerfile}")
        return False
    
    image_tag = f"{registry}-{tier_name}:latest"
    
    cmd = [
        "docker", "build",
        "-f", str(dockerfile),
        "-t", image_tag,
        "--build-arg", f"REGISTRY={registry}",
    ]
    
    if no_cache:
        cmd.append("--no-cache")
    
    cmd.append(str(dockerfile_dir))
    
    print(f"\n{'='*60}")
    print(f"Building {tier_name} -> {image_tag}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✓ Successfully built {image_tag}")
        
        if push:
            push_cmd = ["docker", "push", image_tag]
            print(f"Pushing {image_tag}...")
            subprocess.run(push_cmd, check=True)
            print(f"✓ Successfully pushed {image_tag}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Failed to build {tier_name}: {e}")
        return False


def get_tiers_to_build(target_tier: str | None, tier_order: list[str]) -> list[str]:
    """Get list of tiers that need to be built.
    
    If target_tier is specified, includes all tiers up to and including it.
    Otherwise returns all tiers.
    """
    if target_tier is None:
        return tier_order
    
    if target_tier not in tier_order:
        raise ValueError(f"Unknown tier: {target_tier}. Available: {tier_order}")
    
    idx = tier_order.index(target_tier)
    return tier_order[:idx + 1]


def main():
    parser = argparse.ArgumentParser(description="Build tiered Docker images")
    parser.add_argument(
        "--tier",
        type=str,
        default=None,
        help="Build specific tier (and its dependencies)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Build without Docker cache",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push images to registry after building",
    )
    parser.add_argument(
        "--registry",
        type=str,
        default=None,
        help="Override registry prefix from config",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to tiers.yaml config file",
    )
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    config_path = Path(args.config) if args.config else script_dir / "tiers.yaml"
    
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)
    
    config = load_config(config_path)
    registry = args.registry or config.get("registry", "block-sandbox")
    tier_order = get_tier_order(config)
    
    try:
        tiers_to_build = get_tiers_to_build(args.tier, tier_order)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    
    print(f"Docker Tier Builder")
    print(f"Registry: {registry}")
    print(f"Tiers to build: {', '.join(tiers_to_build)}")
    
    success_count = 0
    failed_tiers = []
    
    for tier_name in tiers_to_build:
        success = build_tier(
            tier_name=tier_name,
            dockerfile_dir=script_dir,
            registry=registry,
            no_cache=args.no_cache,
            push=args.push,
        )
        
        if success:
            success_count += 1
        else:
            failed_tiers.append(tier_name)
            print(f"\nStopping build - {tier_name} failed and is required by later tiers")
            break
    
    print(f"\n{'='*60}")
    print(f"Build Summary")
    print(f"{'='*60}")
    print(f"Successful: {success_count}/{len(tiers_to_build)}")
    
    if failed_tiers:
        print(f"Failed: {', '.join(failed_tiers)}")
        sys.exit(1)
    else:
        print("All tiers built successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
