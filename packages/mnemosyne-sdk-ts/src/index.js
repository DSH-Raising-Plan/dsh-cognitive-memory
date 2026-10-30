/**
 * Thin TS SDK — re-exports / mirrors Host MemoryClient without business logic.
 * Prefer depending on dsh-mnemosyne/client in DSH; this package is for external agents.
 */

export class MnemosyneClient {
  /**
   * @param {{ baseUrl: string, token: string, componentId?: string, timeoutMs?: number }} opts
   */
  constructor(opts) {
    this.baseUrl = String(opts.baseUrl || '').replace(/\/$/, '');
    this.token = String(opts.token || '');
    this.componentId = String(opts.componentId || 'sdk.typescript');
    this.timeoutMs = Number(opts.timeoutMs || 15000);
  }

  async request(method, path, body) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
    try {
      const headers = {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.token}`,
        'X-Component-Id': this.componentId,
      };
      const res = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: ctrl.signal,
      });
      const text = await res.text();
      let data = null;
      try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }
      if (!res.ok) {
        const err = new Error(data?.message || `HTTP ${res.status}`);
        err.status = res.status;
        err.data = data;
        throw err;
      }
      return data;
    } finally {
      clearTimeout(timer);
    }
  }

  health() { return this.request('GET', '/api/v1/health'); }
  discovery() { return this.request('GET', '/api/v1/discovery'); }
  observe(body) { return this.request('POST', '/api/v1/observations', body); }
  retrieve(body) { return this.request('POST', '/api/v1/retrieve', body); }
  search(body) { return this.request('POST', '/api/v1/memories/search', body); }
}
