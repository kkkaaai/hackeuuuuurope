from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import uuid
from typing import Any

from app.blocks.executor import register_implementation

logger = logging.getLogger("agentflow.blocks.act")


@register_implementation("commerce_place_order")
async def commerce_place_order(inputs: dict[str, Any]) -> dict[str, Any]:
    """Place an order for a product (mock implementation)."""
    product_name = inputs["product_name"]
    price = float(inputs["price"])
    quantity = int(inputs.get("quantity", 1))

    logger.info("Simulated order: %dx %s at %.2f", quantity, product_name, price)

    return {
        "order_id": f"ORD-{uuid.uuid4().hex[:8].upper()}",
        "status": "simulated",
        "total": round(price * quantity, 2),
        "estimated_delivery": "3-5 business days",
        "note": "This is a simulated order — no real purchase was made",
    }


@register_implementation("code_run_python")
async def code_run_python(inputs: dict[str, Any]) -> dict[str, Any]:
    """Execute sandboxed Python code in a subprocess with strict limits."""
    code = inputs["code"]
    timeout_seconds = min(int(inputs.get("timeout_seconds", 10)), 30)

    # Write code to a temp file and run in subprocess for isolation
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()

        try:
            python_bin = shutil.which("python3") or shutil.which("python") or "python3"
            result = subprocess.run(
                [python_bin, "-u", f.name],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env={"PATH": "/usr/bin:/usr/local/bin:/opt/homebrew/bin"},
            )
            return {
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:2000],
                "return_value": result.stdout.strip().split("\n")[-1] if result.stdout else "",
                "success": result.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Execution timed out after {timeout_seconds}s",
                "return_value": "",
                "success": False,
            }
