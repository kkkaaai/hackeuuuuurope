"""Autonomous Block Synthesis System.

Production-grade system for generating, testing, and iteratively repairing
Python blocks using LLM and sandboxed execution.

Supports two execution backends:
1. Docker (strongest isolation, requires Docker runtime)
2. Subprocess (simpler deployment, uses resource limits + restricted builtins)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Any

RESOURCE_AVAILABLE = False
try:
    import resource
    RESOURCE_AVAILABLE = True
except ImportError:
    pass

DOCKER_AVAILABLE = False
try:
    import docker
    from docker.errors import ContainerError, DockerException, ImageNotFound
    from docker.models.containers import Container
    DOCKER_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class SandboxError(Exception):
    """Raised when container creation or execution fails."""
    pass


class SynthesisError(Exception):
    """Raised when LLM generation fails."""
    pass


class ValidationError(Exception):
    """Raised when output comparison fails unexpectedly."""
    pass


class MaxIterationsError(Exception):
    """Raised when maximum repair iterations exceeded."""
    pass


# =============================================================================
# Enums and Data Classes
# =============================================================================


class OutputFormat(str, Enum):
    """Supported output formats for block execution."""
    JSON = "json"
    TEXT = "text"
    FILE = "file"
    QUERY = "query"


@dataclass
class BlockRequest:
    """Request to synthesize a block."""
    inputs: list[str]
    outputs: list[str]
    purpose: str
    test_input: Any
    expected_output: Any


@dataclass
class SynthesisResult:
    """Result from LLM block generation."""
    code: str
    output_format: OutputFormat
    output_path: str | None = None
    required_packages: list[str] | None = None


@dataclass
class ExecutionResult:
    """Result from executing code in sandbox."""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    output_file_content: str | None = None
    error: str | None = None


# =============================================================================
# Sandbox Base Class
# =============================================================================


class BaseSandbox(ABC):
    """Abstract base class for sandbox implementations."""
    
    @abstractmethod
    def start(self) -> str:
        """Initialize the sandbox. Returns an identifier."""
        pass
    
    @abstractmethod
    def execute(self, code: str, input_data: Any, timeout: int = 5) -> ExecutionResult:
        """Execute code in the sandbox."""
        pass
    
    @abstractmethod
    def extract_file(self, path: str) -> str | None:
        """Extract file content from sandbox."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up sandbox resources."""
        pass


# =============================================================================
# SubprocessSandbox (No Docker required)
# =============================================================================


