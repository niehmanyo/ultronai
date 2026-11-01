"""Safe public DSH event -> observable 3D tool graph bridge.

Consumes the official SDK on_notification callback. Only tool name, opaque
per-turn call identifier and lifecycle are exported. Never forward arguments,
tool output, messages, reasoning text, IDs of users or runtime paths.
"""
from __future__ import annotations

import re
from typing import Any

SAFE_NAME = re.compile(r"^[a-zA-Z0-9_.:/-]{1,64}$")


def _event(notification: Any):
    """Return only durable, documented session event dictionary."""
    if getattr(notification, "method", None) != "session.event":
        return None
    payload = getattr(notification, "payload", None)
    if not isinstance(payload, dict):
        return None
    event = payload.get("event")
    if not isinstance(event, dict):
        return None
    return event


class ToolGraphObserver:
    def __init__(self, hub, *, turn: int, max_nodes: int = 18):
        self.hub = hub
        self.turn = turn
        self.max_nodes = max_nodes
        self.calls: dict[tuple[str, str], tuple[str, int]] = {}
        self.next_id = 0

    def __call__(self, notification: Any):
        event = _event(notification)
        if event is None:
            return
        kind, data = event.get("type"), event.get("data")
        payload = getattr(notification, "payload", {})
        session = payload.get("sessionId", "") if isinstance(payload, dict) else ""
        if not isinstance(session, str):
            return
        if not isinstance(data, dict):
            return
        if kind == "tool/call":
            call_id, name = data.get("callId"), data.get("name")
            if not isinstance(call_id, str) or not call_id or not isinstance(name, str):
                return
            key = (session, call_id)
            if self.next_id >= self.max_nodes or key in self.calls:
                return
            # Never send model-supplied tool args. Tool names may be custom;
            # display only simple bounded identifiers.
            display_name = name if SAFE_NAME.fullmatch(name) else "tool"
            self.next_id += 1
            self.calls[key] = (display_name, self.next_id)
            self.hub("tool_event", turn=self.turn, tool_id=self.next_id,
                     tool_name=display_name, tool_state="running", detail="Tool started")
        elif kind == "tool/result":
            message = data.get("message")
            source = message.get("source") if isinstance(message, dict) else None
            call_id = source.get("callId") if isinstance(source, dict) else None
            key = (session, call_id)
            if not isinstance(call_id, str) or key not in self.calls:
                return
            name, public_id = self.calls.pop(key)
            # The SDK's tool-result message can expose isError; never expose
            # message.content / raw error info to the dashboard.
            is_error = bool(message.get("isError", False))
            self.hub("tool_event", turn=self.turn, tool_id=public_id,
                     tool_name=name, tool_state="error" if is_error else "completed",
                     detail="Tool failed" if is_error else "Tool finished")

    def finish(self):
        """Unfinished calls must not be marked successful."""
        for _, (name, public_id) in tuple(self.calls.items()):
            self.hub("tool_event", turn=self.turn, tool_id=public_id,
                     tool_name=name, tool_state="unknown",
                     detail="Tool outcome not observed")
        self.calls.clear()
