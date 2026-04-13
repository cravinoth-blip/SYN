"""
Base tool class — all 6 tools inherit from this.

Provides:
- Standardised execute() → result interface
- Automatic audit logging for every call
- OpenAI function-calling schema generation
- Error handling with graceful degradation
- corporate_session(): requests.Session pre-wired to trust the Windows
  system certificate store (handles Syneos Health SSL inspection proxy)
"""

import ssl
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

from audit.logger import AuditLogger


def corporate_session() -> "requests.Session":
    """
    Return a requests.Session whose SSL verification uses the Windows system
    certificate store rather than Python's bundled certifi.

    On the Syneos Health corporate network the proxy re-signs HTTPS traffic
    with an internal CA. The OS trust store already accepts that CA (IT pushes
    it via GPO), but certifi does not — so plain requests.get() calls to
    external APIs (ClinicalTrials.gov, openFDA, Tavily) all fail with
    CERTIFICATE_VERIFY_FAILED.

    Falls back to the default session (certifi) on non-Windows platforms or
    if loading the system store fails.
    """
    import requests
    from requests.adapters import HTTPAdapter

    session = requests.Session()

    try:
        from urllib3.util.ssl_ import create_urllib3_context

        class _SysCAAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                ctx = create_urllib3_context()
                ctx.load_default_certs(ssl.Purpose.SERVER_AUTH)
                kwargs["ssl_context"] = ctx
                super().init_poolmanager(*args, **kwargs)

            def proxy_manager_for(self, proxy, **proxy_kwargs):
                ctx = create_urllib3_context()
                ctx.load_default_certs(ssl.Purpose.SERVER_AUTH)
                proxy_kwargs["ssl_context"] = ctx
                return super().proxy_manager_for(proxy, **proxy_kwargs)

        session.mount("https://", _SysCAAdapter())
    except Exception:
        pass  # non-Windows or urllib3 unavailable — use default session

    return session


class BaseTool(ABC):
    """Abstract base for all pipeline tools."""

    name: str = "base_tool"
    description: str = ""

    @abstractmethod
    def _execute(self, **kwargs) -> dict:
        """
        Subclasses implement this. Must return:
        {
            "result": <any>,
            "summary": "Human-readable summary of what was returned",
            "sources": [{"url": ..., "title": ...}]   # optional
        }
        """
        ...

    @abstractmethod
    def openai_schema(self) -> dict:
        """
        Return the OpenAI function-calling schema for this tool.
        {
            "type": "function",
            "function": {
                "name": "...",
                "description": "...",
                "parameters": { ... }
            }
        }
        """
        ...

    def execute(
        self,
        audit: AuditLogger,
        pass_number: int,
        decision_note: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """
        Public entry point. Wraps _execute with timing and audit logging.
        """
        start = time.time()
        error = None
        result = {}

        try:
            result = self._execute(**kwargs)
        except Exception as e:
            error = f"{type(e).__name__}: {str(e)}"
            result = {"result": None, "summary": f"FAILED: {error}", "sources": []}

        duration_ms = int((time.time() - start) * 1000)

        audit.log_tool_call(
            pass_number=pass_number,
            tool_name=self.name,
            tool_input=kwargs,
            tool_output=result.get("result"),
            output_summary=result.get("summary", ""),
            decision_note=decision_note,
            duration_ms=duration_ms,
            error=error,
        )

        return result


class ToolHarness:
    """
    Registry of all available tools.
    Provides the combined OpenAI function schemas and dispatches calls.
    """

    def __init__(self, tools: list[BaseTool], audit: AuditLogger):
        self.tools = {t.name: t for t in tools}
        self.audit = audit

    def get_openai_tools(self) -> list[dict]:
        """Return all tool schemas for the OpenAI API tools parameter."""
        return [t.openai_schema() for t in self.tools.values()]

    def dispatch(
        self,
        tool_name: str,
        arguments: dict,
        pass_number: int,
        decision_note: Optional[str] = None,
    ) -> dict:
        """
        Called by the orchestrator when the model requests a tool call.
        Routes to the correct tool and returns the result.
        """
        tool = self.tools.get(tool_name)
        if not tool:
            return {
                "result": None,
                "summary": f"Unknown tool: {tool_name}",
                "sources": [],
            }
        return tool.execute(
            audit=self.audit,
            pass_number=pass_number,
            decision_note=decision_note,
            **arguments,
        )
