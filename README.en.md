# dsh-cognitive-memory

DeepSeek Harness **cognitive memory** plugin: starts the external [cognitive-memory](../../services/cognitive-memory) process and exposes search / context / observe / feedback tools over REST.

**Replaces** the in-process A-MEM (Chroma) approach.

Chinese docs: [README.md](./README.md)

## Install

Requires Python ≥ 3.11 and the service package:

```bash
pip install -e ../../services/cognitive-memory
dsh plugin --profile web add github:DSH-Raising-Plan/dsh-cognitive-memory#plugin/dsh
```

## Tools

| Tool | Purpose |
| --- | --- |
| `memory_health` | Health check |
| `memory_search` | Search memories |
| `memory_get` | Detail + evidence |
| `memory_context` | Build context (fast path) |
| `memory_propose` | Propose a candidate memory |
| `memory_observe` | Capture an observation |
| `memory_feedback` | Useful / incorrect feedback |
| `memory_update` / `memory_forget` | Update / invalidate |
| `memory_task_status` | Background task status |

## License

AGPL-3.0-or-later
