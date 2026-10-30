/**
 * dsh-mnemosyne — DSH Host Adapter for external Memory Service.
 * Replaces in-process A-MEM with subprocess + REST/MCP tools.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { MemoryClient } from './memory-client.js';
import { MemoryProcessHost } from './memory-process.js';
import {
  contextToolSpec,
  feedbackToolSpec,
  forgetToolSpec,
  getToolSpec,
  healthToolSpec,
  observeToolSpec,
  proposeToolSpec,
  retrieveToolSpec,
  searchToolSpec,
  taskToolSpec,
  updateToolSpec,
} from './tool-spec.js';
import { CaptureQueue } from './capture-queue.js';

export const name = 'dsh-mnemosyne';
export const inject = ['tools'];

export { MemoryClient } from './memory-client.js';
export { MemoryProcessHost } from './memory-process.js';

async function loadDefineTool() {
  try {
    const mod = await import('@deepseek-ai/dsh-tools');
    if (mod?.defineTool) return mod.defineTool;
  } catch { /* fall through */ }
  const override = process.env.DSH_TOOLS_PATH;
  if (override) {
    const mod = await import(pathToFileURL(override).href);
    if (mod?.defineTool) return mod.defineTool;
  }
  throw new Error('cannot resolve @deepseek-ai/dsh-tools (set DSH_TOOLS_PATH for local dev)');
}

/** Flatten one user/assistant message content into plain text. */
function contentText(content) {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content
      .map((part) => {
        if (typeof part === 'string') return part;
        if (part && typeof part === 'object') {
          const kind = String(part.type || '').toLowerCase();
          // Never persist hidden reasoning/thinking; only user-visible text.
          if (/reason|think/.test(kind)) return '';
          return part.text ?? part.content ?? '';
        }
        return '';
      })
      .filter(Boolean)
      .join('\n');
  }
  if (content && typeof content === 'object') {
    return String(content.text ?? content.content ?? '');
  }
  return '';
}

