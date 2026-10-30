# Foundation Stability Report

Generated: `2026-10-30T06:00:25Z`  
Baseline: **`foundation-0.1.0`**  
Release: **P3 Foundation 1.0 — Stabilized**  
CI (#18): `plugin` / `service` / `foundation-stabilization` — **PASS**

## Results

| Check | OK |
| --- | --- |
| Unit tests | PASS |
| External interop probe (12) | PASS |
| CI foundation-stabilization | PASS |

## Versions

```json
{
  "baseline": "foundation-0.1.0",
  "schemas": {
    "component-contract": {
      "version": "1.0",
      "path": "component-contract/v1.json"
    },
    "universal-data-model": {
      "version": "1.0",
      "path": "universal-data-model/v1.json"
    },
    "events": {
      "version": "1.0",
      "path": "events/v1.json"
    },
    "pcip-exchange": {
      "version": "0.1-proposal",
      "path": "pcip/exchange-v1.json"
    }
  },
  "api": {
    "mnemosyne_api": "v1",
    "rest_prefix": "/api/v1"
  },
  "pcip": {
    "pcip_version": "0.1-proposal",
    "l3_default": "forbidden",
    "inbound_landing": "observation_only",
    "inbound_trust_default": "untrusted"
  },
  "sdks": {
    "mnemosyne-sdk": {
      "language": "python",
      "version": "0.1.0"
    },
    "mnemosyne-sdk-ts": {
      "language": "typescript",
      "version": "0.1.0"
    }
  },
  "compatibility": {
    "matrix_note": "See docs/FOUNDATION_COMPATIBILITY_MATRIX.md",
    "supported": [
      {
        "service": ">=0.3.4",
        "schema_baseline": "foundation-0.1.0",
        "sdk_python": "0.1.x",
        "sdk_ts": "0.1.x",
        "external_probe": "examples/external-weather-adapter@foundation"
      }
    ]
  },
  "frozen_acceptance": "docs/P3_FOUNDATION_ACCEPTANCE.md",
  "release": "1.0",
  "status": "Stabilized",
  "label": "P3 Foundation 1.0 — Stabilized",
  "stabilized_by": "PR #18",
  "next": "Production Security Assessment (not auto P3.2)",
  "compatibility_policy": "After Foundation 1.0 Stabilized, keep verified external REST contracts backward-compatible; production hardening may add capability or tighten remote policy but must not casually break Foundation Verified surfaces."
}
```

## Known limits

See [`FOUNDATION_KNOWN_LIMITS.md`](../FOUNDATION_KNOWN_LIMITS.md).

## Next

Production Security Assessment — do **not** auto-start P3.2.  
Constraints: [`ENGINEERING_CONSTRAINTS.md`](../ENGINEERING_CONSTRAINTS.md)  
Frozen roadmap: [`ROADMAP_FROZEN.md`](../ROADMAP_FROZEN.md)
