# Example Weather Adapter (external component)

Third-party-style adapter used to verify Mnemosyne interop.

- Speaks **REST only** (stdlib `urllib`); does not import `mnemosyne`.
- Registers a Component Contract, calls Discovery / UDM validate / PCIP.

```bash
# terminal A: start node
DSH_MEMORY_TOKEN=probe-token python -m mnemosyne.main --data-dir /tmp/mnemosyne-probe --port 8765

# terminal B: run probe
python examples/external-weather-adapter/external_weather_adapter.py http://127.0.0.1:8765 probe-token
```
