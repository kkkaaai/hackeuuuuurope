"""Tier selector for Docker images.

Selects the optimal Docker tier based on required packages,
returning the tier name and any packages that need runtime installation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TierSelection:
    """Result of tier selection."""
    tier_name: str
    tier_image: str
    tier_packages: set[str]
    missing_packages: list[str]
    description: str


class TierSelector:
    """Selects optimal Docker tier based on package requirements.
    
    Loads tier definitions from tiers.yaml and finds the smallest tier
    that contains as many required packages as possible, returning
    any missing packages for runtime installation.
    """
    
    def __init__(self, config_path: str | Path | None = None):
        """Initialize with tier configuration.
        
        Args:
            config_path: Path to tiers.yaml. Defaults to docker/tiers.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent / "docker" / "tiers.yaml"
        
        self.config_path = Path(config_path)
        self._load_config()
    
    def _load_config(self) -> None:
        """Load tier configuration from YAML."""
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        
        self.registry = self.config.get("registry", "block-sandbox")
        self.aliases = self.config.get("aliases", {})
        self.blacklist = set(self.config.get("blacklist", []))
        
        self.tiers: dict[str, dict[str, Any]] = {}
        self.tier_order: list[str] = []
        self.cumulative_packages: dict[str, set[str]] = {}
        
        self._build_tier_index()
    
    def _build_tier_index(self) -> None:
        """Build cumulative package sets for each tier."""
        tiers_config = self.config.get("tiers", {})
        
        for tier_name, tier_def in tiers_config.items():
            self.tiers[tier_name] = tier_def
            self.tier_order.append(tier_name)
        
        cumulative = set()
        for tier_name in self.tier_order:
            tier_def = self.tiers[tier_name]
            packages = set(tier_def.get("packages", []))
            cumulative = cumulative | packages
            self.cumulative_packages[tier_name] = cumulative.copy()
    
    def _normalize_package(self, package: str) -> str:
        """Normalize package name using aliases."""
        package = package.lower().strip()
        return self.aliases.get(package, package)
    
    def _filter_blacklisted(self, packages: list[str]) -> list[str]:
        """Remove blacklisted packages."""
        return [p for p in packages if p not in self.blacklist]
    
    def select_tier(self, required_packages: list[str]) -> TierSelection:
        """Select optimal tier for the given packages.
        
        Finds the smallest tier that maximizes coverage of required packages.
        Returns the tier info and any packages not included.
        
        Args:
            required_packages: List of package names required by the agent
            
        Returns:
            TierSelection with tier info and missing packages
        """
        if not required_packages:
            tier_name = self.tier_order[0]
            return TierSelection(
                tier_name=tier_name,
                tier_image=f"{self.registry}-{tier_name}:latest",
                tier_packages=self.cumulative_packages[tier_name],
                missing_packages=[],
                description=self.tiers[tier_name].get("description", ""),
            )
        
        normalized = [self._normalize_package(p) for p in required_packages]
        filtered = self._filter_blacklisted(normalized)
        required_set = set(filtered)
        
        best_tier = None
        best_coverage = -1
        best_missing = None
        
        for tier_name in self.tier_order:
            tier_packages = self.cumulative_packages[tier_name]
            covered = required_set & tier_packages
            missing = required_set - tier_packages
            coverage = len(covered)
            
            if coverage > best_coverage:
                best_tier = tier_name
                best_coverage = coverage
                best_missing = list(missing)
            elif coverage == best_coverage and best_tier is not None:
                pass
            
            if len(missing) == 0:
                best_tier = tier_name
                best_missing = []
                break
        
        if best_tier is None:
            best_tier = self.tier_order[0]
            best_missing = list(required_set)
        
        return TierSelection(
            tier_name=best_tier,
            tier_image=f"{self.registry}-{best_tier}:latest",
            tier_packages=self.cumulative_packages[best_tier],
            missing_packages=best_missing or [],
            description=self.tiers[best_tier].get("description", ""),
        )
    
    def get_tier_info(self, tier_name: str) -> dict[str, Any]:
        """Get information about a specific tier."""
        if tier_name not in self.tiers:
            raise ValueError(f"Unknown tier: {tier_name}")
        
        return {
            "name": tier_name,
            "image": f"{self.registry}-{tier_name}:latest",
            "packages": list(self.cumulative_packages[tier_name]),
            "description": self.tiers[tier_name].get("description", ""),
        }
    
    def list_tiers(self) -> list[dict[str, Any]]:
        """List all available tiers with their packages."""
        return [self.get_tier_info(name) for name in self.tier_order]


def select_tier_for_packages(packages: list[str]) -> TierSelection:
    """Convenience function to select tier for a list of packages."""
    selector = TierSelector()
    return selector.select_tier(packages)


if __name__ == "__main__":
    selector = TierSelector()
    
    print("Available tiers:")
    for tier in selector.list_tiers():
        print(f"  {tier['name']}: {tier['description']}")
        print(f"    Packages: {', '.join(tier['packages']) or '(none)'}")
        print()
    
    test_cases = [
        [],
        ["requests"],
        ["pandas", "numpy"],
        ["scipy", "sklearn"],
        ["requests", "some-unknown-package"],
        ["torch", "transformers"],
    ]
    
    print("Test selections:")
    for packages in test_cases:
        result = selector.select_tier(packages)
        print(f"  {packages}")
        print(f"    -> Tier: {result.tier_name}")
        print(f"    -> Missing: {result.missing_packages}")
        print()
