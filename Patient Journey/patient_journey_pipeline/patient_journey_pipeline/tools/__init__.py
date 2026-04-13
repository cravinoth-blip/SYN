from tools.base import BaseTool, ToolHarness
from tools.snowflake_search import SnowflakeSearchTool
from tools.spine_search import SpineSearchTool
from tools.web_search import WebSearchTool
from tools.code_interpreter import CodeInterpreterTool
from tools.clinical_trials import ClinicalTrialsTool
from tools.fda_labelling import FDALabellingTool
from tools.ci_supplements import CISupplementsTool


def build_tool_harness(audit, supplements: list[str] = None) -> ToolHarness:
    """Factory: create the full tool harness wired to an audit logger."""
    ci_tool = CISupplementsTool()
    if supplements:
        ci_tool.register_files(supplements)

    tools = [
        SnowflakeSearchTool(),   # Primary: real evidence from Snowflake DB
        SpineSearchTool(),        # Secondary: locally-ingested docs (ChromaDB)
        CodeInterpreterTool(),
        WebSearchTool(),
        ClinicalTrialsTool(),
        FDALabellingTool(),
        ci_tool,
    ]
    return ToolHarness(tools=tools, audit=audit)