class SubprocessSandbox(BaseSandbox):
    """Subprocess-based sandbox for simpler deployment.
    
    Security measures:
    - Restricted builtins (no open, exec, eval, import manipulation)
    - Memory limit via resource.setrlimit (Linux only)
    - CPU time limit
    - Timeout enforcement
    - Temporary directory isolation
    
    Note: On Windows, resource limits are not enforced.
    """
    
    def __init__(self, memory_limit_mb: int = 512, cpu_time_limit: int = 5):
        self.memory_limit_mb = memory_limit_mb
        self.cpu_time_limit = cpu_time_limit
        self.temp_dir: tempfile.TemporaryDirectory | None = None
        self.output_dir: Path | None = None
    
    def start(self) -> str:
        """Create temporary directory for execution."""
        self.temp_dir = tempfile.TemporaryDirectory(prefix="block_sandbox_")
        self.output_dir = Path(self.temp_dir.name) / "output"
        self.output_dir.mkdir(exist_ok=True)
        logger.info("Started subprocess sandbox: %s", self.temp_dir.name)
        return self.temp_dir.name
    
    def execute(self, code: str, input_data: Any, timeout: int = 5) -> ExecutionResult:
        """Execute code in a subprocess with restrictions."""
        if not self.temp_dir:
            raise SandboxError("Sandbox not started. Call start() first.")
        
        if isinstance(input_data, str):
            stdin_data = input_data
        else:
            stdin_data = json.dumps(input_data)
        
        wrapper_code = self._build_wrapper(code)
        
        script_path = Path(self.temp_dir.name) / "script.py"
        script_path.write_text(wrapper_code, encoding="utf-8")
        
        env = os.environ.copy()
        env["SANDBOX_OUTPUT_DIR"] = str(self.output_dir)
        
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.temp_dir.name,
                env=env,
            )
            
            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                error=result.stderr if result.returncode != 0 else None,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds",
                exit_code=-1,
                error=f"Timeout after {timeout}s",
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                error=str(e),
            )
    
    def _build_wrapper(self, code: str) -> str:
        """Build wrapper script with resource limits and restricted execution."""
        return f'''
import sys
import os
import json
import math
import re
import collections
import itertools
import functools
import datetime
import statistics
import random
import hashlib
import base64

# Set resource limits on Linux
try:
    import resource
    resource.setrlimit(resource.RLIMIT_AS, ({self.memory_limit_mb} * 1024 * 1024, {self.memory_limit_mb} * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, ({self.cpu_time_limit}, {self.cpu_time_limit}))
    resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))  # No subprocess spawning
except (ImportError, ValueError):
    pass  # Windows or permission issue

# Output directory for file outputs
OUTPUT_DIR = os.environ.get("SANDBOX_OUTPUT_DIR", "/output")

# Restricted builtins
ALLOWED_BUILTINS = {{
    "True": True,
    "False": False,
    "None": None,
    "abs": abs,
    "all": all,
    "any": any,
    "bin": bin,
    "bool": bool,
    "bytes": bytes,
    "chr": chr,
    "dict": dict,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "format": format,
    "frozenset": frozenset,
    "hash": hash,
    "hex": hex,
    "int": int,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "iter": iter,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "next": next,
    "oct": oct,
    "ord": ord,
    "pow": pow,
    "print": print,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    "AttributeError": AttributeError,
    "StopIteration": StopIteration,
}}

def safe_open(path, mode="r", *args, **kwargs):
    """Only allow writing to output directory."""
    path = str(path)
    if "w" in mode or "a" in mode:
        if not path.startswith(OUTPUT_DIR):
            raise PermissionError(f"Cannot write to {{path}}. Only {{OUTPUT_DIR}} is writable.")
    else:
        raise PermissionError("Reading files is not allowed")
    return open(path, mode, *args, **kwargs)

ALLOWED_BUILTINS["open"] = safe_open

namespace = {{
    "__builtins__": ALLOWED_BUILTINS,
    "json": json,
    "math": math,
    "re": re,
    "collections": collections,
    "itertools": itertools,
    "functools": functools,
    "datetime": datetime,
    "statistics": statistics,
    "random": random,
    "hashlib": hashlib,
    "base64": base64,
    "OUTPUT_DIR": OUTPUT_DIR,
}}

code = """
{code.replace('"""', "'''").replace(chr(92), chr(92)+chr(92))}
"""

exec(code, namespace)
'''
    
    def extract_file(self, path: str) -> str | None:
        """Extract file from output directory."""
        if not self.output_dir:
            raise SandboxError("Sandbox not started. Call start() first.")
        
        filename = Path(path).name
        file_path = self.output_dir / filename
        
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")
        
        for f in self.output_dir.iterdir():
            if f.is_file():
                return f.read_text(encoding="utf-8")
        
        return None
    
    def cleanup(self) -> None:
        """Remove temporary directory."""
        if self.temp_dir:
            try:
                self.temp_dir.cleanup()
                logger.info("Cleaned up subprocess sandbox")
            except Exception as e:
                logger.warning("Failed to cleanup sandbox: %s", e)
            finally:
                self.temp_dir = None
                self.output_dir = None


# =============================================================================
# DockerSandbox (Strongest isolation)
# =============================================================================


class DockerSandbox(BaseSandbox):
    """Docker-based sandbox for strongest isolation with package installation support.
    
    Two modes:
    1. Strict mode (default): No network, read-only filesystem, maximum security
    2. Permissive mode: Network enabled for pip install, writable filesystem
    
    Security constraints (strict mode):
    - Non-root user
    - Memory limit (512MB)
    - CPU quota (0.5 CPU)
    - Network disabled
    - Read-only filesystem (except /output, /tmp, /home)
    - No new privileges
    
    Requires Docker runtime to be installed and running.
    """
    
    def __init__(
        self,
        image: str = "block-sandbox",
        allow_network: bool = False,
        allow_pip_install: bool = False,
        memory_limit: str = "512m",
        cpu_quota: int = 50000,
    ):
        if not DOCKER_AVAILABLE:
            raise SandboxError(
                "Docker SDK not installed. Install with: pip install docker"
            )
        self.image = image
        self.allow_network = allow_network or allow_pip_install
        self.allow_pip_install = allow_pip_install
        self.memory_limit = memory_limit
        self.cpu_quota = cpu_quota
        self.client: docker.DockerClient | None = None
        self.container: Container | None = None
        self.installed_packages: set[str] = set()
    
    def start(self) -> str:
        """Create and start a sandboxed container."""
        try:
            self.client = docker.from_env()
        except DockerException as e:
            raise SandboxError(f"Failed to connect to Docker: {e}") from e
        
        try:
            self.client.images.get(self.image)
        except ImageNotFound:
            raise SandboxError(
                f"Docker image '{self.image}' not found. "
                "Please build or pull the image first."
            )
        
        try:
            container_config = {
                "image": self.image,
                "command": ["sleep", "infinity"],
                "detach": True,
                "mem_limit": self.memory_limit,
                "cpu_quota": self.cpu_quota,
                "security_opt": ["no-new-privileges"],
                "tmpfs": {
                    "/output": "size=50m,mode=1777",
                    "/tmp": "size=50m,mode=1777",
                },
            }
            
            if self.allow_network:
                container_config["network_disabled"] = False
            else:
                container_config["network_disabled"] = True
                container_config["read_only"] = True
            
            self.container = self.client.containers.run(**container_config)
            logger.info(
                "Started Docker sandbox: %s (network=%s, pip=%s)",
                self.container.short_id,
                self.allow_network,
                self.allow_pip_install,
            )
            return self.container.id
        except (ContainerError, DockerException) as e:
            raise SandboxError(f"Failed to start container: {e}") from e
    
    def install_packages(self, packages: list[str], timeout: int = 60) -> ExecutionResult:
        """Install Python packages in the container.
        
        Args:
            packages: List of package names (e.g., ["pandas", "numpy"])
            timeout: Installation timeout in seconds
            
        Returns:
            ExecutionResult from pip install
        """
        if not self.container:
            raise SandboxError("Container not started. Call start() first.")
        
        if not self.allow_pip_install:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="Package installation not allowed. Set allow_pip_install=True.",
                exit_code=1,
                error="Package installation disabled",
            )
        
        new_packages = [p for p in packages if p not in self.installed_packages]
        if not new_packages:
            return ExecutionResult(
                success=True,
                stdout="All packages already installed",
                stderr="",
                exit_code=0,
            )
        
        packages_str = " ".join(new_packages)
        logger.info("Installing packages: %s", packages_str)
        
        try:
            exit_code, output = self.container.exec_run(
                cmd=["pip", "install", "--no-cache-dir"] + new_packages,
                demux=True,
                user="root",
            )
            
            stdout = output[0].decode("utf-8") if output[0] else ""
            stderr = output[1].decode("utf-8") if output[1] else ""
            
            if exit_code == 0:
                self.installed_packages.update(new_packages)
                logger.info("Successfully installed: %s", packages_str)
            
            return ExecutionResult(
                success=exit_code == 0,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                error=stderr if exit_code != 0 else None,
            )
        except DockerException as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                error=str(e),
            )
    
    def execute(self, code: str, input_data: Any, timeout: int = 5) -> ExecutionResult:
        """Execute Python code in the container."""
        if not self.container:
            raise SandboxError("Container not started. Call start() first.")
        
        if isinstance(input_data, str):
            stdin_data = input_data
        else:
            stdin_data = json.dumps(input_data)
        
        script_content = f'''import sys
import io

input_data = {json.dumps(stdin_data)}
sys.stdin = io.StringIO(input_data)

{code}
'''
        
        try:
            exit_code, output = self.container.exec_run(
                cmd=["python", "-c", script_content],
                demux=True,
                workdir="/tmp",
            )
            
            stdout = output[0].decode("utf-8") if output[0] else ""
            stderr = output[1].decode("utf-8") if output[1] else ""
            
            return ExecutionResult(
                success=exit_code == 0,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                error=stderr if exit_code != 0 else None,
            )
        except DockerException as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                error=str(e),
            )
    
    def execute_shell(self, command: str, timeout: int = 30) -> ExecutionResult:
        """Execute a shell command in the container.
        
        Useful for running arbitrary commands, scripts, or tools.
        """
        if not self.container:
            raise SandboxError("Container not started. Call start() first.")
        
        try:
            exit_code, output = self.container.exec_run(
                cmd=["sh", "-c", command],
                demux=True,
                workdir="/tmp",
            )
            
            stdout = output[0].decode("utf-8") if output[0] else ""
            stderr = output[1].decode("utf-8") if output[1] else ""
            
            return ExecutionResult(
                success=exit_code == 0,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                error=stderr if exit_code != 0 else None,
            )
        except DockerException as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                error=str(e),
            )
    
    def extract_file(self, path: str) -> str | None:
        """Extract file content from container."""
        if not self.container:
            raise SandboxError("Container not started. Call start() first.")
        
        try:
            bits, _ = self.container.get_archive(path)
            
            tar_stream = BytesIO()
            for chunk in bits:
                tar_stream.write(chunk)
            tar_stream.seek(0)
            
            with tarfile.open(fileobj=tar_stream) as tar:
                for member in tar.getmembers():
                    if member.isfile():
                        f = tar.extractfile(member)
                        if f:
                            return f.read().decode("utf-8")
            return None
        except Exception as e:
            logger.warning("Failed to extract file %s: %s", path, e)
            return None
    
    def cleanup(self) -> None:
        """Remove the container."""
        if self.container:
            try:
                self.container.remove(force=True)
                logger.info("Removed Docker sandbox: %s", self.container.short_id)
            except DockerException as e:
                logger.warning("Failed to remove container: %s", e)
            finally:
                self.container = None
                self.installed_packages.clear()


# =============================================================================
# SandboxManager (Factory)
# =============================================================================


class SandboxManager:
    """Factory for creating the appropriate sandbox with tier selection.
    
    Automatically selects:
    - DockerSandbox if Docker is available and requested
    - SubprocessSandbox as fallback or when explicitly requested
    
    Image selection modes:
    - "master": Use the master image containing ALL packages (default, no runtime installs)
    - "tiered": Select optimal tier based on required_packages (faster builds, smaller images)
    - explicit image: Use the specified image name directly
    
    For recursive/agentic workflows that need package installation,
    use backend="docker" with allow_pip_install=True.
    """
    
    # Default master image containing all packages
    MASTER_IMAGE = "block-sandbox-master:latest"
    
    def __init__(
        self,
        backend: str = "auto",
        image: str | None = None,
        memory_limit_mb: int = 512,
        allow_network: bool = False,
        allow_pip_install: bool = False,
        required_packages: list[str] | None = None,
        use_tiers: bool = False,
    ):
        """
        Args:
            backend: "auto", "docker", or "subprocess"
            image: Docker image name. Use "master" for master image, "tiered" for
                   automatic tier selection, or a specific image name.
            memory_limit_mb: Memory limit
            allow_network: Enable network access in container (docker only)
            allow_pip_install: Allow pip install in container (docker only, implies network)
            required_packages: Packages needed by the block (used for tier selection)
            use_tiers: Whether to use tiered Docker images (default: False, uses master)
        """
        self.backend = backend
        self._explicit_image = image
        self.memory_limit_mb = memory_limit_mb
        self.allow_network = allow_network
        self.allow_pip_install = allow_pip_install
        self.required_packages = required_packages or []
        self.use_tiers = use_tiers
        self._sandbox: BaseSandbox | None = None
        self._tier_selection: Any = None
        self._missing_packages: list[str] = []
    
    def _select_tier_image(self) -> str:
        """Select optimal tier image based on required packages.
        
        Returns the image name and stores missing packages for later installation.
        """
        # Explicit "master" keyword
        if self._explicit_image == "master":
            self._missing_packages = []  # Master has everything
            return self.MASTER_IMAGE
        
        # Explicit "tiered" keyword - use tier selection
        if self._explicit_image == "tiered":
            return self._select_from_tiers()
        
        # Explicit image name provided
        if self._explicit_image:
            self._missing_packages = self.required_packages
            return self._explicit_image
        
        # Default: use master image (has all packages, no runtime installs needed)
        if not self.use_tiers:
            self._missing_packages = []  # Master has everything
            return self.MASTER_IMAGE
        
        # Tiered mode: select optimal tier
        return self._select_from_tiers()
    
    def _select_from_tiers(self) -> str:
        """Select from tiered images based on required packages."""
        if not self.required_packages:
            self._missing_packages = []
            return "block-sandbox-tier0:latest"
        
        try:
            from .tier_selector import TierSelector
            selector = TierSelector()
            selection = selector.select_tier(self.required_packages)
            self._tier_selection = selection
            self._missing_packages = selection.missing_packages
            logger.info(
                "Selected tier: %s (%s). Missing packages: %s",
                selection.tier_name,
                selection.description,
                selection.missing_packages or "(none)",
            )
            return selection.tier_image
        except ImportError:
            logger.warning("TierSelector not available, using master image")
            self._missing_packages = []
            return self.MASTER_IMAGE
        except Exception as e:
            logger.warning("Tier selection failed (%s), using master image", e)
            self._missing_packages = []
            return self.MASTER_IMAGE
    
    @property
    def missing_packages(self) -> list[str]:
        """Packages that need to be installed at runtime."""
        return self._missing_packages
    
    @property
    def tier_info(self) -> dict | None:
        """Information about the selected tier, if available."""
        if self._tier_selection:
            return {
                "name": self._tier_selection.tier_name,
                "image": self._tier_selection.tier_image,
                "description": self._tier_selection.description,
                "packages": list(self._tier_selection.tier_packages),
                "missing": self._tier_selection.missing_packages,
            }
        return None
    
    def _create_sandbox(self) -> BaseSandbox:
        """Create the appropriate sandbox based on backend setting."""
        if self.backend == "subprocess":
            if self.allow_pip_install:
                logger.warning("allow_pip_install requires Docker backend, ignoring")
            return SubprocessSandbox(memory_limit_mb=self.memory_limit_mb)
        
        image = self._select_tier_image()
        
        if self.backend == "docker":
            return DockerSandbox(
                image=image,
                allow_network=self.allow_network,
                allow_pip_install=self.allow_pip_install,
                memory_limit=f"{self.memory_limit_mb}m",
            )
        
        if DOCKER_AVAILABLE:
            try:
                client = docker.from_env()
                client.ping()
                logger.info("Docker available, using DockerSandbox with image: %s", image)
                return DockerSandbox(
                    image=image,
                    allow_network=self.allow_network,
                    allow_pip_install=self.allow_pip_install,
                    memory_limit=f"{self.memory_limit_mb}m",
                )
            except Exception as e:
                logger.info("Docker not available (%s), using SubprocessSandbox", e)
        
        if self.allow_pip_install:
            raise SandboxError(
                "allow_pip_install requires Docker, but Docker is not available"
            )
        
        return SubprocessSandbox(memory_limit_mb=self.memory_limit_mb)
    
    def start(self) -> str:
        """Start the sandbox."""
        self._sandbox = self._create_sandbox()
        return self._sandbox.start()
    
    def execute(self, code: str, input_data: Any, timeout: int = 5) -> ExecutionResult:
        """Execute code in the sandbox."""
        if not self._sandbox:
            raise SandboxError("Sandbox not started. Call start() first.")
        return self._sandbox.execute(code, input_data, timeout)
    
    def install_packages(self, packages: list[str], timeout: int = 60) -> ExecutionResult:
        """Install Python packages in the sandbox (Docker only)."""
        if not self._sandbox:
            raise SandboxError("Sandbox not started. Call start() first.")
        if not isinstance(self._sandbox, DockerSandbox):
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="Package installation only supported with Docker backend",
                exit_code=1,
                error="Docker required for pip install",
            )
        return self._sandbox.install_packages(packages, timeout)
    
    def execute_shell(self, command: str, timeout: int = 30) -> ExecutionResult:
        """Execute a shell command in the sandbox (Docker only)."""
        if not self._sandbox:
            raise SandboxError("Sandbox not started. Call start() first.")
        if not isinstance(self._sandbox, DockerSandbox):
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="Shell execution only supported with Docker backend",
                exit_code=1,
                error="Docker required for shell commands",
            )
        return self._sandbox.execute_shell(command, timeout)
    
    def extract_file(self, path: str) -> str | None:
        """Extract file from sandbox."""
        if not self._sandbox:
            raise SandboxError("Sandbox not started. Call start() first.")
        return self._sandbox.extract_file(path)
    
    def cleanup(self) -> None:
        """Clean up sandbox."""
        if self._sandbox:
            self._sandbox.cleanup()
            self._sandbox = None


# =============================================================================
# BlockSynthesizer
# =============================================================================


class BlockSynthesizer:
    """Generates and repairs Python blocks using LLM.
    
    Loads master prompt from file for easy configuration and testing.
    """
    
    def __init__(
        self,
        prompt_file: str | Path = "block_synthesis/prompts/master_prompt.txt",
        provider: str = "openai",
        model: str = "gpt-4o",
    ):
        prompt_path = Path(prompt_file)
        if not prompt_path.exists():
            raise FileNotFoundError(f"Master prompt file not found: {prompt_file}")
        
        self.system_prompt = prompt_path.read_text(encoding="utf-8")
        self.provider = provider
        self.model = model
    
    async def generate_initial_block(self, request: BlockRequest) -> SynthesisResult:
        """Generate initial block code using LLM.
        
        Args:
            request: Block requirements including test case
            
        Returns:
            SynthesisResult with code and output format
            
        Raises:
            SynthesisError: If LLM call or parsing fails
        """
        user_prompt = self._build_task_prompt(request)
        
        try:
            response = await self._call_llm(self.system_prompt, user_prompt)
            return self._parse_synthesis_response(response)
        except Exception as e:
            raise SynthesisError(f"Failed to generate initial block: {e}") from e
    
    async def repair_block(
        self,
        request: BlockRequest,
        previous: SynthesisResult,
        result: ExecutionResult,
    ) -> SynthesisResult:
        """Repair a failed block using LLM.
        
        Args:
            request: Original block requirements
            previous: Previous synthesis attempt
            result: Execution result showing the failure
            
        Returns:
            SynthesisResult with corrected code
            
        Raises:
            SynthesisError: If repair fails
        """
        repair_prompt = self._build_repair_prompt(request, previous, result)
        
        try:
            response = await self._call_llm(self.system_prompt, repair_prompt)
            return self._parse_synthesis_response(response)
        except Exception as e:
            raise SynthesisError(f"Failed to repair block: {e}") from e
    
    def _build_task_prompt(self, request: BlockRequest) -> str:
        """Build user prompt for initial generation."""
        return f"""Generate a Python block with the following specification:

