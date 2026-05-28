# Source Policy

Primary structured source: AkShare public interfaces.

Official documentation references:

- A-share stock, minute, tick, news, popularity, and keyword interfaces: https://akshare.akfamily.xyz/data/stock/stock.html
- Index interfaces: https://akshare.akfamily.xyz/data/index/index.html

Rules:

1. Treat AkShare field names and availability as runtime facts. If an interface changes, record the error in `manifest.json.errors`.
2. Free news and sentiment sources may be stale, incomplete, or noisy. Use them as verification, not as sole proof.
3. A missing non-critical layer must set `data_status.<layer>` to `partial`, `unavailable`, or `error`.
4. `stock_trade` is critical. If it fails, return script status `error`.
5. Use web search only for event verification. Do not use web search to invent price or volume facts.
