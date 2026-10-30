/**
 * Thin TS SDK for external agents (Foundation-stable paths).
 */
import { FOUNDATION_PATHS } from "./paths.js";

export { FOUNDATION_PATHS };

export class MnemosyneClient {
  static PATHS = FOUNDATION_PATHS;

  /**
   * @param {{ baseUrl: string, token: string, componentId?: string, timeoutMs?: number }} opts
   */
  constructor(opts) {
    this.baseUrl = String(opts.baseUrl || "").replace(/\/$/, "");
    this.token = String(opts.token || "");
    this.componentId = String(opts.componentId || "sdk.typescript");
    this.timeoutMs = Number(opts.timeoutMs || 15000);
  }

  async request(method, path, body) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
    try {
      const headers = {
        Accept: "application/json",
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.token}`,
        "X-Component-Id": this.componentId,
      };
      const res = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: ctrl.signal,
      });
      const text = await res.text();
      let data = null;
      try {
        data = text ? JSON.parse(text) : null;
      } catch {
        data = { raw: text };
      }
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

  health() {
    const [m, p] = FOUNDATION_PATHS.health;
    return this.request(m, p);
  }

  discovery() {
    const [m, p] = FOUNDATION_PATHS.discovery;
    return this.request(m, p);
  }

  observe(body) {
    const [m, p] = FOUNDATION_PATHS.observe;
    return this.request(m, p, body);
  }

  retrieve(body) {
    const [m, p] = FOUNDATION_PATHS.retrieve;
    return this.request(m, p, body);
  }

  search(body) {
    const [m, p] = FOUNDATION_PATHS.search;
    return this.request(m, p, body);
  }
}
