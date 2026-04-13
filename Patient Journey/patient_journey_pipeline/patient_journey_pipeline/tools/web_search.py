"""
Tool 3: Web Search — current market data, benchmarks, patient experience reports.

Uses Tavily (designed for LLM agents). Swap to Bing/Google as needed.

SSL note: on the Syneos Health corporate network the proxy re-signs HTTPS traffic
with an internal CA that Python's certifi bundle does not trust. We build an SSL
context from Python's default trust settings and attempt to load OS-level server-auth
certificates where the platform supports it, then inject that context into the HTTP
client used by TavilyClient.
"""

import ssl
import config
from tools.base import BaseTool

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None


def _system_ssl_context() -> ssl.SSLContext:
    """
    Return an SSL context initialized from Python's default trust settings,
    and attempt to load OS default server-auth certificates where supported
    (Windows system store, macOS keychain, etc.). Falls back silently on
    platforms where this is unavailable.
    """
    ctx = ssl.create_default_context()
    try:
        ctx.load_default_certs(ssl.Purpose.SERVER_AUTH)
    except Exception:
        pass
    return ctx


def _make_tavily_client() -> "TavilyClient":
    """
    Construct a TavilyClient with corporate-CA-aware SSL verification.

    Tavily v0.3+ accepts an `httpx_client` kwarg; older versions do not.
    We try the modern path first and fall back to monkey-patching the
    underlying requests session on older builds.
    """
    if TavilyClient is None:
        raise ImportError("tavily-python not installed. pip install tavily-python")

    api_key = config.TAVILY_API_KEY
    if not api_key:
        raise RuntimeError(
            "Missing TAVILY_API_KEY — set it in the .env file before using web search."
        )

    ssl_ctx = _system_ssl_context()

    # ── Modern path: inject a pre-configured httpx client ──────────────────
    try:
        import httpx
    except ImportError:
        httpx = None

    if httpx is not None:
        try:
            http_client = httpx.Client(verify=ssl_ctx, timeout=20.0)
            return TavilyClient(api_key=api_key, httpx_client=http_client)
        except TypeError:
            pass  # older tavily version — doesn't accept httpx_client kwarg

    # ── Legacy path: mount the SSL context on the requests session ──────────
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.ssl_ import create_urllib3_context

    class _SysCAAdapter(HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            ctx = create_urllib3_context()
            ctx.load_default_certs(ssl.Purpose.SERVER_AUTH)
            kwargs["ssl_context"] = ctx
            super().init_poolmanager(*args, **kwargs)

    client = TavilyClient(api_key=api_key)
    if hasattr(client, "_session") and isinstance(client._session, requests.Session):
        client._session.mount("https://", _SysCAAdapter())
    else:
        raise RuntimeError(
            "Legacy Tavily client does not expose a patchable session — "
            "SSL patching could not be applied. Try upgrading tavily-python."
        )

    return client


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Search the web for current information: market data, published patient "
        "experiences, clinical guidelines, epidemiology statistics, treatment "
        "benchmarks, and healthcare policy updates."
    )

    def __init__(self):
        self._client = None

    def _get_client(self) -> "TavilyClient":
        if self._client is None:
            self._client = _make_tavily_client()
        return self._client

    def _execute(self, query: str, max_results: int = 5) -> dict:
        max_results = max(1, min(int(max_results), 10))

        try:
            client = self._get_client()
            response = client.search(
                query=query,
                max_results=max_results,
                include_answer=True,
                search_depth="advanced",
            )
        except Exception as e:
            return {
                "result": {"answer": "", "results": []},
                "summary": f"Web search failed: {type(e).__name__}",
                "sources": [],
                "error": f"{type(e).__name__}: {e}",
            }

        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": (r.get("content", "") or "")[:1500],
                "score": r.get("score", 0),
            })

        return {
            "result": {
                "answer": response.get("answer", ""),
                "results": results,
            },
            "summary": f"{len(results)} web results. Top: {results[0]['title'] if results else 'none'}",
            "sources": [{"title": r["title"], "url": r["url"]} for r in results],
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
                        "query": {
                            "type": "string",
                            "description": "Web search query",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Number of results to return (default 5, max 10)",
                        },
                    },
                    "required": ["query"],
                },
            },
        }
