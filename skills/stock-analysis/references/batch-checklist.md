# Phase 3 分批手写 + 校验清单

> Phase 3 开始时，agent 必读本文 + [html-spec.md](./html-spec.md)。
> **核心规则：** 不靠记范例，靠每批 grep diff。

---

## 工具分工（不可违反）

| 操作 | 工具 |
|------|------|
| 写入 HTML 内容 | **Write**（直接写 markup，无转义） |
| 精确局部修改 | **Edit** |
| 字节拼接 | **Bash `cat`** |
| **禁止** | Python f-string / Bash heredoc / `python -c` 拼字符串 |

每批 ≤300 行，独立 Write 调用。

---

## 范例引用方式（不依赖行号）

范例 [../examples/比亚迪_002594.html](../examples/比亚迪_002594.html) 中预置了 ANCHOR 注释：

| ANCHOR | 包含 |
|--------|------|
| `<!-- ANCHOR:head-style -->` | DOCTYPE + head + style 起点 |
| `<!-- ANCHOR:body-start -->` | body 起点 |
| `<!-- ANCHOR:nav -->` | top-nav 区块 |
| `<!-- ANCHOR:compliance-banner -->` | 合规 banner |
| `<!-- ANCHOR:hero -->` | hero 卡片 |
| `<!-- ANCHOR:conclusion-top -->` | 顶部结论卡片 |
| `<!-- ANCHOR:profile-grid -->` | 公司画像 grid-2 |
| `<!-- ANCHOR:financial-grid -->` | 财务/饼图 grid-2 |
| `<!-- ANCHOR:kline -->` | K 线图卡片 |
| `<!-- ANCHOR:step-0-mission -->` ~ `<!-- ANCHOR:step-8-tracking -->` | 各 Step 卡片 |
| `<!-- ANCHOR:conclusion-box -->` | // CONCLUSION 总结框 |
| `<!-- ANCHOR:footer -->` | footer |
| `<!-- ANCHOR:script -->` | script 区块 |

**用法：** `grep -n 'ANCHOR:nav' examples/比亚迪_002594.html` 找到行号 → `Read` 该行至下一个 ANCHOR 之前的范围。

---

## 标准 6 批方案（~900 行 HTML）

每批三步：**Read 范例 → Write → grep 校验**。

### Batch 0 · head + style

- **Read：** ANCHOR:head-style 至 ANCHOR:body-start 前
- **Write：** `_h_part0.html` 包含 `<!DOCTYPE html>` + `<html>` + `<head>` + `<style>`（完整复制 `templates/template_base.css` 内容）+ `</head>`
- **校验：**

      grep -c '<style>' _h_part0.html        # =1
      grep -c '</style>' _h_part0.html       # =1
      grep -o 'echarts\|MathJax' _h_part0.html  # 都存在
      grep -c '\-\-accent: *#5e6ad2' _h_part0.html  # =1（确认 lavender 已注入）

### Batch 1 · body + nav + compliance + hero + conclusion-top + profile-grid

- **Read：** ANCHOR:body-start 至 ANCHOR:financial-grid 前
- **Write：** `_h_part1.html`
- **校验：**

      grep -oc 'href="#' _h_part1.html       # =13（nav 13 个锚点）
      grep -c 'compliance-banner' _h_part1.html  # =1
      grep -c 'class="hero"' _h_part1.html   # =1
      grep -c 'hero-meta-item' _h_part1.html # =4
      grep -c 'sparkline' _h_part1.html      # ≥1

### Batch 2 · financial-grid + K线 + Step 0-3

- **Read：** ANCHOR:financial-grid 至 ANCHOR:step-4-elasticity 前
- **Write：** `_h_part2.html`
- **校验：**

      grep -c 'id="chart-kline-full"' _h_part2.html  # =1
      grep -c 'height: *480px' _h_part2.html         # =1
      grep -oE 'id="(mission|macro|chain|quality)"' _h_part2.html | sort -u | wc -l  # =4

### Batch 3 · Step 4-6

- **Read：** ANCHOR:step-4-elasticity 至 ANCHOR:step-7-compare 前
- **Write：** `_h_part3.html`
- **校验：**

      grep -oE 'id="(elasticity|risk|valuation)"' _h_part3.html | sort -u | wc -l  # =3
      grep -c 'class="score-seg' _h_part3.html       # ≥30（6 维 × 5 段）
      grep -c 'class="score-seg lit"' _h_part3.html  # 与该股各维度分数对应
      grep -c 'target-mid' _h_part3.html             # =1（中期目标价发光元素）

### Batch 4 · Step 7-8 + 总结框 + footer

- **Read：** ANCHOR:step-7-compare 至 ANCHOR:script 前
- **Write：** `_h_part4.html`
- **校验：**

      grep -oE 'id="(compare|tracking|conclusion)"' _h_part4.html | sort -u | wc -l  # =3
      grep -c '// CONCLUSION' _h_part4.html          # =1（mono eyebrow）
      grep -c '<strong>' _h_part4.html               # =0（footer 禁止 strong）
      grep -c 'color: *#FFD700\|gold' _h_part4.html  # =0（无金色残留）

### Batch 5 · script + 数据注入

- **Read：** ANCHOR:script 至文件末
- **Write：** `_h_part5.html`，复制 `templates/template_base.js` 内容，并把数据数组从 `data.json` 提取后直接嵌入到 `const rawData = [...]` 和 `const pieData = [...]` 位置
- **校验：**

      grep -c '__RAW_DATA' _h_part5.html         # =0（占位符清零）
      grep -c '__PIE_DATA' _h_part5.html         # =0
      grep -c 'const rawData' _h_part5.html      # =1
      grep -c 'const pieData' _h_part5.html      # =1
      grep -c '});' _h_part5.html                # ≥1（IIFE 闭合）
      grep -c '</script>' _h_part5.html          # =1

### 合并 + 终验

    cat _h_part0.html _h_part1.html _h_part2.html _h_part3.html _h_part4.html _h_part5.html > report.html
    bash skills/stock-analysis/scripts/verify_html.sh report.html

终验脚本输出全 PASS → 删 `_h_part*.html`。

---

## 失败处理

若任一批 grep 校验失败：
1. `grep -n 'ANCHOR:<对应>' examples/比亚迪_002594.html` 找范例对应区段
2. `Read` 范例对应行号区间
3. `Read` 自己写的批次文件对应区域
4. 对比差异，用 `Edit` 修正
5. 重跑该批 grep

不允许跳过校验进入下一批。