export async function apply(ctx) {
  const defineTool = await loadDefineTool();
  // `config` is optional: headless Cordis profiles provide no config service.
  let rootConfig = {};
  try {
    rootConfig = (typeof ctx.get === 'function' ? ctx.get('config') : null) || {};
  } catch { rootConfig = {}; }
  const cfg = rootConfig['dsh-mnemosyne']
    || rootConfig['dsh-cognitive-memory']
    || {};
  const autoStart = cfg.auto_start !== false;

  const host = new MemoryProcessHost({
    serviceRoot: cfg.service_root,
    dataDir: cfg.data_dir,
    python: cfg.python,
    token: cfg.token || process.env.DSH_MEMORY_TOKEN,
  });

  let client = null;

  async function ensureClient() {
    if (client) return client;
    if (cfg.base_url && (cfg.token || process.env.DSH_MEMORY_TOKEN)) {
      client = new MemoryClient({
        baseUrl: cfg.base_url,
        token: cfg.token || process.env.DSH_MEMORY_TOKEN,
      });
      return client;
    }
    if (!autoStart) throw new Error('memory service not configured (set base_url+token or auto_start)');
    const info = await host.start();
    client = new MemoryClient({ baseUrl: info.baseUrl, token: info.token });
    return client;
  }

  const tools = [
    defineTool({
      ...healthToolSpec(),
      async execute() {
        const c = await ensureClient();
        return c.health();
      },
    }),
    defineTool({
      ...searchToolSpec(),
      async execute(args) {
        const c = await ensureClient();
        return c.search({
          query: args.query,
          limit: args.limit ?? 10,
          types: args.types,
        });
      },
    }),
    defineTool({
      ...getToolSpec(),
      async execute(args) {
        const c = await ensureClient();
        return c.get(args.id, Boolean(args.include_evidence));
      },
    }),
    defineTool({
      ...contextToolSpec(),
      async execute(args) {
        const c = await ensureClient();
        return c.context({
          query: args.query,
          token_budget: args.token_budget,
        });
      },
    }),
    defineTool({
      ...retrieveToolSpec(),
      async execute(args) {
        const c = await ensureClient();
        return c.retrieve({
          query: args.query,
          force: Boolean(args.force),
          limit: args.limit ?? 8,
          mode: args.mode || 'current',
          session_id: args.session_id,
          token_budget: args.token_budget,
        });
      },
    }),
    defineTool({
      ...proposeToolSpec(),
      async execute(args) {
        const c = await ensureClient();
        return c.propose({
          content: args.content,
          type: args.type || 'semantic',
          source_ids: args.source_ids || [],
          status: args.status || 'candidate',
        });
      },
    }),
    defineTool({
      ...feedbackToolSpec(),
      async execute(args) {
        const c = await ensureClient();
        return c.feedback(args);
      },
    }),
    defineTool({
      ...updateToolSpec(),
      async execute(args) {
        const c = await ensureClient();
        const { id, ...rest } = args;
        return c.update(id, rest);
      },
    }),
    defineTool({
      ...forgetToolSpec(),
      async execute(args) {
        const c = await ensureClient();
        return c.forget(args.id, Boolean(args.hard));
      },
    }),
    defineTool({
      ...taskToolSpec(),
      async execute(args) {
        const c = await ensureClient();
        return c.task(args.id);
      },
    }),
    defineTool({
      ...observeToolSpec(),
      async execute(args) {
        const c = await ensureClient();
        return c.observe({
          content: args.content,
          source_kind: args.source_kind || 'dialog',
          correlation_id: args.correlation_id,
          producer: args.producer || 'dsh.agent',
        });
      },
    }),
  ];

  // Host-level capture: write every user/assistant message into the memory
  // service without asking the model to call memory_observe. The model may
  // still call memory_observe for an extra semantic note; this hook is the
  // baseline that guarantees the turn is not lost.
  let offSession = null;
  let offFlush = null;
  const pendingCaptures = new Set();
  const latestAssistant = new Map();
  const durableCapture = cfg.durable_capture !== false;
  const queuePath = cfg.capture_queue_path
    || path.join(host.dataDir, 'runtime', 'capture-queue.jsonl');
  const captureQueue = durableCapture ? new CaptureQueue({ filePath: queuePath }) : null;

  async function sendObserve(payload) {
    const c = await ensureClient();
    await c.observe(payload);
  }

  async function drainCaptureQueue() {
    if (!captureQueue) return;
    await captureQueue.drain(async (item) => {
      await sendObserve({
        content: item.content,
        source_kind: 'dialog',
        producer: 'dsh.host',
        correlation_id: item.correlation_id,
        occurred_at: item.occurred_at,
        metadata: item.metadata || {},
        idempotency_key: item.idempotency_key,
      });
    });
  }

  // Replay durable leftovers from previous crash (best-effort, non-blocking).
  if (captureQueue) {
    drainCaptureQueue().catch((err) => {
      if (process.env.DSH_MEMORY_DEBUG) {
        process.stderr.write(`[mnemosyne] capture replay: ${err}\n`);
      }
    });
  }

  if (cfg.auto_capture !== false && typeof ctx.on === 'function') {
    offFlush = ctx.on('session/flush', async () => {
      await Promise.allSettled([...pendingCaptures]);
      await drainCaptureQueue();
    });
    offSession = ctx.on('session/event', (session, event) => {
      try {
        const type = event?.type;
        if (type !== 'user/message' && type !== 'assistant/message' && type !== 'turn/end') return;
        const sessionId = String(session?.id || session?.header?.id || '');
        if (!sessionId) return;
        const data = event.data || {};

        const capture = (role, content, seq, time, source) => {
          const text = contentText(content).trim();
          if (!text) return;
          const occurredAt = new Date(Number(time) || Date.now()).toISOString();
          const metadata = {
            session_id: sessionId,
            event_seq: Number(seq) || 0,
            role,
            source: source ?? null,
          };
          const payload = {
            content: text,
            correlation_id: sessionId,
            occurred_at: occurredAt,
            metadata,
            idempotency_key: `dsh:${sessionId}:${Number(seq) || 0}`,
          };
          if (captureQueue) {
            try { captureQueue.enqueue(payload); } catch { /* ignore disk errors */ }
          }
          const task = (async () => {
            await sendObserve({
              content: payload.content,
              source_kind: 'dialog',
              producer: 'dsh.host',
              correlation_id: payload.correlation_id,
              occurred_at: payload.occurred_at,
              metadata: payload.metadata,
              idempotency_key: payload.idempotency_key,
            });
            // Successful send: drop matching durable rows on next drain (idempotent key).
            if (captureQueue) {
              const left = captureQueue.peekAll().filter(
                (it) => it.idempotency_key !== payload.idempotency_key,
              );
              captureQueue.rewrite(left);
            }
          })().catch((err) => {
            if (process.env.DSH_MEMORY_DEBUG) {
              process.stderr.write(`[mnemosyne] auto-capture skipped: ${err}\n`);
            }
          });
          pendingCaptures.add(task);
          task.finally(() => pendingCaptures.delete(task));
        };

        if (type === 'user/message') {
          if (!data || data.role !== 'user') return;
          capture('user', data.content, event.seq, event.time, data.source);
          return;
        }
        if (type === 'assistant/message') {
          const message = data.message;
          if (!message || message.role !== 'assistant') return;
          latestAssistant.set(sessionId, {
            content: message.content,
            seq: event.seq,
            time: event.time,
            source: message.source,
          });
          return;
        }
        const last = latestAssistant.get(sessionId);
        latestAssistant.delete(sessionId);
        if (last) {
          capture('assistant', last.content, last.seq, last.time, last.source);
        }
      } catch (err) {
        if (process.env.DSH_MEMORY_DEBUG) {
          process.stderr.write(`[mnemosyne] auto-capture ignored: ${err}\n`);
        }
      }
    });
  }

  const disposers = tools.map((t) => ctx.tools.register(t));
  if (offSession) disposers.push(offSession);
  if (offFlush) disposers.push(offFlush);
  return () => {
    for (const d of disposers.reverse()) d?.();
    host.stop();
  };
}
