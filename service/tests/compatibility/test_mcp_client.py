# -*- coding: utf-8 -*-
"""MCP 兼容：JSON-RPC stdio 客户端对工具清单与调用的集成测。"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from mnemosyne.bootstrap import build_context
from mnemosyne.mcp.server import _run_jsonrpc_fallback
from mnemosyne.mcp.tools import TOOL_NAMES, tool_specs


class McpClientCompatTests(unittest.TestCase):
    def test_tool_parity_includes_retrieve_and_observe(self) -> None:
        names = {t["name"] for t in tool_specs()}
        for required in (
            "memory_health",
            "memory_retrieve",
            "memory_observe",
            "memory_context",
            "memory_forget",
        ):
            self.assertIn(required, names)
        self.assertEqual(set(TOOL_NAMES), names)

    def test_stdio_initialize_list_and_observe(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            ctx = build_context(
                data_dir=tmp,
                token="mcp-test",
                acquire_lock=False,
                auto_backup_on_migrate=False,
            )
            lines = [
                json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "memory_observe",
                            "arguments": {
                                "content": "MCP 写入一条观察",
                                "source_kind": "dialog",
                            },
                        },
                    }
                ),
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "tools/call",
                        "params": {
                            "name": "memory_retrieve",
                            "arguments": {"query": "观察", "force": True},
                        },
                    }
                ),
            ]
            stdin = io.StringIO("\n".join(lines) + "\n")
            buf = io.StringIO()
            with mock.patch("sys.stdin", stdin), redirect_stdout(buf):
                _run_jsonrpc_fallback(ctx.service)
            responses = [json.loads(x) for x in buf.getvalue().splitlines() if x.strip()]
            self.assertEqual(len(responses), 4)
            self.assertIn("serverInfo", responses[0]["result"])
            tool_names = {t["name"] for t in responses[1]["result"]["tools"]}
            self.assertIn("memory_retrieve", tool_names)
            observe_text = responses[2]["result"]["content"][0]["text"]
            observe = json.loads(observe_text)
            self.assertTrue(observe.get("id"))
            retrieve = json.loads(responses[3]["result"]["content"][0]["text"])
            self.assertIn("status", retrieve)
            ctx.db.close()


if __name__ == "__main__":
    unittest.main()
