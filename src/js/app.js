/* ============================================================================
   Interaction Lab v4 — Pure High-Tech Interactive Showcase Controller
   Focused on Visual Showcase + 1:1 Lightbox + AI CLI/Skill Integration
   ============================================================================ */
(function () {
  'use strict';

  const DRIVE_LABELS = {
    press: '按压',
    click: '点击',
    drag: '拖拽',
    hover: '悬停',
    pointer: '指针跟随',
    scroll: '滚动',
    time: '循环节奏',
    state: '状态切换',
  };

  const FLAGSHIP_LABELS = {
    'coverflow-depth-stage': 'ATLAS 3D 透视',
    'glass-drag-bookshelf': '毛玻璃书架拖拽',
    'editorial-image-hero': '松林大图主视觉',
    'rotary-climate-dial': '31 刻度温控旋钮',
    'perspective-tilt-glare': '拉丝金 3D 倾斜',
  };

  const state = {
    categories: [],
    patterns: [],
    catMap: {},
    featured: [],
    heroIdx: 0,
    heroSpecimenTheme: 'light',
    activeCategory: 'all',
    theme: 'dark',
    lightboxPattern: null,
    lightboxTheme: 'dark',
    lightboxRO: null,
    galleryIO: null,
    galleryRO: null,
    unmountTimers: new Map(),
    cmdIdx: 0,
    cmdMatches: [],
  };

  const $ = (id) => document.getElementById(id);
  const tel = window.ILTelemetry || { track() {}, trackInteract() {} };
  const ai = window.ILAIEngine;

  let toastTimer = null;
  function showToast(msg) {
    const el = $('toast');
    el.textContent = msg;
    el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('show'), 2200);
  }

  async function copyText(text, successMsg) {
    try {
      await navigator.clipboard.writeText(text);
      showToast(successMsg || '已复制到剪贴板');
      return true;
    } catch (_) {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand('copy');
        showToast(successMsg || '已复制到剪贴板');
        return true;
      } catch (e) {
        showToast('复制失败，请手动复制');
        return false;
      } finally {
        ta.remove();
      }
    }
  }

  function postToIframe(iframe, msg) {
    if (!iframe || !iframe.contentWindow) return;
    try { iframe.contentWindow.postMessage(msg, '*'); } catch (_) {}
  }

  function broadcastAllIframes(msg) {
    document.querySelectorAll('iframe').forEach((ifr) => postToIframe(ifr, msg));
  }

  function specimenUrl(p, themeOverride) {
    const t = themeOverride || state.theme;
    return `${p.specimen_url}?theme=${encodeURIComponent(t)}`;
  }

  function fitScaler(containerEl, scalerEl, logicalSize) {
    const [lw, lh] = logicalSize || [640, 380];
    const cw = Math.max(120, containerEl.clientWidth);
    const ch = Math.max(100, containerEl.clientHeight);
    const scale = Math.min(cw / lw, ch / lh);
    scalerEl.style.width = `${lw}px`;
    scalerEl.style.height = `${lh}px`;
    scalerEl.style.transform = `translate(-50%, -50%) scale(${scale.toFixed(4)})`;
  }

  /* ---------- THEME ---------- */
  function loadPrefs() {
    try {
      const saved = localStorage.getItem('il_v4_theme');
      if (saved === 'dark' || saved === 'light') state.theme = saved;
    } catch (_) {}
    applyTheme();
  }

  function applyTheme() {
    document.documentElement.dataset.theme = state.theme;
    $('themeLabel').textContent = state.theme === 'dark' ? '暖白' : '暗室';
    try { localStorage.setItem('il_v4_theme', state.theme); } catch (_) {}
    broadcastAllIframes({ type: 'set-theme', theme: state.theme });
    state.heroSpecimenTheme = state.theme;
    state.lightboxTheme = state.theme;
  }

  /* ---------- HERO FLAGSHIP SHOWCASE ---------- */
  let heroRO = null;

  function renderHeroSwitcher() {
    const box = $('heroSwitcher');
    box.innerHTML = state.featured.map((p, i) => `
      <button type="button" class="hero-tab${i === state.heroIdx ? ' on' : ''}" data-hidx="${i}">
        ${FLAGSHIP_LABELS[p.id] || p.name_cn}
      </button>
    `).join('');
    box.querySelectorAll('.hero-tab').forEach((b) => {
      b.onclick = () => selectHero(Number(b.dataset.hidx));
    });
  }

  function selectHero(idx) {
    if (!state.featured.length) return;
    state.heroIdx = (idx + state.featured.length) % state.featured.length;
    const p = state.featured[state.heroIdx];
    renderHeroSwitcher();

    state.heroSpecimenTheme = p.id === 'coverflow-depth-stage' ? 'light' : state.theme;

    const frame = $('heroStageFrame');
    const ifr = $('heroIframe');
    const [lw, lh] = p.logical_size || [780, 460];
    ifr.style.width = `${lw}px`;
    ifr.style.height = `${lh}px`;

    const applyHeroScale = () => {
      const cw = Math.max(200, frame.clientWidth);
      const ch = Math.max(200, frame.clientHeight);
      const sc = Math.min(cw / lw, ch / lh);
      ifr.style.transform = `translate(-50%, -50%) scale(${sc.toFixed(4)})`;
    };
    applyHeroScale();
    if (heroRO) heroRO.disconnect();
    heroRO = new ResizeObserver(applyHeroScale);
    heroRO.observe(frame);

    ifr.src = specimenUrl(p, state.heroSpecimenTheme);

    $('heroIdx').textContent = `0${state.heroIdx + 1} / 0${state.featured.length} · FLAGSHIP`;
    $('heroTitle').textContent = p.name_cn;
    $('heroEn').textContent = p.name_en;
    $('heroEssence').textContent = p.essence;
    $('heroCliText').textContent = `ilab get ${p.id}`;
  }

  /* ---------- TOPBAR CATEGORIES ---------- */
  function renderTopCategories() {
    const nav = $('topCats');
    const pills = [
      `<button type="button" class="top-cat-pill${state.activeCategory === 'all' ? ' on' : ''}" data-cat="all">全部 <b>${state.patterns.length}</b></button>`,
    ];
    state.categories.forEach((c) => {
      const cnt = state.patterns.filter((p) => p.category === c.id).length;
      pills.push(
        `<button type="button" class="top-cat-pill${state.activeCategory === c.id ? ' on' : ''}" data-cat="${c.id}">${c.name_cn} <b>${cnt}</b></button>`
      );
    });
    nav.innerHTML = pills.join('');
    nav.querySelectorAll('.top-cat-pill').forEach((b) => {
      b.onclick = () => {
        state.activeCategory = b.dataset.cat;
        renderTopCategories();
        renderGallery();
        // Scroll smoothly down past Hero when picking a specific category
        if (state.activeCategory !== 'all') {
          $('viewTitle').scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        tel.track('filter_change', { category: state.activeCategory });
      };
    });
  }

  /* ---------- 2-COLUMN LIVE GALLERY WITH VIEWPORT IFRAME POOL ---------- */
  function teardownGalleryPool() {
    if (state.galleryIO) { state.galleryIO.disconnect(); state.galleryIO = null; }
    if (state.galleryRO) { state.galleryRO.disconnect(); state.galleryRO = null; }
    state.unmountTimers.forEach((t) => clearTimeout(t));
    state.unmountTimers.clear();
  }

  function mountCardIframe(cardEl, p) {
    if (cardEl.querySelector('iframe')) return;
    const scaler = cardEl.querySelector('.pcard-scaler');
    const ph = cardEl.querySelector('.pcard-placeholder');
    const ifr = document.createElement('iframe');
    ifr.title = `${p.name_cn} 实时标本`;
    const initTheme = p.id === 'coverflow-depth-stage' ? 'light' : state.theme;
    ifr.src = specimenUrl(p, initTheme);
    ifr.onload = () => { if (ph) ph.hidden = true; };
    scaler.appendChild(ifr);
  }

  function unmountCardIframe(cardEl) {
    const ifr = cardEl.querySelector('iframe');
    if (ifr) ifr.remove();
    const ph = cardEl.querySelector('.pcard-placeholder');
    if (ph) ph.hidden = false;
  }

  function renderGallery() {
    teardownGalleryPool();
    const list = state.activeCategory === 'all'
      ? state.patterns
      : state.patterns.filter((p) => p.category === state.activeCategory);

    const cat = state.catMap[state.activeCategory];
    $('viewTitle').textContent = cat ? `${cat.num} · ${cat.name_cn}` : '全部高保真交互';
    $('viewCount').textContent = String(list.length);
    $('viewSummary').textContent = cat
      ? `${cat.summary}（CLI 查询：ilab list ${cat.id}）`
      : '48 个可交互标本，均按精确测量参数独立重写实现。点击卡片直接操作，或让 AI 用 ilab CLI 自动检索。';

    const grid = $('galleryGrid');
    grid.innerHTML = '';

    const pById = {};
    list.forEach((p) => { pById[p.id] = p; });

    state.galleryRO = new ResizeObserver((entries) => {
      entries.forEach((entry) => {
        const stage = entry.target;
        const p = pById[stage.dataset.pid];
        const scaler = stage.querySelector('.pcard-scaler');
        if (p && scaler) fitScaler(stage, scaler, p.logical_size);
      });
    });

    state.galleryIO = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        const card = entry.target;
        const pid = card.dataset.id;
        const p = pById[pid];
        if (!p) return;
        if (entry.isIntersecting) {
          if (state.unmountTimers.has(pid)) {
            clearTimeout(state.unmountTimers.get(pid));
            state.unmountTimers.delete(pid);
          }
          mountCardIframe(card, p);
        } else {
          if (!state.unmountTimers.has(pid)) {
            const tid = setTimeout(() => {
              state.unmountTimers.delete(pid);
              unmountCardIframe(card);
            }, 900);
            state.unmountTimers.set(pid, tid);
          }
        }
      });
    }, { rootMargin: '260px 0px' });

    const frag = document.createDocumentFragment();
    list.forEach((p) => {
      const cInfo = state.catMap[p.category];
      const card = document.createElement('article');
      card.className = 'pcard';
      card.dataset.id = p.id;
      card.innerHTML = `
        <div class="pcard-inner">
          <div class="pcard-stage" data-pid="${p.id}">
            <div class="pcard-placeholder">LOADING · ${p.name_en.toUpperCase()}</div>
            <div class="pcard-scaler"></div>
            <span class="pcard-cat-chip">${cInfo ? cInfo.name_cn : p.category}</span>
          </div>
          <div class="pcard-body">
            <div class="pcard-head">
              <div class="pcard-titles">
                <strong>${p.name_cn}</strong>
                <span>${p.name_en}</span>
              </div>
              <button type="button" class="cli-chip" data-cli="${p.id}" title="点击复制 Agent CLI 命令">ilab get ${p.id}</button>
            </div>
            <p class="pcard-essence">${p.essence}</p>
            <div class="pcard-foot">
              <div class="pcard-tags">
                ${p.drive.slice(0, 2).map((d) => `<span class="micro-tag">${DRIVE_LABELS[d] || d}</span>`).join('')}
              </div>
              <div class="pcard-actions">
                <button type="button" class="btn-outline" data-zoom="${p.id}">放大 1:1</button>
                <button type="button" class="btn-soft" data-copy="${p.id}">复制规范</button>
              </div>
            </div>
          </div>
        </div>
      `;

      card.addEventListener('pointermove', (e) => {
        const r = card.getBoundingClientRect();
        card.style.setProperty('--mx', `${(e.clientX - r.left).toFixed(1)}px`);
        card.style.setProperty('--my', `${(e.clientY - r.top).toFixed(1)}px`);
      }, { passive: true });

      card.querySelector('[data-cli]').onclick = () => {
        copyText(`ilab get ${p.id}`, `已复制：ilab get ${p.id}`);
        tel.track('copy_prompt', { pattern_id: p.id, category: p.category, props: { prompt_mode: 'cli_cmd' } });
      };

      card.querySelector('[data-zoom]').onclick = () => openLightbox(p.id, 'gallery');

      card.querySelector('[data-copy]').onclick = () => {
        copyText(ai.buildPrompt(p, { mode: 'strict', framework: 'vanilla' }), `已复制「${p.name_cn}」AI 防呆规范`);
        tel.track('copy_prompt', { pattern_id: p.id, category: p.category, props: { prompt_mode: 'strict', surface: 'gallery' } });
      };

      const stageEl = card.querySelector('.pcard-stage');
      const scalerEl = card.querySelector('.pcard-scaler');
      fitScaler(stageEl, scalerEl, p.logical_size);
      state.galleryRO.observe(stageEl);
      state.galleryIO.observe(card);
      frag.appendChild(card);
    });
    grid.appendChild(frag);
  }

  /* ---------- FRAMELESS 1:1 LIGHTBOX ---------- */
  function openLightbox(patternId, fromSource) {
    const p = state.patterns.find((x) => x.id === patternId);
    if (!p) return;
    state.lightboxPattern = p;
    state.lightboxTheme = p.id === 'coverflow-depth-stage' ? 'light' : state.theme;

    $('lbTitle').textContent = p.name_cn;
    $('lbEn').textContent = p.name_en;
    $('lbCliChip').textContent = `ilab get ${p.id}`;
    $('lightboxModal').hidden = false;

    const stage = $('lbStage');
    const scaler = $('lbScaler');
    const ifr = $('lbIframe');
    const [lw, lh] = p.logical_size || [760, 440];
    if (state.lightboxRO) state.lightboxRO.disconnect();
    const fitLb = () => fitScaler(stage, scaler, [lw, lh]);
    fitLb();
    state.lightboxRO = new ResizeObserver(fitLb);
    state.lightboxRO.observe(stage);

    ifr.src = specimenUrl(p, state.lightboxTheme);
    tel.track('specimen_open', { pattern_id: p.id, category: p.category, props: { from: fromSource || 'gallery' } });
  }

  function closeLightbox() {
    if (state.lightboxRO) { state.lightboxRO.disconnect(); state.lightboxRO = null; }
    $('lbIframe').src = 'about:blank';
    state.lightboxPattern = null;
    $('lightboxModal').hidden = true;
  }

  /* ---------- AI CLI / SKILL SETUP MODAL ---------- */
  function openAiModal() {
    const origin = location.origin;
    $('cliInstallCmd').textContent =
      `mkdir -p ~/.local/bin && curl -fsSL ${origin}/cli/ilab -o ~/.local/bin/ilab && chmod +x ~/.local/bin/ilab`;
    $('skillInstallCmd').textContent =
      `mkdir -p ~/.agents/skills/interaction-lab && curl -fsSL ${origin}/SKILL.md -o ~/.agents/skills/interaction-lab/SKILL.md`;
    $('aiModal').hidden = false;
  }
  function closeAiModal() { $('aiModal').hidden = true; }

  /* ---------- ⌘K COMMAND PALETTE ---------- */
  let searchTrackTimer = null;

  function scorePattern(p, q) {
    const query = q.trim().toLowerCase();
    if (!query) return 1;
    const fields = [
      { txt: p.name_cn, w: 10 },
      { txt: p.name_en, w: 9 },
      { txt: p.id, w: 9 },
      { txt: (p.symptoms || []).join(' '), w: 8 },
      { txt: p.essence, w: 5 },
      { txt: (p.drive || []).map((d) => DRIVE_LABELS[d] || d).join(' '), w: 4 },
    ];
    let score = 0;
    for (const f of fields) {
      if (f.txt.toLowerCase().includes(query)) score += f.w;
    }
    return score;
  }

  function renderCmdResults(q) {
    const matches = state.patterns
      .map((p) => ({ p, s: scorePattern(p, q) }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, 12)
      .map((x) => x.p);

    state.cmdMatches = matches;
    state.cmdIdx = 0;
    const box = $('cmdResults');

    if (!matches.length) {
      box.innerHTML = `<div class="cmd-empty">没有找到与「${q}」相关的交互（已记入搜索缺口日志）。</div>`;
    } else {
      box.innerHTML = matches.map((p, i) => {
        const c = state.catMap[p.category];
        return `
          <button type="button" class="cmd-item${i === 0 ? ' active' : ''}" data-cmd-id="${p.id}">
            <span class="cmd-item-l">
              <strong>${p.name_cn} · ${p.name_en}</strong>
              <small>${p.essence}</small>
            </span>
            <span class="cmd-item-r">${c ? c.name_cn : ''}</span>
          </button>
        `;
      }).join('');
      box.querySelectorAll('.cmd-item').forEach((b) => {
        b.onclick = () => { closeCmd(); openLightbox(b.dataset.cmdId, 'search'); };
      });
    }

    if (q.trim().length >= 2) {
      clearTimeout(searchTrackTimer);
      searchTrackTimer = setTimeout(() => {
        tel.track('search_query', { props: { query: q.trim().slice(0, 64), result_count: matches.length } });
      }, 600);
    }
  }

  function openCmd() {
    $('cmdModal').hidden = false;
    const inp = $('cmdInput');
    inp.value = '';
    renderCmdResults('');
    setTimeout(() => inp.focus(), 20);
  }
  function closeCmd() { $('cmdModal').hidden = true; }

  /* ---------- GLOBAL EVENTS ---------- */
  function bindEvents() {
    $('brandHome').onclick = (e) => {
      e.preventDefault();
      state.activeCategory = 'all';
      renderTopCategories();
      renderGallery();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    $('themeToggle').onclick = () => {
      state.theme = state.theme === 'dark' ? 'light' : 'dark';
      applyTheme();
    };

    // Hero buttons
    $('heroCliCopy').onclick = () => {
      const p = state.featured[state.heroIdx];
      if (!p) return;
      copyText(`ilab get ${p.id}`, `已复制：ilab get ${p.id}`);
      tel.track('copy_prompt', { pattern_id: p.id, category: p.category, props: { prompt_mode: 'cli_cmd', surface: 'hero' } });
    };
    $('heroCopyPrompt').onclick = () => {
      const p = state.featured[state.heroIdx];
      if (!p) return;
      copyText(ai.buildPrompt(p, { mode: 'strict', framework: 'vanilla' }), `已复制「${p.name_cn}」AI 蓝图规范`);
      tel.track('copy_prompt', { pattern_id: p.id, category: p.category, props: { prompt_mode: 'strict', surface: 'hero' } });
    };
    $('heroZoom').onclick = () => {
      const p = state.featured[state.heroIdx];
      if (p) openLightbox(p.id, 'hero');
    };
    $('heroFlipTheme').onclick = () => {
      state.heroSpecimenTheme = state.heroSpecimenTheme === 'dark' ? 'light' : 'dark';
      postToIframe($('heroIframe'), { type: 'set-theme', theme: state.heroSpecimenTheme });
    };

    // Lightbox buttons
    $('closeLightbox').onclick = closeLightbox;
    $('lightboxModal').onclick = (e) => { if (e.target === $('lightboxModal')) closeLightbox(); };
    $('lbCliChip').onclick = () => {
      if (!state.lightboxPattern) return;
      copyText(`ilab get ${state.lightboxPattern.id}`, `已复制：ilab get ${state.lightboxPattern.id}`);
    };
    $('lbFlipTheme').onclick = () => {
      state.lightboxTheme = state.lightboxTheme === 'dark' ? 'light' : 'dark';
      postToIframe($('lbIframe'), { type: 'set-theme', theme: state.lightboxTheme });
    };
    $('lbCopyPrompt').onclick = () => {
      const p = state.lightboxPattern;
      if (!p) return;
      copyText(ai.buildPrompt(p, { mode: 'strict', framework: 'vanilla' }), `已复制「${p.name_cn}」AI 蓝图规范`);
      tel.track('copy_prompt', { pattern_id: p.id, category: p.category, props: { prompt_mode: 'strict', surface: 'lightbox' } });
    };
    $('lbOpenMd').onclick = () => {
      if (state.lightboxPattern) window.open(`patterns/${state.lightboxPattern.id}.md`, '_blank', 'noopener');
    };

    // AI CLI / Skill Modal
    $('openAiSetup').onclick = openAiModal;
    $('closeAiModal').onclick = closeAiModal;
    $('aiModal').onclick = (e) => { if (e.target === $('aiModal')) closeAiModal(); };
    $('copyCliInstall').onclick = () => copyText($('cliInstallCmd').textContent, '已复制 ilab CLI 安装命令');
    $('copySkillInstall').onclick = () => copyText($('skillInstallCmd').textContent, '已复制 SKILL.md 安装命令');
    $('copySkillRaw').onclick = async () => {
      const txt = await (await fetch('SKILL.md')).text();
      copyText(txt, '已复制 SKILL.md 全文');
    };

    // ⌘K Palette
    $('openCmd').onclick = openCmd;
    $('cmdModal').onclick = (e) => { if (e.target === $('cmdModal')) closeCmd(); };
    $('cmdInput').oninput = (e) => renderCmdResults(e.target.value);
    $('cmdInput').onkeydown = (e) => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        const n = state.cmdMatches.length;
        if (!n) return;
        state.cmdIdx = (state.cmdIdx + (e.key === 'ArrowDown' ? 1 : -1) + n) % n;
        $('cmdResults').querySelectorAll('.cmd-item').forEach((el, i) => {
          el.classList.toggle('active', i === state.cmdIdx);
          if (i === state.cmdIdx) el.scrollIntoView({ block: 'nearest' });
        });
      } else if (e.key === 'Enter' && state.cmdMatches[state.cmdIdx]) {
        e.preventDefault();
        const id = state.cmdMatches[state.cmdIdx].id;
        closeCmd();
        openLightbox(id, 'search');
      }
    };

    // Cross-iframe telemetry
    window.addEventListener('message', (e) => {
      const msg = e.data;
      if (!msg || typeof msg !== 'object') return;
      if (msg.type === 'il-interact' && msg.id) {
        const p = state.patterns.find((x) => x.id === msg.id);
        if (!p) return;
        const surface = state.lightboxPattern && state.lightboxPattern.id === p.id
          ? 'lightbox'
          : (state.featured[state.heroIdx] && state.featured[state.heroIdx].id === p.id ? 'hero' : 'gallery');
        tel.trackInteract(p.id, p.category, surface);
      }
    });

    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if ($('cmdModal').hidden) openCmd(); else closeCmd();
      } else if (e.key === 'Escape') {
        if (!$('cmdModal').hidden) closeCmd();
        else if (!$('lightboxModal').hidden) closeLightbox();
        else if (!$('aiModal').hidden) closeAiModal();
      }
    });
  }

  async function init() {
    loadPrefs();
    const res = await fetch('api/patterns.json');
    const data = await res.json();
    state.categories = data.categories || [];
    state.patterns = data.patterns || [];
    state.catMap = {};
    state.categories.forEach((c) => { state.catMap[c.id] = c; });

    const featOrder = data.featured_order || [];
    state.featured = featOrder.map((id) => state.patterns.find((p) => p.id === id)).filter(Boolean);
    if (!state.featured.length) state.featured = state.patterns.slice(0, 5);

    bindEvents();
    renderTopCategories();
    selectHero(0);
    renderGallery();

    tel.track('page_view', { props: { theme: state.theme, viewport: `${window.innerWidth}x${window.innerHeight}` } });
  }

  init().catch((err) => {
    console.error('Interaction Lab init failed:', err);
    $('galleryGrid').innerHTML = `<div style="padding:40px;text-align:center;color:var(--ink3)">加载失败：${err.message}</div>`;
  });
})();
