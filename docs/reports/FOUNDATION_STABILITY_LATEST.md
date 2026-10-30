# Foundation Stability Report

Generated: `2026-10-30T05:47:23Z`  
Baseline: **`foundation-0.1.0`**

## Results

| Check | OK |
| --- | --- |
| Unit tests | PASS |
| External interop probe (12) | PASS |

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
  "frozen_acceptance": "docs/P3_FOUNDATION_ACCEPTANCE.md"
}
```

## Known limits

See [`FOUNDATION_KNOWN_LIMITS.md`](../FOUNDATION_KNOWN_LIMITS.md).

## Notes

- Acceptance freeze: [`P3_FOUNDATION_ACCEPTANCE.md`](../P3_FOUNDATION_ACCEPTANCE.md)
- Stabilization plan: [`P3.1_FOUNDATION_STABILIZATION.md`](../P3.1_FOUNDATION_STABILIZATION.md)
- Compatibility matrix: [`FOUNDATION_COMPATIBILITY_MATRIX.md`](../FOUNDATION_COMPATIBILITY_MATRIX.md)
