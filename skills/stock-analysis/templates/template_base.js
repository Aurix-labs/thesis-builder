/* =============================================================
   stock-analysis · template_base.js
   K 线图 + 饼图 ECharts 配置（lavender accent 主题）
   ============================================================= */

(function () {
  'use strict';

  // ⚠ 数据注入点：Phase 3 写 HTML 时把 __RAW_DATA_ARRAY__ 替换为实际数组
  const rawData = __RAW_DATA_ARRAY__;
  const pieData = __PIE_DATA_ARRAY__;

  // ============================================================
  //  色板（与 template_base.css 一致）
  // ============================================================
  const C = {
    canvas: '#010102',
    surface1: '#0c0d10',
    hairline: '#1f2128',
    ink: '#f7f8f8',
    inkMuted: '#d0d6e0',
    inkSubtle: '#8a8f98',
    accent: '#5e6ad2',
    accentHover: '#828fff',
    up: '#ff5a5f',   // 涨色（A 股惯例：红）
    down: '#27a644', // 跌色（A 股惯例：绿）
  };

  // ============================================================
  //  K 线图
  // ============================================================
  function renderKline() {
    const dom = document.getElementById('chart-kline-full');
    if (!dom || !rawData || rawData.length === 0) return;

    const chart = echarts.init(dom, null, { renderer: 'canvas' });

    const dates = rawData.map(r => r[0]);
    // OHLC 格式：[open, close, low, high]（ECharts candlestick 默认）
    const ohlc = rawData.map(r => [r[1], r[2], r[3], r[4]]);
    const volumes = rawData.map((r, i) => ({
      value: r[5],
      itemStyle: { color: r[2] >= r[1] ? C.up : C.down },
    }));

    // MA5 / MA20
    const ma = (n) => dates.map((_, i) => {
      if (i < n - 1) return '-';
      let sum = 0;
      for (let j = 0; j < n; j++) sum += rawData[i - j][2];
      return (sum / n).toFixed(2);
    });

    chart.setOption({
      backgroundColor: 'transparent',
      grid: [
        { left: 60, right: 32, top: 32, height: '60%' },
        { left: 60, right: 32, top: '72%', height: '20%' },
      ],
      xAxis: [
        { type: 'category', data: dates, axisLine: { lineStyle: { color: C.hairline } }, axisLabel: { color: C.inkSubtle, fontFamily: 'IBM Plex Mono' } },
        { type: 'category', gridIndex: 1, data: dates, axisLine: { lineStyle: { color: C.hairline } }, axisLabel: { show: false } },
      ],
      yAxis: [
        { type: 'value', scale: true, splitLine: { lineStyle: { color: C.hairline, type: 'dashed' } }, axisLabel: { color: C.inkSubtle, fontFamily: 'IBM Plex Mono' } },
        { type: 'value', gridIndex: 1, splitLine: { show: false }, axisLabel: { color: C.inkSubtle, fontFamily: 'IBM Plex Mono' } },
      ],
      tooltip: {
        trigger: 'axis',
        backgroundColor: C.surface1,
        borderColor: C.hairline,
        textStyle: { color: C.inkMuted, fontFamily: 'IBM Plex Mono' },
      },
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1], start: 70, end: 100 },
      ],
      series: [
        {
          type: 'candlestick', data: ohlc,
          itemStyle: { color: C.up, color0: C.down, borderColor: C.up, borderColor0: C.down },
        },
        { type: 'line', name: 'MA5', data: ma(5), smooth: true, showSymbol: false, lineStyle: { color: C.accent, width: 1 } },
        { type: 'line', name: 'MA20', data: ma(20), smooth: true, showSymbol: false, lineStyle: { color: C.accentHover, width: 1 } },
        { type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: volumes },
      ],
    });
    window.addEventListener('resize', () => chart.resize());
  }

  // ============================================================
  //  饼图（主营业务构成）
  // ============================================================
  function renderPie() {
    const dom = document.getElementById('chart-business-pie');
    if (!dom || !pieData || pieData.length === 0) return;

    const chart = echarts.init(dom, null, { renderer: 'canvas' });
    chart.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: C.surface1,
        borderColor: C.hairline,
        textStyle: { color: C.inkMuted, fontFamily: 'IBM Plex Mono' },
      },
      legend: { textStyle: { color: C.inkSubtle, fontFamily: 'Inter' }, bottom: 0 },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        data: pieData.map((d, i) => ({
          ...d,
          itemStyle: {
            color: i === 0 ? C.accent : (i === 1 ? C.accentHover : C.hairline),
            borderColor: C.canvas,
            borderWidth: 2,
          },
        })),
        label: { color: C.inkMuted, fontFamily: 'Inter' },
      }],
    });
    window.addEventListener('resize', () => chart.resize());
  }

  // ============================================================
  //  数据时效性提示
  // ============================================================
  function renderStaleWarn() {
    const meta = document.querySelector('meta[name="data-as-of"]');
    if (!meta) return;
    const asOf = new Date(meta.content);
    const days = Math.floor((Date.now() - asOf.getTime()) / 86400000);
    if (days > 7) {
      const warn = document.createElement('div');
      warn.className = 'data-stale-warn';
      warn.textContent = `数据已 ${days} 天未刷新，建议重新生成`;
      const banner = document.querySelector('.compliance-banner');
      if (banner) banner.after(warn);
    }
  }

  // ============================================================
  //  初始化
  // ============================================================
  document.addEventListener('DOMContentLoaded', () => {
    renderKline();
    renderPie();
    renderStaleWarn();
    if (window.MathJax && window.MathJax.typesetPromise) {
      window.MathJax.typesetPromise();
    }
  });
})();
