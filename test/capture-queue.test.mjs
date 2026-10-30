import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { CaptureQueue } from '../src/capture-queue.js';

test('capture queue enqueue drain rewrite', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'mnemosyne-cq-'));
  const file = path.join(dir, 'q.jsonl');
  const q = new CaptureQueue({ filePath: file });
  q.enqueue({ idempotency_key: 'a', content: 'hello' });
  q.enqueue({ idempotency_key: 'b', content: 'world' });
  assert.equal(q.peekAll().length, 2);

  const seen = [];
  const result = await q.drain(async (item) => {
    seen.push(item.idempotency_key);
    if (item.idempotency_key === 'b') throw new Error('fail b');
  });
  assert.equal(result.drained, 1);
  assert.equal(result.remaining, 1);
  assert.deepEqual(seen, ['a', 'b']);
  assert.equal(q.peekAll()[0].idempotency_key, 'b');
});
