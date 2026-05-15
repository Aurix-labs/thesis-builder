# data_inventory · 三角防务 300775 · 2026-05-15

## Block 覆盖矩阵

| Block | 行数 | 最新日期 | 健康度 |
|---|---|---|---|
| info | 9 | — | ⚠️ 数据极少 |
| kline_daily | 0 | — | ❌ 缺失，需 web 补 |
| business | 92 | 2025-12-31 | ✅ |
| financial_abstract | 80 | 20260331 | ✅ |
| top_holders | 0 | — | ❌ 缺失，需 web 补 |
| fund_flow | 121 | 2026-05-15 | ✅ |
| notice | 0 | — | ❌ 缺失，需 web 补 |
| news | 0 | — | ❌ 缺失，需 web 补 |
| research | 27 | 2025-10-28 | ✅ |
| recommend | 1 | — | ⚠️ 数据极少 |
| earnings_forecast | 0 | — | ❌ 缺失，需 web 补 |
| margin | 1 | — | ⚠️ 数据极少 |
| quote_snapshot | 0 | — | ❌ 缺失，需 web 补 |

## 顶层字段（v3 规范字段）

| 字段 | 行数 | 状态 |
|---|---|---|
| kline_daily | 0 | ❌ 缺失 |
| financials | 0 | ❌ 缺失 |
| business_segments | 0 | ❌ 缺失 |
| top_holders | 0 | ❌ 缺失 |
| news | 0 | ❌ 缺失 |

## Step 字段需求映射

| Step | 必需字段 | 状态 |
|---|---|---|
| Step 0.5 异常分析 | financial_abstract, fund_flow | ✅ |
| Step 1 宏观 | news | ❌ 缺 news |
| Step 2 产业链 | business, news | ❌ 缺 news |
| Step 3 公司质地 | financials, top_holders | ❌ 缺 financials, top_holders |
| Step 4 弹性 | financials, business | ❌ 缺 financials |
| Step 5 风险 | financials, notice | ❌ 缺 financials, notice |
| Step 6a+ 资金面 | fund_flow, margin | ✅ |
| Step 6c 研报验证 | research, recommend | ✅ |
| Step 7 对标 | financials | ❌ 缺 financials |
| Step 8 跟踪 | financial_abstract | ✅ |

## 推荐补全

- [ ] financials → web_fetch / 调研补 / 显式 [GAP]
- [ ] news → web_fetch / 调研补 / 显式 [GAP]
- [ ] notice → web_fetch / 调研补 / 显式 [GAP]
- [ ] top_holders → web_fetch / 调研补 / 显式 [GAP]
