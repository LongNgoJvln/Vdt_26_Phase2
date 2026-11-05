"""
mcp_manager.py

Manages connections to MCP (Model Context Protocol) tool servers.
Each server exposes tools that are made available to the agent loop.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Hard cap on any single MCP tool call. Streamable-HTTP sessions can wedge
# silently when the remote service rotates endpoints or load-balances to a
# node that has no session state — without this cap, the agent loop blocks
# forever on a single hung tool call.
MCP_CALL_TIMEOUT = int(os.getenv("MCP_CALL_TIMEOUT", "15"))

# Consecutive failures before we mark the server as "error" and force a
# reconnect on the next call. Three strikes = the session is wedged, not
# just a one-off tool failure.
MCP_FAILURE_THRESHOLD = 3


def _schema_identifier_key(value: Any) -> str:
    """Return a separator/case-insensitive key for schema name matching.

    This deliberately applies to *names only*. Argument values are never
    changed. For example, ``resource_type`` and ``resourceType`` both become
    ``resourcetype``.
    """
    return "".join(char.lower() for char in str(value) if char.isalnum())


def _normalise_arguments_to_schema(
    arguments: Any,
    schema: Any,
    *,
    path: str = "",
) -> tuple[Any, List[tuple[str, str]]]:
    """Map model-generated argument keys to exact JSON-schema property names.

    Local models sometimes emit Python-style snake_case even when an MCP
    server advertises camelCase. Matching is schema-aware and only happens
    when one advertised property is an unambiguous canonical match. Unknown
    keys are preserved for schemas that intentionally allow extra properties.

    Exact keys always win. Conflicting aliases raise ``ValueError`` instead
    of silently selecting one model-generated value.
    """
    if not isinstance(schema, dict):
        return arguments, []

    if isinstance(arguments, list):
        item_schema = schema.get("items")
        if not isinstance(item_schema, dict):
            return arguments, []
        normalised_items = []
        renames: List[tuple[str, str]] = []
        for index, item in enumerate(arguments):
            child_path = f"{path}[{index}]" if path else f"[{index}]"
            normalised, child_renames = _normalise_arguments_to_schema(
                item, item_schema, path=child_path
            )
            normalised_items.append(normalised)
            renames.extend(child_renames)
        return normalised_items, renames

    if not isinstance(arguments, dict):
        return arguments, []

    properties = schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        return arguments, []

    # Only accept aliases that resolve to exactly one advertised property.
    canonical_properties: Dict[str, List[str]] = {}
    for property_name in properties:
        canonical_properties.setdefault(
            _schema_identifier_key(property_name), []
        ).append(property_name)

    output: Dict[str, Any] = {}
    source_for_target: Dict[str, str] = {}
    renames: List[tuple[str, str]] = []

    # Process exact schema keys first so an alias can never overwrite one.
    ordered_keys = sorted(arguments, key=lambda key: key not in properties)
    for raw_key in ordered_keys:
        value = arguments[raw_key]
        target_key = raw_key
        if raw_key not in properties:
            matches = canonical_properties.get(_schema_identifier_key(raw_key), [])
            if len(matches) == 1:
                target_key = matches[0]

        if target_key in output:
            if output[target_key] != value:
                previous = source_for_target[target_key]
                location = f" at '{path}'" if path else ""
                raise ValueError(
                    f"Conflicting MCP arguments{location}: '{previous}' and "
                    f"'{raw_key}' both map to '{target_key}'."
                )
            # Identical duplicate alias: keep the exact/first value once.
            continue

        property_schema = properties.get(target_key)
        child_path = f"{path}.{target_key}" if path else target_key
        if isinstance(property_schema, dict):
            value, child_renames = _normalise_arguments_to_schema(
                value, property_schema, path=child_path
            )
            renames.extend(child_renames)

        output[target_key] = value
        source_for_target[target_key] = raw_key
        if target_key != raw_key:
            source_path = f"{path}.{raw_key}" if path else raw_key
            target_path = f"{path}.{target_key}" if path else target_key
            renames.append((source_path, target_path))

    return output, renames

# anyio exception classes that indicate the underlying MCP transport
# stream is dead and the session object is unusable. We match by class
# (not just error string) because their str() is often empty.
try:
    from anyio import (
        ClosedResourceError as _AnyioClosedResourceError,
        EndOfStream as _AnyioEndOfStream,
        BrokenResourceError as _AnyioBrokenResourceError,
    )
    _STREAM_DEAD_EXCEPTIONS = (
        _AnyioClosedResourceError,
        _AnyioEndOfStream,
        _AnyioBrokenResourceError,
    )
except ImportError:  # pragma: no cover - anyio is a transitive dep of mcp
    _STREAM_DEAD_EXCEPTIONS = ()


def _format_mcp_connection_error(name: str, command: str = "", args: Optional[List[str]] = None, error: Exception = None) -> str:
    """Return a user-actionable MCP connection error message."""
    args = args or []
    raw_error = str(error) if error else "Unknown error"
    command_line = " ".join([command or "", *args]).strip()
    lower_command = command_line.lower()

    if "@playwright/mcp" in lower_command:
        return (
            f"{raw_error}\n\n"
            "Browser MCP could not start. On fresh installs, cache the Playwright MCP package once before connecting:\n\n"
            "npx -y @playwright/mcp@latest --version\n\n"
            "Then restart VHT Network Automation and reconnect the Browser MCP server."
        )

    return raw_error



class McpManager:
    """Manages MCP server connections and tool routing."""

    def __init__(self):
        # server_id -> connection state
        self._connections: Dict[str, Dict[str, Any]] = {}
        # server_id -> list of tool schemas
        self._tools: Dict[str, List[Dict]] = {}
        # server_id -> MCP ClientSession
        self._sessions: Dict[str, Any] = {}
        # server_id -> exit stack (for cleanup)
        self._stacks: Dict[str, Any] = {}
        # server_id -> anyio task-group owning the streamable_http session
        self._owner_tasks: Dict[str, Any] = {}
        # server_id -> asyncio task hosting that task-group (for join on disconnect)
        self._owner_tasks_owner: Dict[str, Any] = {}
        # In-flight stack-close tasks (kept alive so a return from
        # disconnect_server never races teardown into the response body).
        self._close_tasks: set = set()
        # Tracking updates to tools/connections for RAG indexing
        self._generation = 0

    async def connect_server(
        self,
        server_id: str,
        name: str,
        transport: str,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Connect to an MCP server via stdio, SSE, or streamable_http transport.

        Args:
            server_id: Unique server identifier
            name: Human-readable server name
            transport: One of "stdio", "sse", "streamable_http"
            command: Executable path (for stdio)
            args: Command line arguments (for stdio)
            env: Environment variables (for stdio)
            url: Server URL (for sse/streamable_http)
            api_key: Optional API key for HTTP transports (added as Bearer token)
            headers: Optional dict of custom HTTP headers
        """
        try:
            if transport == "stdio":
                res = await self._connect_stdio(server_id, name, command, args or [], env or {})
            elif transport == "sse":
                res = await self._connect_sse(server_id, name, url, api_key=api_key, custom_headers=headers)
            elif transport == "streamable_http":
                res = await self._connect_streamable_http(
                    server_id, name, url, api_key=api_key or "", custom_headers=headers or {}
                )
            else:
                logger.error(f"Unknown MCP transport: {transport}")
                res = False
            if res:
                self._generation += 1
            return res
        except Exception as e:
            logger.error(f"Failed to connect MCP server {name} ({server_id}): {e}")
            error_message = _format_mcp_connection_error(name, command or "", args or [], e)
            self._connections[server_id] = {"status": "error", "error": error_message, "name": name}
            self._generation += 1
            return False

    async def _connect_stdio(self, server_id: str, name: str, command: str, args: List[str], env: Dict[str, str]) -> bool:
        """Connect to an MCP server via stdio transport."""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            from contextlib import AsyncExitStack

            server_params = StdioServerParameters(
                command=command,
                args=args,
                env={**os.environ, **env} if env else None,
            )

            stack = AsyncExitStack()
            transport = await stack.enter_async_context(stdio_client(server_params))
            read_stream, write_stream = transport
            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))

            await session.initialize()

            # Discover tools
            tools_result = await session.list_tools()
            tools = []
            for tool in tools_result.tools:
                tools.append({
                    "name": tool.name,
                    "description": tool.description or "",
                    # mcp <2.0 exposes ``inputSchema`` (camelCase); mcp 2.x
                    # renamed it to ``input_schema`` (snake_case). Accept both
                    # so a library bump doesn't silently surface empty schemas
                    # — which would otherwise make argument normalisation a
                    # no-op and let camelCase/snake_case mismatches through.
                    "input_schema": getattr(tool, "input_schema", None)
                    or getattr(tool, "inputSchema", None)
                    or {},
                })

            self._sessions[server_id] = session
            self._stacks[server_id] = stack
            self._tools[server_id] = tools
            # Extract identity hints from env vars (e.g. email address, API name)
            # so tool descriptions can distinguish between multiple instances of
            # the same MCP server (e.g. two email accounts).
            identity_hints = []
            for k, v in (env or {}).items():
                k_lower = k.lower()
                if any(x in k_lower for x in ['email_address', 'account', 'user', 'username']):
                    identity_hints.append(v)
            identity = ", ".join(identity_hints) if identity_hints else ""

            self._connections[server_id] = {
                "status": "connected",
                "name": name,
                "transport": "stdio",
                "tool_count": len(tools),
                "identity": identity,
            }

            logger.info(f"MCP server connected: {name} ({server_id}) - {len(tools)} tools via stdio")
            return True

        except ImportError:
            logger.warning("MCP package not installed. Install with: pip install mcp")
            self._connections[server_id] = {"status": "error", "error": "mcp package not installed", "name": name}
            return False

    async def _connect_sse(self, server_id: str, name: str, url: str, api_key: Optional[str] = None, custom_headers: Optional[Dict[str, str]] = None) -> bool:
        """Connect to an MCP server via SSE transport."""
        try:
            from mcp import ClientSession
            from mcp.client.sse import sse_client
            from contextlib import AsyncExitStack

            stack = AsyncExitStack()
            headers = dict(custom_headers) if custom_headers else {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                logger.debug(f"Using Bearer token auth for SSE server {name}")
            transport = await stack.enter_async_context(sse_client(url, headers=headers if headers else None))
            read_stream, write_stream = transport
            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))

            await session.initialize()

            # Discover tools
            tools_result = await session.list_tools()
            tools = []
            for tool in tools_result.tools:
                tools.append({
                    "name": tool.name,
                    "description": tool.description or "",
                    # mcp <2.0 exposes ``inputSchema`` (camelCase); mcp 2.x
                    # renamed it to ``input_schema`` (snake_case). Accept both
                    # so a library bump doesn't silently surface empty schemas
                    # — which would otherwise make argument normalisation a
                    # no-op and let camelCase/snake_case mismatches through.
                    "input_schema": getattr(tool, "input_schema", None)
                    or getattr(tool, "inputSchema", None)
                    or {},
                })

            self._sessions[server_id] = session
            self._stacks[server_id] = stack
            self._tools[server_id] = tools
            self._connections[server_id] = {
                "status": "connected",
                "name": name,
                "transport": "sse",
                "tool_count": len(tools),
            }

            logger.info(f"MCP server connected: {name} ({server_id}) - {len(tools)} tools via SSE{' (auth)' if api_key else ''}")
            return True

        except ImportError:
            logger.warning("MCP package not installed. Install with: pip install mcp")
            self._connections[server_id] = {"status": "error", "error": "mcp package not installed", "name": name}
            return False

    async def _connect_streamable_http(self, server_id: str, name: str, url: str, api_key: str = "", custom_headers: Optional[Dict[str, str]] = None) -> bool:
        """Connect to an MCP server via streamable HTTP transport.

        The streamable_http transport uses HTTP POST with SSE responses,
        which is the newer MCP transport spec (replaces raw SSE).
        """
        try:
            from mcp import ClientSession
            # Correct export name is `streamablehttp_client`; the historical
            # `streamable_http_client` spelling never existed and raised
            # ImportError, which surfaced as a misleading "requires mcp>=1.0".
            try:
                from mcp.client.streamable_http import streamablehttp_client as _streamable_client
            except ImportError:  # very old mcp revisions used the underscore spelling
                from mcp.client.streamable_http import streamable_http_client as _streamable_client
            from contextlib import AsyncExitStack
            import httpx

            # streamable_http's anyio task-group must be entered AND exited by
            # the SAME task, and that task must STAY ALIVE for the whole
            # session lifetime (mcp 2.x). A long-lived owner task opens the
            # stack, parks on an event while the session serves tool calls,
            # and closes the stack itself when disconnect signals it. Closing
            # from any other task raises "Attempted to exit cancel scope in a
            # different task" — and has been seen to cancel the calling
            # request handler ("No response returned" → INTERNAL_ERROR).
            headers = dict(custom_headers) if custom_headers else {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                logger.debug(f"Using Bearer token auth for streamable_http server {name}")
            # Explicit timeouts: httpx's 5s default for *every* phase (incl.
            # read) is far too tight for kubectl-heavy MCP servers — a single
            # `kubectl get pods --all-namespaces` over a big cluster can take
            # 6-10s to start streaming a response, and httpx then raises
            # ReadTimeout -> the stream closes -> MCP SDK surfaces it as
            # "-32000 Connection closed", which in call_tool fans out into a
            # 3-failure burst (1 timeout + 2 retries on the dead session).
            _read_timeout = float(os.getenv("MCP_READ_TIMEOUT_SECONDS", "60"))

            state: dict = {}
            opened = asyncio.Event()

            import anyio as _anyio

            async def _lifespan() -> None:
                """Whole session lifecycle inside one anyio task-group.

                Opening, parking and closing all happen in this single task:
                anyio cancel-scopes (mcp's transport task-group) may only be
                exited by the task that entered them. Disconnect cancels the
                surrounding task-group, the CancelledError lands HERE, and the
                `async with` chain unwinds in the correct task. Verified on
                mcp 2.2.0 + mcp 1.19: teardown is silent and cross-task tool
                calls keep working while parked.
                """
                try:
                    async with httpx.AsyncClient(
                        headers=headers or None,
                        timeout=httpx.Timeout(connect=5.0, write=10.0, pool=5.0, read=_read_timeout),
                    ) as _hc:
                        async with _streamable_client(url, http_client=_hc) as transport:
                            read_stream, write_stream = transport[0], transport[1]
                            async with ClientSession(read_stream, write_stream) as session:
                                await session.initialize()
                                state["session"] = session
                                opened.set()
                                await _anyio.sleep_forever()  # park until cancelled
                except BaseException as exc:
                    if "session" not in state:
                        state["error"] = exc
                        opened.set()

            async def _run_group():
                async with _anyio.create_task_group() as tg:
                    self._owner_tasks[server_id] = tg
                    tg.start_soon(_lifespan)
                    # Keep the group alive until disconnect cancels it.
                    await _anyio.sleep_forever()

            owner = asyncio.create_task(_run_group())
            self._owner_tasks_owner[server_id] = owner

            # Wait (bounded) for the session to be ready.
            for _ in range(int(_read_timeout * 4)):
                if "session" in state or "error" in state:
                    break
                await asyncio.sleep(0.25)
                if owner.done():
                    break
            if "error" in state:
                try:
                    await owner
                except BaseException:
                    pass
                raise state["error"]

            session = state.get("session")
            if session is None:
                if not owner.done():
                    owner.cancel()
                raise RuntimeError("MCP owner task produced no session")

            # Discover tools
            tools_result = await session.list_tools()
            tools = []
            for tool in tools_result.tools:
                tools.append({
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": getattr(tool, "input_schema", None)
                    or getattr(tool, "inputSchema", None)
                    or {},
                })

            self._sessions[server_id] = session
            self._tools[server_id] = tools
            self._connections[server_id] = {
                "status": "connected",
                "name": name,
                "transport": "streamable_http",
                "tool_count": len(tools),
            }

            logger.info(f"MCP server connected: {name} ({server_id}) - {len(tools)} tools via streamable_http{' (auth)' if api_key else ''}")
            return True

        except ImportError:
            logger.warning("mcp.client.streamable_http not available — install `mcp` >= 1.0")
            self._connections[server_id] = {
                "status": "error",
                "error": "streamable_http transport requires `mcp` >= 1.0",
                "name": name
            }
            return False

        except KeyError:
            # Fallback: streamable_http might not be exported yet in this mcp version
            logger.warning(f"streamable_http not found in mcp.client; try upgrading mcp package")
            self._connections[server_id] = {
                "status": "error",
                "error": "streamable_http transport not available — upgrade `mcp` package to >= 1.0",
                "name": name
            }
            return False

    async def disconnect_server(self, server_id: str):
        """Disconnect from an MCP server.

        streamable_http sessions live inside an anyio task-group (see
        `_connect_streamable_http`). Cancelling that group's scope drops
        every transport task and unwinds the `async with` chain in the
        same task that opened it — the only teardown mcp's cancel-scopes
        accept. The caller is shielded, so neither the cancellation nor
        teardown noise can leak into the request handler (which previously
        surfaced as "No response returned" → INTERNAL_ERROR, or a response
        body cut mid-stream → ERR_CONTENT_LENGTH_MISMATCH).
        """
        tg = self._owner_tasks.pop(server_id, None)
        owner = self._owner_tasks_owner.pop(server_id, None)

        if tg is not None:
            try:
                tg.cancel_scope.cancel()
            except BaseException:
                logger.debug(f"MCP {server_id}: cancel-scope cancel ignored error", exc_info=True)

        if owner is not None:
            try:
                await asyncio.wait_for(asyncio.shield(owner), timeout=15)
            except BaseException:
                logger.debug(f"MCP {server_id} group winding down in background")
                self._close_tasks.add(owner)
                owner.add_done_callback(self._close_tasks.discard)

        legacy = self._stacks.pop(server_id, None)  # stdio/SSE plain stacks
        if legacy is not None:
            async def _close_legacy() -> None:
                try:
                    await asyncio.wait_for(legacy.aclose(), timeout=15)
                except BaseException as e:
                    logger.debug(f"MCP {server_id} legacy teardown: {type(e).__name__} (ignored)")
            closer = asyncio.create_task(_close_legacy())
            try:
                await asyncio.shield(closer)
            except BaseException:
                self._close_tasks.add(closer)
                closer.add_done_callback(self._close_tasks.discard)

        self._sessions.pop(server_id, None)
        self._tools.pop(server_id, None)
        self._connections.pop(server_id, None)
        self._generation += 1
        logger.info(f"MCP server disconnected: {server_id}")

    async def disconnect_all(self):
        """Disconnect from all MCP servers."""
        ids = list(self._sessions.keys())
        for sid in ids:
            await self.disconnect_server(sid)

    async def connect_all_enabled(self):
        """Connect to all enabled MCP servers from the database."""
        from core.database import McpServer, SessionLocal

        db = SessionLocal()
        try:
            servers = db.query(McpServer).filter(McpServer.is_enabled == True).all()
            for srv in servers:
                args = json.loads(srv.args) if srv.args else []
                env = json.loads(srv.env) if srv.env else {}
                srv_headers = {}
                try:
                    srv_headers = json.loads(srv.mcp_headers) if srv.mcp_headers else {}
                except (json.JSONDecodeError, TypeError):
                    pass
                await self.connect_server(
                    server_id=srv.id,
                    name=srv.name,
                    transport=srv.transport,
                    command=srv.command,
                    args=args,
                    env=env,
                    url=srv.url,
                    api_key=srv.api_key,
                    headers=srv_headers,
                )
        finally:
            db.close()

    async def call_tool(self, qualified_name: str, arguments: Dict) -> Dict:
        """Call an MCP tool by its qualified name (mcp__{server_id}__{tool_name}).

        Returns a result dict compatible with agent_tools format.
        """
        parts = qualified_name.split("__", 2)
        if len(parts) != 3 or parts[0] != "mcp":
            return {"error": f"Invalid MCP tool name: {qualified_name}", "exit_code": 1}

        server_id = parts[1]
        tool_name = parts[2]

        session = self._sessions.get(server_id)
        if not session:
            # Try to re-establish the session for non-builtin servers (e.g.
            # remote streamable_http whose pod was restarted). Builtin
            # servers are handled below.
            if not self.is_builtin(server_id):
                logger.warning(
                    "MCP session missing for %s, attempting reconnect",
                    qualified_name,
                )
                reconnected = await self._reconnect_remote(server_id)
                if reconnected:
                    session = self._sessions.get(server_id)
            if not session:
                self._mark_failure(server_id)
                return {"error": f"MCP server not connected: {server_id}", "exit_code": 1}

        # Normalize model-generated aliases against the server-advertised
        # schema before validation/call. Some local models consistently emit
        # snake_case (resource_type) for camelCase MCP fields (resourceType).
        # This compatibility boundary is intentionally here—not in the UI or
        # prompt parser—so native calls, fenced calls and scheduled calls all
        # receive identical treatment.
        tool_schema = self._tool_schema(server_id, tool_name)
        try:
            arguments, renamed_arguments = _normalise_arguments_to_schema(
                arguments, tool_schema
            )
        except ValueError as exc:
            return {"error": str(exc), "exit_code": 1}
        if renamed_arguments:
            logger.info(
                "Normalized MCP argument name(s) for %s: %s",
                qualified_name,
                ", ".join(f"{old}->{new}" for old, new in renamed_arguments),
            )

        # Pre-validate required arguments against the server-advertised schema.
        # Some remote MCP servers (notably the k8s MCP server) crash with an
        # opaque JS TypeError ("Cannot read properties of undefined ...") when
        # a required argument is missing instead of returning a clean validation
        # error. Short-circuit here so the agent gets an actionable message.
        required_fields = self._required_fields(server_id, tool_name)
        missing = [
            f for f in required_fields
            if not isinstance(arguments, dict)
            or arguments.get(f) is None
            or (isinstance(arguments.get(f), str) and arguments.get(f) == "")
        ]
        if missing:
            hint = (
                f"Missing or empty required argument(s): {', '.join(missing)}. "
                f"Tool 'kubectl_get' requires a 'resourceType' (e.g. 'pods', 'deployments', 'services')."
                if tool_name == "kubectl_get" else
                f"Missing or empty required argument(s): {', '.join(missing)}."
            )
            return {"error": hint, "exit_code": 1}

        try:
            result = await self._do_call(session, tool_name, arguments)
            self._mark_success(server_id)
        except asyncio.TimeoutError:
            logger.error(
                "MCP tool %s timed out after %ds — marking server as error",
                qualified_name, MCP_CALL_TIMEOUT,
            )
            self._mark_failure(server_id, fatal=True)
            await self._invalidate_session(server_id)
            return {
                "error": (
                    f"MCP tool '{tool_name}' timed out after {MCP_CALL_TIMEOUT}s. "
                    f"The MCP server may have hung — try reconnecting."
                ),
                "exit_code": 1,
            }
        except Exception as e:
            # Some failures (anyio.EndOfStream, RuntimeError(""), McpError
            # with empty message) have str(e) == "" — fall back to repr and
            # the McpError.error payload so the log shows what actually went wrong.
            err_str = str(e) or repr(e)
            mcp_error_data = None
            try:
                from mcp.shared.exceptions import McpError
                if isinstance(e, McpError) and getattr(e, "error", None) is not None:
                    ed = e.error
                    mcp_error_data = {
                        "code": getattr(ed, "code", None),
                        "message": getattr(ed, "message", "") or "",
                        "data": getattr(ed, "data", None),
                    }
                    if mcp_error_data["message"] and not err_str:
                        err_str = mcp_error_data["message"]
            except Exception:
                pass
            # Streamable-HTTP sessions die when the remote service rotates
            # endpoints or load-balances to a node without session state.
            # The library surfaces these as RuntimeError, McpError, or an
            # anyio stream exception (ClosedResourceError / EndOfStream /
            # BrokenResourceError). anyio exceptions frequently have an
            # empty str(), so we match by class in addition to substring.
            is_session_dead = (
                isinstance(e, _STREAM_DEAD_EXCEPTIONS)
                or "Session terminated" in err_str
                or "session" in err_str.lower()
                or "not connected" in err_str.lower()
                or "closedresource" in type(e).__name__.lower()
            )

            if self.is_builtin(server_id):
                logger.warning(
                    "MCP call failed for %s, attempting reconnect: %s",
                    qualified_name, e,
                )
                reconnected = await self._reconnect_builtin(server_id)
                if reconnected:
                    session = self._sessions.get(server_id)
                    if session:
                        try:
                            result = await self._do_call(session, tool_name, arguments)
                            self._mark_success(server_id)
                            return result
                        except Exception as e2:
                            logger.error(
                                "MCP tool call failed after reconnect: %s: %s",
                                qualified_name, e2,
                            )
                            self._mark_failure(server_id, fatal=True)
                            return {"error": str(e2), "exit_code": 1}
                logger.error("MCP reconnect failed for %s", server_id)
                self._mark_failure(server_id, fatal=True)
                return {
                    "error": f"MCP server crashed and reconnect failed: {server_id}",
                    "exit_code": 1,
                }

            # Non-builtin (remote) server: try one reconnect on session-dead errors
            if is_session_dead:
                logger.warning(
                    "MCP session for %s looks dead (%s), attempting reconnect",
                    qualified_name, err_str,
                )
                reconnected = await self._reconnect_remote(server_id)
                if reconnected:
                    session = self._sessions.get(server_id)
                    if session:
                        try:
                            result = await self._do_call(session, tool_name, arguments)
                            self._mark_success(server_id)
                            return result
                        except Exception as e2:
                            logger.error(
                                "MCP tool call failed after reconnect: %s: %s",
                                qualified_name, e2,
                            )
                            self._mark_failure(server_id, fatal=True)
                            return {"error": str(e2), "exit_code": 1}
                # Reconnect failed
                self._mark_failure(server_id, fatal=True)
                return {
                    "error": (
                        f"MCP server '{server_id}' session is dead and reconnect failed: {err_str}"
                    ),
                    "exit_code": 1,
                }

            # Generic tool failure — server is healthy, tool just failed.
            # Surface the exception class, repr, and McpError payload so an
            # empty str(e) doesn't make the log unreadable.
            logger.error(
                "MCP tool call failed: %s: exc=%s repr=%r mcp_error=%s",
                qualified_name, type(e).__name__, e, mcp_error_data,
            )
            self._mark_failure(server_id)
            return {
                "error": (
                    f"MCP tool '{tool_name}' failed: {err_str or type(e).__name__}"
                    if err_str
                    else f"MCP tool '{tool_name}' raised {type(e).__name__}"
                ),
                "exit_code": 1,
                "error_type": type(e).__name__,
                "mcp_error": mcp_error_data,
            }

        return result

    def _required_fields(self, server_id: str, tool_name: str) -> List[str]:
        """Return the cached 'required' field list for an MCP tool.

        Empty list when the tool/schema isn't cached or has no required
        fields — callers simply skip validation in that case.
        """
        schema = self._tool_schema(server_id, tool_name)
        required = schema.get("required") if isinstance(schema, dict) else None
        return list(required) if required else []

    def _tool_schema(self, server_id: str, tool_name: str) -> Dict[str, Any]:
        """Return the cached input schema for one exact MCP tool name."""
        tools = self._tools.get(server_id) or []
        for tool in tools:
            if tool.get("name") == tool_name:
                schema = tool.get("input_schema") or {}
                return schema if isinstance(schema, dict) else {}
        return {}

    async def _do_call(self, session, tool_name: str, arguments: Dict) -> Dict:
        """Execute a single MCP tool call and return result dict.

        Wrapped in a timeout so a wedged streamable-HTTP session cannot
        deadlock the agent loop.
        """
        result = await asyncio.wait_for(
            session.call_tool(tool_name, arguments),
            timeout=MCP_CALL_TIMEOUT,
        )
        output_parts = []
        images = []
        for content in result.content:
            if hasattr(content, 'text'):
                output_parts.append(content.text)
            elif getattr(content, 'type', '') == 'image' and hasattr(content, 'data'):
                # Image content (e.g. Playwright screenshots)
                mime = getattr(content, 'mimeType', 'image/png')
                images.append({"data": content.data, "mimeType": mime})
                output_parts.append(f"[Screenshot captured ({mime})]")
            elif hasattr(content, 'data'):
                output_parts.append(str(content.data))

        output = "\n".join(output_parts)
        is_error = getattr(result, 'isError', False)

        result_dict = {
            "stdout": output if not is_error else "",
            "stderr": output if is_error else "",
            "exit_code": 1 if is_error else 0,
        }
        if images:
            result_dict["images"] = images
        return result_dict

    # ── Failure tracking & reconnect ─────────────────────────────────

    def _mark_failure(self, server_id: str, fatal: bool = False) -> None:
        """Record a tool call failure. When fatal or threshold exceeded,
        mark the connection status as "error" so the UI shows real state.
        """
        conn = self._connections.setdefault(server_id, {})
        fails = conn.get("consecutive_failures", 0) + 1
        conn["consecutive_failures"] = fails
        conn["last_failure_at"] = time.time()

        if fatal or fails >= MCP_FAILURE_THRESHOLD:
            conn["status"] = "error"
            conn["error"] = (
                f"tool failures: {fails}"
                if not fatal
                else f"fatal tool failure (count={fails})"
            )
            logger.warning(
                "MCP server %s marked as error (consecutive_failures=%d, fatal=%s)",
                server_id, fails, fatal,
            )
            # Auto-quarantine: tear down the session object so the next
            # call forces a reconnect (builds a fresh streamable-http
            # transport). Without this, a stale session can pile up
            # many failures (e.g. 11+) while never being invalidated.
            # Schedule the invalidation — _invalidate_session is async.
            try:
                conn["session_invalidated_at"] = time.time()
                if server_id in self._sessions:
                    asyncio.create_task(self._invalidate_session(server_id))
                    logger.info(
                        "MCP server %s: session scheduled for invalidation "
                        "after %d failures",
                        server_id, fails,
                    )
            except Exception:
                pass

    def _mark_success(self, server_id: str) -> None:
        """Reset failure counter on a successful call."""
        conn = self._connections.get(server_id)
        if conn and conn.get("consecutive_failures", 0) > 0:
            conn["consecutive_failures"] = 0
            conn.pop("last_failure_at", None)
            # Restore status to connected if it was in error state
            if conn.get("status") == "error":
                conn["status"] = "connected"

    async def _invalidate_session(self, server_id: str) -> None:
        """Tear down the session object without touching the server list.
        Used after a timeout to force a fresh session on next call.
        """
        stack = self._stacks.pop(server_id, None)
        if stack:
            try:
                await stack.aclose()
            except Exception as e:
                logger.warning(
                    "Error closing wedged MCP session %s: %s", server_id, e,
                )
        self._sessions.pop(server_id, None)
        self._tools.pop(server_id, None)

    async def _reconnect_remote(self, server_id: str) -> bool:
        """Reconnect a remote (SSE/streamable_http) MCP server using its
        stored DB configuration. Returns True on success.
        """
        try:
            from core.database import McpServer, SessionLocal
        except Exception as e:
            logger.error("Cannot import DB models for reconnect: %s", e)
            return False

        db = SessionLocal()
        try:
            srv = db.query(McpServer).filter(McpServer.id == server_id).first()
            if not srv:
                logger.error("Cannot reconnect %s — not found in DB", server_id)
                return False

            # Tear down existing session
            await self._invalidate_session(server_id)

            args = json.loads(srv.args) if srv.args else []
            env = json.loads(srv.env) if srv.env else {}
            headers_obj = {}
            try:
                headers_obj = json.loads(srv.mcp_headers) if srv.mcp_headers else {}
            except (json.JSONDecodeError, TypeError):
                headers_obj = {}

            ok = await self.connect_server(
                server_id=srv.id,
                name=srv.name,
                transport=srv.transport,
                command=srv.command,
                args=args,
                env=env,
                url=srv.url,
                api_key=srv.api_key,
                headers=headers_obj,
            )
            if ok:
                logger.info("Reconnected remote MCP server: %s", srv.name)
            return ok
        finally:
            db.close()

    async def _reconnect_builtin(self, server_id: str) -> bool:
        """Tear down and reconnect a crashed builtin MCP server."""
        import sys
        from src.builtin_mcp import _BUILTIN_SERVERS

        if server_id not in _BUILTIN_SERVERS:
            return False

        script_rel, name = _BUILTIN_SERVERS[server_id]
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_path = os.path.join(base_dir, script_rel)

        # Clean up old connection
        await self.disconnect_server(server_id)

        try:
            ok = await self.connect_server(
                server_id=server_id,
                name=name,
                transport="stdio",
                command=sys.executable,
                args=[script_path],
                env={"PYTHONPATH": base_dir},
            )
            if ok:
                logger.info(f"Reconnected builtin MCP server: {name}")
            return ok
        except Exception as e:
            logger.error(f"Failed to reconnect builtin MCP server {name}: {e}")
            return False

    def get_all_openai_schemas(self, disabled_map: Optional[Dict[str, set]] = None) -> List[Dict]:
        """Return all MCP tools in OpenAI function-calling format.

        Tool names are namespaced as mcp__{server_id}__{tool_name}.
        disabled_map: optional {server_id: set_of_disabled_tool_names} to filter out.
        """
        schemas = []
        for server_id, tools in self._tools.items():
            # Skip builtin Python servers — they use the code-block tool format
            # But include NPX-based builtins (like browser) which need function calling
            if self.is_builtin(server_id) and server_id != "builtin_browser":
                continue
            conn = self._connections.get(server_id, {})
            server_name = conn.get("name", server_id)
            disabled = (disabled_map or {}).get(server_id, set())

            identity = conn.get("identity", "")
            label = f"{server_name} ({identity})" if identity else server_name

            for tool in tools:
                if tool["name"] in disabled:
                    continue
                qualified = f"mcp__{server_id}__{tool['name']}"
                schema = {
                    "type": "function",
                    "function": {
                        "name": qualified,
                        "description": f"[MCP:{label}] {tool['description']}",
                        "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
                    },
                }
                schemas.append(schema)

        return schemas

    def get_all_tools(self, disabled_map: Optional[Dict[str, set]] = None) -> List[Dict]:
        """Return a flat list of all discovered tools with server info."""
        result = []
        for server_id, tools in self._tools.items():
            conn = self._connections.get(server_id, {})
            disabled = (disabled_map or {}).get(server_id, set())
            for tool in tools:
                result.append({
                    "server_id": server_id,
                    "server_name": conn.get("name", server_id),
                    "name": tool["name"],
                    "qualified_name": f"mcp__{server_id}__{tool['name']}",
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("input_schema", {"type": "object", "properties": {}}),
                    "is_disabled": tool["name"] in disabled,
                })
        return result

    def is_builtin(self, server_id: str) -> bool:
        """Check if a server is a built-in (auto-registered) server."""
        return server_id.startswith("builtin_") or server_id in {
            "image_gen",
            "memory",
            "email",
        }

    def get_server_status(self, server_id: str) -> Dict:
        """Get connection status for a server."""
        return self._connections.get(server_id, {"status": "disconnected"})

    def get_all_statuses(self) -> Dict[str, Dict]:
        """Get connection statuses for all servers."""
        return dict(self._connections)

    _cached_prompt_desc = None
    _cached_prompt_desc_key = None

    def get_tool_descriptions_for_prompt(self, disabled_map: Optional[Dict[str, set]] = None) -> str:
        """Generate text describing MCP tools for the agent system prompt. Cached."""
        cache_key = (
            frozenset((k, frozenset(v)) for k, v in (disabled_map or {}).items()),
            len(self._tools),
            self._generation,
        )
        if self._cached_prompt_desc is not None and self._cached_prompt_desc_key == cache_key:
            return self._cached_prompt_desc
        tools = self.get_all_tools(disabled_map)
        if not tools:
            return ""

        lines = ["\n\nYou also have access to external MCP tool servers. These tools are called via native function calling:"]
        by_server = {}
        for t in tools:
            # Skip builtin Python servers — they're already in the agent prompt
            # But include NPX-based builtins (like browser) which aren't hardcoded
            if self.is_builtin(t["server_id"]) and t["server_id"] != "builtin_browser":
                continue
            if t.get("is_disabled"):
                continue
            sn = t["server_name"]
            if sn not in by_server:
                by_server[sn] = []
            by_server[sn].append(t)

        if not by_server:
            return ""

        for server_name, server_tools in by_server.items():
            # Include identity (e.g. email address) if available
            sid = server_tools[0]["server_id"] if server_tools else ""
            identity = self._connections.get(sid, {}).get("identity", "")
            label = f"{server_name} ({identity})" if identity else server_name
            lines.append(f"\n**{label}:**")
            for t in server_tools:
                # Truncate long descriptions
                desc = t['description'][:120] + '...' if len(t['description']) > 120 else t['description']
                lines.append(f"  - {t['qualified_name']}: {desc}")

        result = "\n".join(lines)
        self._cached_prompt_desc = result
        self._cached_prompt_desc_key = cache_key
        return result