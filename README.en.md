# dsh-cognitive-memory

DeepSeek Harness **cognitive memory** plugin: starts an external **cognitive-memory** process and exposes search / context / observe / feedback tools over REST.

**Replaces** in-process A-MEM (Chroma). Aimed at DeepSeek Harness / **DSH desk-pet (丛雨)**.

> Community plugin. Not affiliated with DeepSeek.  
> Full Chinese docs (vision + install): [README.md](./README.md)

This repo is the **Host Adapter** (process lifecycle + DSH tools). The Python `MemoryService` usually lives in a monorepo at `services/cognitive-memory`.

## What it is for

Not “store more chat summaries”, but a base for a character with **continuous experience, stable persona room, evolving interests, habits, and relationship history** — so DSH can move from “prompt → model → reply” toward living-with-you companionship.

Memory alone does **not** create emotion, goals, or consciousness; those need separate modules. It *does* give them a consistent substrate.

## Advantages (summary)

1. **Shared life continuity** — observations → episodes (not conclusions without how they happened).  
2. **Evolving interests** — observe → relate → candidate → promote, with evidence — not hard-coded or one-shot chat.  
3. **Causal understanding** — keep links, time, and raw evidence so misunderstandings can be revised.  
4. **Proactive continuity** — upper layers can continue unfinished threads / interests instead of only answering.

| Dimension | Typical desk-pet AI | This design |
| --- | --- | --- |
| Memory | Summaries / prefs | Experience, evidence, links, change history |
| Persona | Fixed system prompt | Stable core + slowly shaped interests/habits |
| Interests | Per-turn guess | Long-horizon signals + feedback |
| Learning | Re-reason each turn | Propose → verify → consolidate → correct → forget |
| Consistency | Prompt only | Persona bounds + habits + history |

**Three bets worth building first:** perception↔memory↔decision↔behavior **closed loop**; **three persona layers** (core / experience / dynamic state); **traceable growth** (correct / explain / roll back / evaluate).

**Prefer:** episode memory + dynamic interest model + behavior feedback loop — before polishing “sounds human”.

## Layout (why)

```
src/index.js           # Cordis entry: start process, register tools
src/memory-process.js  # subprocess host
src/memory-client.js   # REST client
src/tool-spec.js       # schemas apart from execute
```

| Choice | Why |
| --- | --- |
| Separate subprocess | Crash isolation; upgrade/backup alone |
| Thin Host Adapter | One Python service for Harness + desk-pet bridge |
| Observe ≠ memory | Traceable evidence; promotable, correctable claims |
| Fast / slow paths | Chat stays light; Outbox/Tasks recover slow work |

## Install

```bash
pip install -e ../../services/cognitive-memory   # or your service checkout
dsh plugin --profile web add github:DSH-Raising-Plan/dsh-cognitive-memory#plugin/dsh
```

## Tools

| Tool | Purpose |
| --- | --- |
| `memory_health` | Health check |
| `memory_search` | Search |
| `memory_get` | Detail + evidence |
| `memory_context` | Fast context build |
| `memory_propose` / `memory_observe` | Candidate / raw observation |
| `memory_feedback` | Useful / incorrect |
| `memory_update` / `memory_forget` | Update / invalidate |
| `memory_task_status` | Background tasks |

## Config

```yaml
dsh-cognitive-memory:
  auto_start: true
  # service_root / data_dir / token / base_url
```

## License

AGPL-3.0-or-later
