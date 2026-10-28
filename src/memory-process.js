/**
 * Spawn / supervise the Python cognitive-memory subprocess.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function defaultServiceRoot() {
  const env = process.env.DSH_COGNITIVE_MEMORY_ROOT;
  if (env) return path.resolve(env);
  // monorepo: _dsh_plugins/dsh-cognitive-memory/src → ../../../services/cognitive-memory
  return path.resolve(__dirname, '../../../services/cognitive-memory');
}

function defaultDataDir() {
  if (process.env.DSH_MEMORY_DATA_DIR) return process.env.DSH_MEMORY_DATA_DIR;
  const local = process.env.LOCALAPPDATA || path.join(os.homedir(), '.local', 'share');
  return path.join(local, 'DSH', 'cognitive-memory');
}

function pythonBin() {
  return process.env.DSH_MEMORY_PYTHON
    || process.env.PYTHON
    || (process.platform === 'win32' ? 'python' : 'python3');
}

export class MemoryProcessHost {
  /**
   * @param {{ serviceRoot?: string, dataDir?: string, python?: string, token?: string }} [opts]
   */
  constructor(opts = {}) {
    this.serviceRoot = opts.serviceRoot || defaultServiceRoot();
    this.dataDir = opts.dataDir || defaultDataDir();
    this.python = opts.python || pythonBin();
    this.token = opts.token || process.env.DSH_MEMORY_TOKEN || '';
    this.child = null;
    this.baseUrl = '';
    this.ready = false;
  }

  serviceJsonPath() {
    return path.join(this.dataDir, 'runtime', 'service.json');
  }

  tokenPath() {
    return path.join(this.dataDir, 'runtime', 'token');
  }

  async start({ timeoutMs = 20000 } = {}) {
    if (this.child && !this.child.killed) return this.info();

    if (!this.token) {
      this.token = Buffer.from(cryptoGetRandom()).toString('base64url');
    }
    fs.mkdirSync(path.join(this.dataDir, 'runtime'), { recursive: true });

    const env = {
      ...process.env,
      DSH_MEMORY_TOKEN: this.token,
      DSH_MEMORY_DATA_DIR: this.dataDir,
      DSH_MEMORY_HOST: '127.0.0.1',
      DSH_MEMORY_PORT: '0',
      PYTHONPATH: [
        path.join(this.serviceRoot, 'src'),
        process.env.PYTHONPATH || '',
      ].filter(Boolean).join(path.delimiter),
    };

    const mainPy = path.join(this.serviceRoot, 'src', 'cognitive_memory', 'main.py');
    this.child = spawn(this.python, [mainPy, '--host', '127.0.0.1', '--port', '0', '--data-dir', this.dataDir, '--token', this.token], {
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    });

    this.child.stderr.on('data', (buf) => {
      const line = String(buf);
      if (process.env.DSH_MEMORY_DEBUG) process.stderr.write(`[cognitive-memory] ${line}`);
    });
    this.child.stdout.on('data', (buf) => {
      const text = String(buf);
      const m = text.match(/DSH_MEMORY_BOUND\s+(\S+)/);
      if (m) {
        this.baseUrl = `http://${m[1]}`;
        this.ready = true;
      }
    });
    this.child.on('exit', () => {
      this.ready = false;
      this.child = null;
    });

    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      if (this.ready && this.baseUrl) break;
      // also poll service.json
      try {
        const sj = this.serviceJsonPath();
        if (fs.existsSync(sj)) {
          const meta = JSON.parse(fs.readFileSync(sj, 'utf8'));
          if (meta.port) {
            this.baseUrl = `http://${meta.host || '127.0.0.1'}:${meta.port}`;
            this.ready = true;
            break;
          }
        }
      } catch { /* ignore */ }
      await sleep(100);
    }
    if (!this.ready) {
      this.stop();
      throw new Error('cognitive-memory subprocess failed to become ready');
    }
    // health check
    const { MemoryClient } = await import('./memory-client.js');
    const client = new MemoryClient({ baseUrl: this.baseUrl, token: this.token });
    await client.health();
    return this.info();
  }

  info() {
    return {
      ready: this.ready,
      baseUrl: this.baseUrl,
      token: this.token,
      dataDir: this.dataDir,
      pid: this.child?.pid || null,
    };
  }

  stop() {
    if (this.child && !this.child.killed) {
      try { this.child.kill(); } catch { /* ignore */ }
    }
    this.child = null;
    this.ready = false;
  }
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function cryptoGetRandom() {
  // eslint-disable-next-line no-undef
  return globalThis.crypto?.getRandomValues
    ? globalThis.crypto.getRandomValues(new Uint8Array(24))
    : Buffer.from(String(Date.now()) + Math.random());
}
