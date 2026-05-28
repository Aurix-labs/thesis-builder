# after-market-review evals

These evals check routing, cache behavior, force refresh translation, and tick-trade evidence handling.

Manual smoke command:

```bash
cd /Users/zhangchao/workspace/thesis-builder/skills/after-market-review/scripts
python run_review.py 002594
```

Expected JSONL status:

- `reuse` when a report already exists for the trade date.
- `data_ready` when data was collected and the agent still needs to write `report.md`.
- `error` only when the critical `stock_trade` layer fails.

Run unit tests:

```bash
cd /Users/zhangchao/workspace/thesis-builder/skills/after-market-review/scripts
pytest tests -q
```
