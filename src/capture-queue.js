/**
 * Durable auto-capture queue: JSONL on disk so crash before flush can replay.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import fs from 'node:fs';
import path from 'node:path';

export class CaptureQueue {
  /**
   * @param {{ filePath: string }} opts
   */
  constructor(opts) {
    this.filePath = opts.filePath;
    this._ensured = false;
  }

  ensure() {
    if (this._ensured) return;
    fs.mkdirSync(path.dirname(this.filePath), { recursive: true });
    if (!fs.existsSync(this.filePath)) {
      fs.writeFileSync(this.filePath, '', 'utf8');
    }
    this._ensured = true;
  }

  /** @param {Record<string, unknown>} item */
  enqueue(item) {
    this.ensure();
    const line = `${JSON.stringify({ ...item, queued_at: Date.now() })}\n`;
    fs.appendFileSync(this.filePath, line, 'utf8');
  }

  /** @returns {Record<string, unknown>[]} */
  peekAll() {
    this.ensure();
    const raw = fs.readFileSync(this.filePath, 'utf8');
    if (!raw.trim()) return [];
    const out = [];
    for (const line of raw.split('\n')) {
      if (!line.trim()) continue;
      try {
        out.push(JSON.parse(line));
      } catch {
        /* skip corrupt line */
      }
    }
    return out;
  }

  /** Replace queue with remaining items (after successful drains). */
  rewrite(items) {
    this.ensure();
    const body = items.map((it) => JSON.stringify(it)).join('\n');
    fs.writeFileSync(this.filePath, body ? `${body}\n` : '', 'utf8');
  }

  /**
   * Drain queue via async worker. Failed items stay.
   * @param {(item: Record<string, unknown>) => Promise<void>} worker
   */
  async drain(worker) {
    const items = this.peekAll();
    if (!items.length) return { drained: 0, remaining: 0 };
    const remain = [];
    let drained = 0;
    for (const item of items) {
      try {
        await worker(item);
        drained += 1;
      } catch {
        remain.push(item);
      }
    }
    this.rewrite(remain);
    return { drained, remaining: remain.length };
  }
}
