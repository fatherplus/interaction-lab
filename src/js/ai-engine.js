/* ============================================================================
   Interaction Lab v2 — AI-Native Prompt, Code Interpolation & Spec Engine
   Designed to make even low-IQ / lightweight models output high-craft UI/UX
   ============================================================================ */
(function (global) {
  'use strict';

  const FRAMEWORK_NOTES = {
    vanilla: '输出格式：纯原生 HTML + CSS + JavaScript，零外部依赖，可直接嵌入现有页面运行。',
    react: '输出格式：请严格保留下方所有 CSS 变量数值、缓动曲线与状态机逻辑，转译为干净的 React 函数组件（支持 Tailwind CSS 或 CSS Module，动画仍使用上述精确贝塞尔曲线与 transform/opacity）。',
    vue: '输出格式：请严格保留下方所有 CSS 变量数值、缓动曲线与状态机逻辑，转译为 Vue 3 `<script setup>` 单文件组件（SFC）。',
  };

  function interpolateCode(snippet, tokens) {
    let out = snippet || '';
    if (!tokens) return out;
    Object.keys(tokens).forEach((key) => {
      const val = String(tokens[key]);
      const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const re = new RegExp(`(${escaped}\\s*:\\s*)([^;}\\n]+)`, 'g');
      out = out.replace(re, `$1${val}`);
    });
    return out;
  }

  function formatTokensBlock(tokens) {
    return Object.entries(tokens || {})
      .map(([k, v]) => `  ${k}: ${v};`)
      .join('\n');
  }

  function formatStateMachine(states) {
    return (states || [])
      .map((s, i) => `${i + 1}. [${s.state}] 触发: ${s.trigger} → 视觉: ${s.visual} (节奏: ${s.timing})`)
      .join('\n');
  }

  function buildPrompt(pattern, opts) {
    const mode = (opts && opts.mode) || 'strict';
    const framework = (opts && opts.framework) || 'vanilla';
    const tokens = Object.assign({}, pattern.tokens, (opts && opts.overrides) || {});
    const code = interpolateCode(pattern.code_snippet, tokens);

    if (mode === 'lite') {
      return [
        `# 交互实现规范：${pattern.name_cn} (${pattern.name_en})`,
        `- Pattern ID: \`${pattern.id}\``,
        `- 核心动作本质：${pattern.essence}`,
        `- ${FRAMEWORK_NOTES[framework] || FRAMEWORK_NOTES.vanilla}`,
        '',
        '## 精确数值契约（禁止随意替换为默认 0.5s ease）',
        '```css',
        ':root {',
        formatTokensBlock(tokens),
        '}',
        '```',
        '',
        '## 状态机转换',
        formatStateMachine(pattern.state_machine),
        '',
        '## 强制反模式禁区（DO NOT）',
        ...(pattern.do_not || []).map((d) => `- ✕ ${d}`),
      ].join('\n');
    }

    // Strict Blueprint Mode — specifically engineered to raise the floor of low-IQ / small models
    return [
      `你是一位精通微交互与前端动效工程的高级 UI 工程师。请严格按以下【防呆蓝图】实现「${pattern.name_cn}（${pattern.name_en}）」交互组件，禁止擅自简化状态机或修改核心物理参数。`,
      '',
      `## 1. 交互目标与本质`,
      `- 模式编号：\`${pattern.id}\``,
      `- 动作本质：${pattern.essence}`,
      `- ${FRAMEWORK_NOTES[framework] || FRAMEWORK_NOTES.vanilla}`,
      '',
      `## 2. 写死的数值契约（必须原样保留）`,
      '```css',
      formatTokensBlock(tokens),
      '```',
      '',
      `## 3. 完整状态机（缺一不可）`,
      formatStateMachine(pattern.state_machine),
      '',
      `## 4. 严格禁止事项（违反任意一条均视为不合格）`,
      ...(pattern.do_not || []).map((d, i) => `${i + 1}. 严禁：${d}`),
      '',
      `## 5. 已验证的最小参考实现骨架（请在此骨架上替换业务文案/颜色，不要从零瞎写曲线）`,
      '```html',
      code,
      '```',
      '',
      `## 6. 输出前强制自检清单（请逐项确认满足后再输出代码）`,
      ...(pattern.self_check || []).map((c) => `- [ ] ${c}`),
    ].join('\n');
  }

  function buildBundleSpec(patterns, mode) {
    if (!patterns || !patterns.length) {
      return '# 请先在画廊或实验台点击「+ 选入规范包」勾选至少 1 个交互模式。';
    }
    const header = [
      '# INTERACTION_SPEC.md — 项目级 AI 交互规范包',
      '',
      '> 本规范由 Interaction Lab 自动生成。AI 编码助手在实现以下 UI 交互时，必须严格遵守各模式的数值 Token、状态机与反模式禁区，并在生成代码前完成自检。',
      '',
      `## 全局基础动效铁律`,
      '1. 仅对 `transform`、`opacity`、`stroke-dashoffset` 与颜色做动画，禁止动画修改 `width / height / top / left / margin`。',
      '2. 任何数值滚动或动态计数必须启用 `font-variant-numeric: tabular-nums`。',
      '3. 所有组件必须尊重 `@media (prefers-reduced-motion: reduce)` 无障碍减弱动效降级。',
      '',
      `## 已选交互清单（共 ${patterns.length} 项）`,
      ...patterns.map((p, i) => `${i + 1}. **${p.name_cn}** (\`${p.id}\`) — ${p.essence}`),
      '',
      '---',
      '',
    ].join('\n');

    const sections = patterns.map((p) => buildPrompt(p, { mode: mode || 'strict', framework: 'vanilla' })).join('\n\n---\n\n');
    return header + sections;
  }

  function buildStandaloneHtml(pattern, overrides) {
    const tokens = Object.assign({}, pattern.tokens, overrides || {});
    const code = interpolateCode(pattern.code_snippet, tokens);
    return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>${pattern.name_cn} · ${pattern.name_en}</title>
  <style>
    body {
      margin: 0; min-height: 100vh; display: grid; place-items: center;
      background: ${pattern.default_surface === 'dark' ? '#16181c' : '#f6f3ec'};
      color: ${pattern.default_surface === 'dark' ? '#f3f1eb' : '#1e1a14'};
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", sans-serif;
    }
  </style>
</head>
<body>
${code}
</body>
</html>
`;
  }

  function renderBezierSVG(curve) {
    const b = (curve && curve.bezier) || [0.16, 1, 0.3, 1];
    const [x1, y1, x2, y2] = b;
    // Map [0..1] into x: [8..84], y: [64..12] (allowing y2 > 1 overshoot cleanly up to y=-10)
    const sx = (v) => (8 + v * 76).toFixed(1);
    const sy = (v) => (64 - v * 48).toFixed(1);
    const d = `M ${sx(0)} ${sy(0)} C ${sx(x1)} ${sy(y1)}, ${sx(x2)} ${sy(y2)}, ${sx(1)} ${sy(1)}`;
    const bezText = `cubic-bezier(${b.join(', ')})`;
    return `
      <svg viewBox="0 0 92 74" aria-hidden="true">
        <line x1="8" y1="64" x2="84" y2="64" stroke="var(--line)" stroke-width="1"/>
        <line x1="8" y1="16" x2="8" y2="64" stroke="var(--line)" stroke-width="1"/>
        <line x1="8" y1="64" x2="84" y2="16" stroke="var(--line-soft)" stroke-width="1" stroke-dasharray="3 3"/>
        <line x1="${sx(0)}" y1="${sy(0)}" x2="${sx(x1)}" y2="${sy(y1)}" stroke="var(--ink3)" stroke-width="1" opacity="0.55"/>
        <line x1="${sx(1)}" y1="${sy(1)}" x2="${sx(x2)}" y2="${sy(y2)}" stroke="var(--ink3)" stroke-width="1" opacity="0.55"/>
        <path d="${d}" fill="none" stroke="var(--accent)" stroke-width="2.4" stroke-linecap="round"/>
        <circle cx="${sx(x1)}" cy="${sy(y1)}" r="3.2" fill="var(--surface)" stroke="var(--accent)" stroke-width="1.8"/>
        <circle cx="${sx(x2)}" cy="${sy(y2)}" r="3.2" fill="var(--surface)" stroke="var(--accent)" stroke-width="1.8"/>
      </svg>
      <div class="curve-info">
        <strong>${(curve && curve.label) || 'Motion Curve'}</strong>
        <code>${bezText}</code>
      </div>
    `;
  }

  global.ILAIEngine = {
    interpolateCode,
    buildPrompt,
    buildBundleSpec,
    buildStandaloneHtml,
    renderBezierSVG,
  };
})(window);
