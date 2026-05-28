# after-market-review Report Method

Write `report.md` from `data.json`. The report explains what happened today and which evidence supports that explanation. It must not produce trading instructions.

Required structure:

```markdown
# <股票名>（<代码>）<trade_date> 盘后复盘

## 一句话结论
2-3 句说明今日走势类型：市场带动、板块共振、个股消息驱动、盘口资金推动、情绪退潮，或证据不足。

## 今日走势拆解
- 集合竞价 / 开盘：
- 上午：
- 午后：
- 尾盘：

## 市场与板块背景
说明大盘环境、所属板块表现、个股相对强弱。

## 量价与盘口
结合分钟线和分笔大单；如果 `tick_trade` 不是 `ok` 或 `partial`，写“盘口大单证据缺失”。

## 事件与消息验证
分为已验证主因、可能催化、暂无证据支持。没有可靠事件时写“暂无明确事件证据”。

## 背后逻辑
写 1-3 条主逻辑。每条必须绑定至少一类证据：交易、板块、事件、盘口、情绪。

## 次日观察点
只写观察锚点：关键价位、量能阈值、板块延续、情绪退潮或继续发酵、公告新闻验证。
```

Forbidden wording:

- 建议买入
- 建议卖出
- 加仓
- 减仓
- 满仓
- 梭哈
- 必涨
- 必跌

Evidence rules:

1. `stock_trade` is mandatory. If it is missing, do not write the report.
2. `tick_trade` may explain big-order behavior only when `data_status.tick_trade` is `ok` or `partial`.
3. `event_context` must distinguish `verified_driver`, `possible_catalyst`, and `unsupported_rumor`.
4. `sentiment_context` can support short-term emotion, but it cannot be the only reason for the main conclusion.
5. If evidence conflicts, say so directly.