## Inputs
{json.dumps(request.inputs, indent=2)}

## Outputs
{json.dumps(request.outputs, indent=2)}

## Purpose
{request.purpose}

## Test Case
Input:
{json.dumps(request.test_input, indent=2)}

Expected Output:
{json.dumps(request.expected_output, indent=2)}

Generate the block that transforms the test input into the expected output."""
    
    def _build_repair_prompt(
        self,
        request: BlockRequest,
        previous: SynthesisResult,
        result: ExecutionResult,
    ) -> str:
        """Build user prompt for repair."""
        return f"""The previous block failed. Fix it.

## Original Specification
Inputs: {json.dumps(request.inputs)}
Outputs: {json.dumps(request.outputs)}
Purpose: {request.purpose}

## Test Case
Input: {json.dumps(request.test_input)}
Expected Output: {json.dumps(request.expected_output)}

## Previous Code (output_format: {previous.output_format.value})
```python
{previous.code}
```

## Execution Result
Exit Code: {result.exit_code}
Stdout: {result.stdout[:1000] if result.stdout else "(empty)"}
Stderr: {result.stderr[:1000] if result.stderr else "(empty)"}

## Error Analysis
{result.error or "Output did not match expected value."}

Fix the code and return the corrected version."""
    
    def _parse_synthesis_response(self, response: str) -> SynthesisResult:
        """Parse LLM response into SynthesisResult."""
        json_matches = list(re.finditer(r"\{[\s\S]*?\}", response))
        
        if not json_matches:
            raise SynthesisError("No JSON object found in LLM response")
        
        data = None
        for match in json_matches:
            try:
                candidate = json.loads(match.group())
                if isinstance(candidate, dict) and "code" in candidate:
                    data = candidate
                    break
            except json.JSONDecodeError:
                continue
        
        if data is None:
            all_json_text = re.search(r"\{[\s\S]*\}", response)
            if all_json_text:
                try:
                    data = json.loads(all_json_text.group())
                except json.JSONDecodeError:
                    brace_count = 0
                    start_idx = response.find("{")
                    if start_idx >= 0:
                        for i, char in enumerate(response[start_idx:], start_idx):
                            if char == "{":
                                brace_count += 1
                            elif char == "}":
                                brace_count -= 1
                                if brace_count == 0:
                                    try:
                                        data = json.loads(response[start_idx : i + 1])
                                        break
                                    except json.JSONDecodeError:
                                        continue
        
        if data is None:
            raise SynthesisError("Could not parse valid JSON from LLM response")
        
        if "code" not in data:
            raise SynthesisError("Response missing 'code' field")
        
        code = data["code"]
        if "\\n" in code and "\n" not in code:
            code = code.replace("\\n", "\n").replace("\\t", "\t")
        data["code"] = code
        
        output_format_str = data.get("output_format", "json").lower()
        try:
            output_format = OutputFormat(output_format_str)
        except ValueError:
            logger.warning("Unknown output format '%s', defaulting to JSON", output_format_str)
            output_format = OutputFormat.JSON
        
        required_packages = data.get("required_packages")
        if required_packages and not isinstance(required_packages, list):
            required_packages = [required_packages]
        
        return SynthesisResult(
            code=data["code"],
            output_format=output_format,
            output_path=data.get("output_path"),
            required_packages=required_packages,
        )
    
    async def _call_llm(self, system: str, user: str) -> str:
        """Call LLM with system and user prompts.
        
        Uses direct SDK calls to OpenAI or Anthropic.
        """
        if self.provider == "openai":
            from openai import OpenAI
            
            client = OpenAI()
            
            def _call():
                return client.chat.completions.create(
                    model=self.model,
                    temperature=0.0,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
            
            response = await asyncio.to_thread(_call)
            return response.choices[0].message.content or ""
        
        elif self.provider == "anthropic":
            import anthropic
            
            client = anthropic.Anthropic()
            
            def _call():
                return client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=0.0,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
            
            response = await asyncio.to_thread(_call)
            return response.content[0].text
        
        else:
            raise SynthesisError(f"Unknown provider: {self.provider}")
        
        # ─────────────────────────────────────────────────────────────────────
        # Alternative: Use Demo/backend/llm/service.py
        # Uncomment below and comment out the direct SDK code above
        # ─────────────────────────────────────────────────────────────────────
        # import sys as _sys
        # from pathlib import Path
        # 
        # project_root = Path(__file__).parent.parent
        # demo_backend = project_root / "Demo" / "backend"
        # if str(demo_backend) not in _sys.path:
        #     _sys.path.insert(0, str(demo_backend))
        # 
        # from llm.service import call_llm
        # 
        # return await call_llm(
        #     system=system,
        #     user=user,
        #     provider=self.provider,
        #     model=self.model,
        # )


# =============================================================================
# BlockValidator
# =============================================================================


class BlockValidator:
    """Validates block output against expected gold-standard output.
    
    Supports multiple output formats: JSON, text, file, query.
    """
    
    def compare(
        self,
        actual: str | None,
        expected: Any,
        output_format: OutputFormat,
    ) -> tuple[bool, str]:
        """Compare actual output against expected.
        
        Args:
            actual: Actual output from execution
            expected: Expected gold-standard output
            output_format: Format to use for comparison
            
        Returns:
            Tuple of (match: bool, diff_description: str)
        """
        if actual is None:
            return False, "No output received"
        
        if output_format == OutputFormat.JSON:
            return self._compare_json(actual, expected)
        elif output_format == OutputFormat.TEXT:
            return self._compare_text(actual, expected)
        elif output_format == OutputFormat.FILE:
            return self._compare_file(actual, expected)
        elif output_format == OutputFormat.QUERY:
            return self._compare_query(actual, expected)
        else:
            return False, f"Unknown output format: {output_format}"
    
    def _compare_json(self, actual: str, expected: Any) -> tuple[bool, str]:
        """Compare JSON output."""
        try:
            actual_parsed = json.loads(actual.strip())
        except json.JSONDecodeError as e:
            return False, f"Failed to parse actual output as JSON: {e}\nActual: {actual[:500]}"
        
        if actual_parsed == expected:
            return True, ""
        
        diff = self._describe_json_diff(actual_parsed, expected)
        return False, diff
    
    def _compare_text(self, actual: str, expected: str) -> tuple[bool, str]:
        """Compare plain text output with whitespace normalization."""
        actual_normalized = actual.strip()
        expected_normalized = str(expected).strip()
        
        if actual_normalized == expected_normalized:
            return True, ""
        
        return False, f"Text mismatch:\nExpected: {expected_normalized[:500]}\nActual: {actual_normalized[:500]}"
    
    def _compare_file(self, actual: str, expected: str) -> tuple[bool, str]:
        """Compare file content."""
        actual_normalized = actual.strip()
        expected_normalized = str(expected).strip()
        
        if actual_normalized == expected_normalized:
            return True, ""
        
        return False, f"File content mismatch:\nExpected: {expected_normalized[:500]}\nActual: {actual_normalized[:500]}"
    
    def _compare_query(self, actual: str, expected: str) -> tuple[bool, str]:
        """Compare query strings with normalization."""
        actual_normalized = self._normalize_query(actual)
        expected_normalized = self._normalize_query(str(expected))
        
        if actual_normalized == expected_normalized:
            return True, ""
        
        return False, f"Query mismatch:\nExpected: {expected_normalized}\nActual: {actual_normalized}"
    
    def _normalize_query(self, query: str) -> str:
        """Normalize a query string for comparison."""
        normalized = " ".join(query.strip().split())
        normalized = normalized.upper()
        return normalized
    
    def _describe_json_diff(self, actual: Any, expected: Any, path: str = "") -> str:
        """Describe differences between two JSON values."""
        if type(actual) != type(expected):
            return f"Type mismatch at {path or 'root'}: expected {type(expected).__name__}, got {type(actual).__name__}"
        
        if isinstance(expected, dict):
            diffs = []
            all_keys = set(actual.keys()) | set(expected.keys())
            for key in all_keys:
                key_path = f"{path}.{key}" if path else key
                if key not in actual:
                    diffs.append(f"Missing key: {key_path}")
                elif key not in expected:
                    diffs.append(f"Extra key: {key_path}")
                elif actual[key] != expected[key]:
                    diffs.append(self._describe_json_diff(actual[key], expected[key], key_path))
            return "\n".join(diffs) if diffs else ""
        
        if isinstance(expected, list):
            if len(actual) != len(expected):
                return f"Array length mismatch at {path or 'root'}: expected {len(expected)}, got {len(actual)}"
            diffs = []
            for i, (a, e) in enumerate(zip(actual, expected)):
                if a != e:
                    diffs.append(self._describe_json_diff(a, e, f"{path}[{i}]"))
            return "\n".join(diffs) if diffs else ""
        
        return f"Value mismatch at {path or 'root'}: expected {expected!r}, got {actual!r}"


# =============================================================================
# Orchestrator
# =============================================================================


class Orchestrator:
    """Orchestrates the full block synthesis flow.
    
    Coordinates between synthesizer, sandbox, and validator with
    iterative repair loop.
    """
    
    def __init__(
        self,
        synthesizer: BlockSynthesizer,
        sandbox: SandboxManager,
        validator: BlockValidator,
        max_iterations: int = 6,
    ):
        self.synthesizer = synthesizer
        self.sandbox = sandbox
        self.validator = validator
        self.max_iterations = max_iterations
    
    async def run(self, request: BlockRequest) -> str:
        """Run the full synthesis flow.
        
        Args:
            request: Block requirements including test case
            
        Returns:
            Final working block code
            
        Raises:
            MaxIterationsError: If synthesis fails after max iterations
            SandboxError: If container operations fail
            SynthesisError: If LLM generation fails
        """
        try:
            self.sandbox.start()
            
            # Install any packages that weren't in the selected tier
            if self.sandbox.missing_packages:
                logger.info(
                    "Installing packages not in tier: %s", 
                    self.sandbox.missing_packages
                )
                install_result = self.sandbox.install_packages(self.sandbox.missing_packages)
                if not install_result.success:
                    logger.warning("Initial package installation failed: %s", install_result.error)
            
            logger.info("Generating initial block for: %s", request.purpose)
            synthesis = await self.synthesizer.generate_initial_block(request)
            logger.info("Initial block generated (format: %s)", synthesis.output_format.value)
            
            for iteration in range(self.max_iterations):
                logger.info("Iteration %d/%d", iteration + 1, self.max_iterations)
                
                # Install any additional packages requested by the LLM
                if synthesis.required_packages:
                    # Only install packages not already in the tier or previously installed
                    new_packages = [
                        p for p in synthesis.required_packages 
                        if p not in (self.sandbox.tier_info or {}).get("packages", [])
                    ]
                    if new_packages:
                        logger.info("Installing LLM-requested packages: %s", new_packages)
                        install_result = self.sandbox.install_packages(new_packages)
                        if not install_result.success:
                            logger.warning("Package installation failed: %s", install_result.error)
                            result = install_result
                            result.error = f"Failed to install packages: {install_result.stderr}"
                            synthesis = await self.synthesizer.repair_block(request, synthesis, result)
                            continue
                
                result = self.sandbox.execute(synthesis.code, request.test_input)
                
                if synthesis.output_format == OutputFormat.FILE and synthesis.output_path:
                    actual = self.sandbox.extract_file(synthesis.output_path)
                else:
                    actual = result.stdout
                
                if not result.success:
                    logger.warning("Execution failed: %s", result.error)
                    synthesis = await self.synthesizer.repair_block(request, synthesis, result)
                    continue
                
                match, diff = self.validator.compare(
                    actual, request.expected_output, synthesis.output_format
                )
                
                if match:
                    logger.info("Block validated successfully after %d iteration(s)", iteration + 1)
                    return synthesis.code
                
                logger.warning("Output mismatch: %s", diff[:200])
                
                result.error = diff
                synthesis = await self.synthesizer.repair_block(request, synthesis, result)
            
            raise MaxIterationsError(
                f"Failed to synthesize valid block after {self.max_iterations} iterations"
            )
        
        finally:
            self.sandbox.cleanup()


# =============================================================================
# Convenience Functions
# =============================================================================


async def synthesize_block(
    inputs: list[str],
    outputs: list[str],
    purpose: str,
    test_input: Any,
    expected_output: Any,
    prompt_file: str | Path = "block_synthesis/prompts/master_prompt.txt",
    provider: str = "openai",
    model: str = "gpt-4o",
    sandbox_backend: str = "auto",
    docker_image: str | None = None,
    allow_pip_install: bool = False,
    required_packages: list[str] | None = None,
    use_tiers: bool = True,
    max_iterations: int = 6,
) -> str:
    """Convenience function to synthesize a block.
    
    Args:
        inputs: Input field names
        outputs: Output field names
        purpose: What the block should do
        test_input: Gold-standard input
        expected_output: Gold-standard expected output
        prompt_file: Path to master prompt file
        provider: LLM provider (openai or anthropic)
        model: Model name
        sandbox_backend: "auto", "docker", or "subprocess"
        docker_image: Docker image for sandbox (overrides tier selection)
        allow_pip_install: Allow dynamic package installation (requires docker)
        required_packages: Packages required by the block (used for tier selection)
        use_tiers: Whether to use tiered Docker images (default: True)
        max_iterations: Maximum repair attempts
        
    Returns:
        Final working block code
    """
    request = BlockRequest(
        inputs=inputs,
        outputs=outputs,
        purpose=purpose,
        test_input=test_input,
        expected_output=expected_output,
    )
    
    synthesizer = BlockSynthesizer(
        prompt_file=prompt_file,
        provider=provider,
        model=model,
    )
    sandbox = SandboxManager(
        backend=sandbox_backend,
        image=docker_image,
        allow_pip_install=allow_pip_install,
        required_packages=required_packages,
        use_tiers=use_tiers,
    )
    validator = BlockValidator()
    orchestrator = Orchestrator(
        synthesizer=synthesizer,
        sandbox=sandbox,
        validator=validator,
        max_iterations=max_iterations,
    )
    
    return await orchestrator.run(request)


# =============================================================================
# Main (for testing)
# =============================================================================


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    async def main():
        request = BlockRequest(
            inputs=["numbers"],
            outputs=["sum"],
            purpose="Sum all numbers in the input list",
            test_input={"numbers": [1, 2, 3, 4, 5]},
            expected_output={"sum": 15},
        )
        
        try:
            code = await synthesize_block(
                inputs=request.inputs,
                outputs=request.outputs,
                purpose=request.purpose,
                test_input=request.test_input,
                expected_output=request.expected_output,
            )
            print("=" * 60)
            print("SYNTHESIZED BLOCK:")
            print("=" * 60)
            print(code)
        except Exception as e:
            print(f"Synthesis failed: {e}", file=sys.stderr)
            sys.exit(1)
    
    asyncio.run(main())
