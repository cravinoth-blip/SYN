"""
Tool 6: CI Supplements — read user-uploaded Excel/CSV datasets.

These are competitive benchmarking tables, epidemiology datasets,
pricing grids, etc. that the user provides alongside the evidence spine.
The tool reads and summarises them so the model can decide what to
pass to the code interpreter for deeper analysis.
"""

import os
import json
from tools.base import BaseTool

try:
    import pandas as pd
except ImportError:
    pd = None


class CISupplementsTool(BaseTool):
    name = "read_ci_supplement"
    description = (
        "Read a CI supplement file (Excel or CSV) uploaded by the user. "
        "Returns sheet names, column headers, row counts, and a data preview. "
        "Use this to understand available data before writing code interpreter "
        "scripts to analyse it in depth."
    )

    def __init__(self, supplement_dir: str = "./data/supplements"):
        self.supplement_dir = supplement_dir
        self._available_files: list[str] = []
        self._scan_files()

    def _scan_files(self):
        if os.path.isdir(self.supplement_dir):
            self._available_files = [
                f for f in os.listdir(self.supplement_dir)
                if f.endswith((".xlsx", ".xls", ".csv", ".tsv"))
            ]

    def register_files(self, file_paths: list[str]):
        """Register supplement files from arbitrary locations."""
        os.makedirs(self.supplement_dir, exist_ok=True)
        import shutil
        for path in file_paths:
            if os.path.isfile(path):
                dest = os.path.join(self.supplement_dir, os.path.basename(path))
                shutil.copy2(path, dest)
        self._scan_files()

    def _execute(self, filename: str = "", action: str = "preview") -> dict:
        if pd is None:
            raise ImportError("pandas not installed. pip install pandas")

        # If no filename, list available files
        if not filename or action == "list":
            return {
                "result": {"available_files": self._available_files},
                "summary": f"{len(self._available_files)} supplement files available: {self._available_files}",
                "sources": [],
            }

        filepath = os.path.join(self.supplement_dir, filename)
        if not os.path.isfile(filepath):
            return {
                "result": None,
                "summary": f"File not found: {filename}. Available: {self._available_files}",
                "sources": [],
            }

        result = {"filename": filename, "sheets": {}}

        if filename.endswith((".xlsx", ".xls")):
            xls = pd.ExcelFile(filepath)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                result["sheets"][sheet_name] = {
                    "columns": list(df.columns),
                    "rows": len(df),
                    "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                    "preview": df.head(5).to_dict(orient="records"),
                    "stats": df.describe(include="all").to_dict() if len(df) > 0 else {},
                }
        elif filename.endswith((".csv", ".tsv")):
            sep = "\t" if filename.endswith(".tsv") else ","
            df = pd.read_csv(filepath, sep=sep)
            result["sheets"]["default"] = {
                "columns": list(df.columns),
                "rows": len(df),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "preview": df.head(5).to_dict(orient="records"),
                "stats": df.describe(include="all").to_dict() if len(df) > 0 else {},
            }

        sheet_count = len(result["sheets"])
        total_rows = sum(s["rows"] for s in result["sheets"].values())

        return {
            "result": result,
            "summary": f"{filename}: {sheet_count} sheet(s), {total_rows} total rows",
            "sources": [{"title": filename, "url": ""}],
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
                        "filename": {
                            "type": "string",
                            "description": "Name of the supplement file to read (or empty to list available files)",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["preview", "list"],
                            "description": "'preview' to read a file, 'list' to see available files",
                        },
                    },
                    "required": [],
                },
            },
        }
