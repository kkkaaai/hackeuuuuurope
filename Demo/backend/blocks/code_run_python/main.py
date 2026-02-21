"""Code run Python block — executes user-provided Python in a sandboxed namespace."""

import json
import traceback
from io import StringIO


async def execute(inputs: dict, context: dict) -> dict:
    code = inputs["code"]
    timeout = inputs.get("timeout_seconds", 30)

    stdout_buf = StringIO()
    stderr_buf = StringIO()
    return_value = None

    namespace = {
        "__builtins__": {
            "print": lambda *a, **kw: print(*a, file=stdout_buf, **kw),
            "len": len, "range": range, "int": int, "float": float,
            "str": str, "list": list, "dict": dict, "bool": bool,
            "max": max, "min": min, "sum": sum, "sorted": sorted,
            "enumerate": enumerate, "zip": zip, "map": map, "filter": filter,
            "abs": abs, "round": round, "type": type, "isinstance": isinstance,
            "True": True, "False": False, "None": None,
        },
        "json": json,
    }

    try:
        exec(code, namespace)
        return_value = str(namespace.get("result", ""))
        success = True
    except Exception:
        stderr_buf.write(traceback.format_exc())
        success = False

    return {
        "stdout": stdout_buf.getvalue(),
        "stderr": stderr_buf.getvalue(),
        "return_value": return_value or "",
        "success": success,
    }
