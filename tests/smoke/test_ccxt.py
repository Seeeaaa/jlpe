"""Smoke test for ccxt.

ccxt is a unified crypto-exchange trading API. Its meaningful offline
check is instantiation plus API introspection: build exchange classes
(which is lazy and makes no network request), verify the unified `has`
capability map and `id`/`describe()` surface, and exercise a couple of
pure helper methods that do not require network access. A bare import
would not catch a broken transitive dependency (aiohttp, orjson,
coincurve, cryptography) unless that dependency fails at import time, so
the test reaches into the library's real code paths instead.

No network calls: load_markets / fetch_* are deliberately avoided so the
probe and folded smoke test stay deterministic and offline-safe in CI.
"""

import ccxt


def main() -> None:
    # Exchange construction is lazy; none of these hit the network.
    ex_binance = ccxt.binance()
    ex_kraken = ccxt.kraken()

    for ex in (ex_binance, ex_kraken):
        # The unified capability map is core to ccxt's cross-exchange API.
        assert isinstance(ex.has, dict), f"{ex.id}: missing 'has' capability map"
        assert "fetchTicker" in ex.has, f"{ex.id}: unified capability missing fetchTicker"
        desc = ex.describe()
        assert desc["id"] == ex.id, f"{ex.id}: describe() id mismatch: {desc['id']}"
        assert isinstance(desc.get("urls"), dict), f"{ex.id}: describe() missing urls"
        assert isinstance(desc.get("name"), str), f"{ex.id}: describe() missing name"
        print(f"ccxt: OK ({ex.id} instantiated offline, {len(ex.has)} capabilities)")

    # Parse a datetime string to a ms timestamp through ccxt's own parser,
    # exercising the yarl/requests-independent helper path.
    ts = ex_binance.parse8601("2026-01-02T03:04:05.000Z")
    assert ts == 1767323045000, f"unexpected parse8601 result: {ts}"
    print("ccxt: OK (parse8601)")


if __name__ == "__main__":
    main()