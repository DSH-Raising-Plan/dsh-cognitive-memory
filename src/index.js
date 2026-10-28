/**
 * dsh-cognitive-memory — DSH Host Adapter for external Memory Service.
 * Replaces in-process A-MEM with subprocess + REST/MCP tools.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

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
  searchToolSpec,
  taskToolSpec,
  updateToolSpec,
} from './tool-spec.js';

export const name = 'dsh-cognitive-memory';
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

export async function apply(ctx) {
  const defineTool = await loadDefineTool();
  // `config` is optional: headless Cordis profiles provide no config service.
  let rootConfig = {};
  try {
    rootConfig = (typeof ctx.get === 'function' ? ctx.get('config') : null) || {};
  } catch { rootConfig = {}; }
  const cfg = rootConfig['dsh-cognitive-memory'] || {};
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

  const disposers = tools.map((t) => ctx.tools.register(t));
  return () => {
    for (const d of disposers.reverse()) d?.();
    host.stop();
  };
}
