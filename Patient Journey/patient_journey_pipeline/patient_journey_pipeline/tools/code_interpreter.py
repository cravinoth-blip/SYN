"""
Tool 2: Code Interpreter — sandboxed Python execution.

For production: use OpenAI's native code interpreter (Assistants API)
or a sandboxed environment like E2B, Modal, or Docker.

This skeleton uses subprocess with a timeout as a local fallback.
Replace with your preferred sandboxing solution.
"""

import subprocess
import tempfile
import os
import json
from tools.base import BaseTool


class CodeInterpreterTool(BaseTool):
    name = "code_interpreter"
    description = (
        "Execute Python code for quantitative modelling, data extraction, "
        "tabular analysis, chart generation, and file creation. The interpreter "
        "has access to pandas, openpyxl, matplotlib, numpy, and scipy. "
        "Use this to analyse CI supplements, build Excel artifacts, and compute "
        "derived metrics."
    )

    def __init__(self, working_dir: str = "./workspace"):
        self.working_dir = os.path.abspath(working_dir)
        os.makedirs(self.working_dir, exist_ok=True)

    def _execute(self, code: str, description: str = "") -> dict:
        """
        Execute Python code in a subprocess with a timeout.

        PRODUCTION NOTE: Replace this with:
        - OpenAI Assistants API code_interpreter tool type
        - E2B sandbox (pip install e2b_code_interpreter)
        - Docker container execution
        """
        # Write code to temp file
        script_path = os.path.join(self.working_dir, "_exec_script.py")
        with open(script_path, "w") as f:
            f.write(code)

        try:
            result = subprocess.run(
                ["python", script_path],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.working_dir,
            )

            stdout = result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout
            stderr = result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr

            # Check for files created
            created_files = []
            for fname in os.listdir(self.working_dir):
                fpath = os.path.join(self.working_dir, fname)
                if fname != "_exec_script.py" and os.path.isfile(fpath):
                    created_files.append(fname)

            success = result.returncode == 0

            return {
                "result": {
                    "success": success,
                    "stdout": stdout,
                    "stderr": stderr if not success else "",
                    "created_files": created_files,
                },
                "summary": (
                    f"Code executed {'successfully' if success else 'with errors'}. "
                    f"Files created: {created_files if created_files else 'none'}. "
                    f"Output: {stdout[:200]}"
                ),
                "sources": [],
            }

        except subprocess.TimeoutExpired:
            return {
                "result": {"success": False, "stdout": "", "stderr": "Execution timed out (120s)", "created_files": []},
                "summary": "Code execution timed out after 120 seconds",
                "sources": [],
            }

    def openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute. Has access to pandas, openpyxl, matplotlib, numpy, scipy.",
                        },
                        "description": {
                            "type": "string",
                            "description": "Brief description of what this code does (for audit trail)",
                        },
                    },
                    "required": ["code"],
                },
            },
        }
