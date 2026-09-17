/* ==========================================================================
   iPRES 2026 virtual poster hall - shared behaviour for every page.

   Loads the data files once, builds the header/footer/poll button, keeps the
   "poster passport" in localStorage, and renders PDF thumbnails with pdf.js.
   No build step, no framework: drop the folder on any web server.
   ========================================================================== */

const IPRES = (() => {
  const PDFJS_VERSION = '3.11.174';
  const PDFJS_LOCAL = 'assets/vendor/pdfjs';
  const PDFJS_CDN = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${PDFJS_VERSION}`;
  const STORE_SEEN = 'ipres26.seen';
  const STORE_THEME = 'ipres26.theme';

  const NAV = [
    { href: 'index.html', label: 'Home' },
    { href: 'posters.html', label: 'All posters' },
    { href: 'map.html', label: 'Map' },
    { href: 'trails.html', label: 'Trails' },
  ];

  const BADGES = [
    { at: 1, emoji: '\u{1F423}', name: 'First poster' },
    { at: 5, emoji: '\u{1F9ED}', name: 'Finding your feet' },
    { at: 10, emoji: '\u{1F6B6}', name: 'Ten down' },
    { at: 20, emoji: '\u{1F525}', name: 'Halfway hero' },
    { at: 30, emoji: '\u{1F393}', name: 'Serious scholar' },
    { at: 39, emoji: '\u{1F3C6}', name: 'Completed the hall' },
  ];

  /* ---------- tiny helpers ---------- */

  const esc = (value) => String(value == null ? '' : value)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

  const el = (html) => {
    const t = document.createElement('template');
    t.innerHTML = html.trim();
    return t.content.firstElementChild;
  };

  const store = {
    get(key, fallback) {
      try {
        const raw = localStorage.getItem(key);
        return raw == null ? fallback : JSON.parse(raw);
      } catch (err) { return fallback; }
    },
    set(key, value) {
      try { localStorage.setItem(key, JSON.stringify(value)); } catch (err) { /* private mode */ }
    },
  };

  /* ---------- data ---------- */

  const cache = {};
  const loadJSON = (path) => {
    if (!cache[path]) {
      cache[path] = fetch(path, { cache: 'no-cache' }).then((res) => {
        if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}`);
        return res.json();
      });
    }
    return cache[path];
  };

  const data = {
    posters: () => loadJSON('data/posters.json'),
    layout: () => loadJSON('data/layout.json'),
    config: () => loadJSON('data/config.json').catch(() => ({ poll: {}, conference: {} })),
  };

  /* Posters plus their (provisional) map slot, and a themes lookup. */
  async function hall() {
    const [posterData, layoutData] = await Promise.all([data.posters(), data.layout()]);
    const slotByPoster = {};
    layoutData.clusters.forEach((cluster) => {
      cluster.walls.forEach((wall) => {
        wall.slots.forEach((slot) => {
          if (slot.poster) {
            slotByPoster[slot.poster] = {
              id: slot.id, number: slot.number, cluster: cluster.id, clusterName: cluster.name,
            };
          }
        });
      });
    });
    const themes = {};
    posterData.themes.forEach((theme) => { themes[theme.id] = theme; });
    const posters = posterData.posters.map((poster) => ({
      ...poster,
      slot: slotByPoster[poster.id] || null,
      themeObjects: (poster.themes || []).map((id) => themes[id]).filter(Boolean),
    }));
    /* Board order where boards are assigned, title order where they are not. */
    posters.sort((a, b) =>
      (a.slot?.number || 9999) - (b.slot?.number || 9999)
      || a.title.localeCompare(b.title));
    return { posters, themes, themeList: posterData.themes, counts: posterData.counts, layout: layoutData };
  }

  const byId = (posters) => Object.fromEntries(posters.map((p) => [p.id, p]));

  /* ---------- colour scheme ---------- */

  function initTheme() {
    const saved = store.get(STORE_THEME, null);
    const preferred = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.dataset.theme = preferred;
  }

  function toggleTheme() {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    store.set(STORE_THEME, next);
    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      button.textContent = next === 'dark' ? '☀️' : '\u{1F319}';
    });
  }

  /* ---------- the poster passport ---------- */

  const passport = {
    seen: () => new Set(store.get(STORE_SEEN, [])),
    has(id) { return this.seen().has(id); },
    toggle(id) {
      const seen = this.seen();
      if (seen.has(id)) seen.delete(id); else seen.add(id);
      store.set(STORE_SEEN, [...seen]);
      document.dispatchEvent(new CustomEvent('passport:change', { detail: { id, seen: [...seen] } }));
      return seen.has(id);
    },
    reset() {
      store.set(STORE_SEEN, []);
      document.dispatchEvent(new CustomEvent('passport:change', { detail: { seen: [] } }));
    },
    badges(count) { return BADGES.map((b) => ({ ...b, earned: count >= b.at })); },
  };

  function renderPassport(node, total) {
    if (!node) return;
    const draw = () => {
      const count = passport.seen().size;
      const pct = total ? Math.round((count / total) * 100) : 0;
      node.innerHTML = `
        <h3>Your poster passport</h3>
        <p>Mark posters as seen while you wander. Kept in this browser only - nothing is sent anywhere.</p>
        <div class="passport__bar"><div class="passport__fill" style="width:${pct}%"></div></div>
        <p><strong>${count}</strong> of ${total} posters visited${count ? ` &middot; ${pct}%` : ''}</p>
        <div class="passport__badges">${passport.badges(count).map((b) =>
          `<span class="badge${b.earned ? ' is-earned' : ''}" title="${esc(b.name)} (${b.at}+)">${b.emoji}</span>`).join('')}</div>
        ${count ? '<p><button class="btn btn--sm btn--ghost" data-passport-reset>Start again</button></p>' : ''}`;
      const reset = node.querySelector('[data-passport-reset]');
      if (reset) reset.addEventListener('click', () => passport.reset());
    };
    draw();
    document.addEventListener('passport:change', draw);
  }

  /* ---------- PDF rendering (pdf.js, vendored, loaded on demand) ---------- */

  let pdfLibPromise = null;

  const loadScript = (src) => new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src;
    script.onload = resolve;
    script.onerror = () => reject(new Error(`could not fetch ${src}`));
    document.head.appendChild(script);
  });

  /* The local copy comes first so the viewer survives bad conference wifi;
     the CDN is only a safety net if assets/vendor was not deployed. */
  function pdfLib() {
    if (!pdfLibPromise) {
      pdfLibPromise = loadScript(`${PDFJS_LOCAL}/pdf.min.js`)
        .then(() => PDFJS_LOCAL)
        .catch(() => loadScript(`${PDFJS_CDN}/pdf.min.js`).then(() => PDFJS_CDN))
        .then((base) => {
          const lib = window.pdfjsLib;
          if (!lib) throw new Error('pdf.js did not load');
          lib.GlobalWorkerOptions.workerSrc = `${base}/pdf.worker.min.js`;
          return lib;
        });
    }
    return pdfLibPromise;
  }

  const docCache = new Map();
  function openPdf(url) {
    if (!docCache.has(url)) {
      docCache.set(url, pdfLib().then((lib) => lib.getDocument(url).promise));
    }
    return docCache.get(url);
  }

  /* pdf.js refuses two concurrent renders onto one canvas, which is easy to
     trigger by clicking zoom or next-page twice quickly. Cancel whatever that
     canvas was drawing before starting again. */
  const renderTasks = new WeakMap();

  async function renderPage(doc, pageNumber, canvas, targetWidth) {
    const inFlight = renderTasks.get(canvas);
    if (inFlight) {
      inFlight.cancel();
      try { await inFlight.promise; } catch (err) { /* cancelled, as intended */ }
    }
    const page = await doc.getPage(pageNumber);
    const base = page.getViewport({ scale: 1 });
    const scale = targetWidth / base.width;
    const viewport = page.getViewport({ scale });
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(viewport.width * ratio);
    canvas.height = Math.floor(viewport.height * ratio);
    canvas.style.width = `${Math.floor(viewport.width)}px`;
    canvas.style.height = `${Math.floor(viewport.height)}px`;
    const context = canvas.getContext('2d', { alpha: false });
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    const task = page.render({ canvasContext: context, viewport });
    renderTasks.set(canvas, task);
    try {
      await task.promise;
    } catch (err) {
      if (err && err.name !== 'RenderingCancelledException') throw err;
    } finally {
      if (renderTasks.get(canvas) === task) renderTasks.delete(canvas);
    }
    return viewport;
  }

  /* Lazily paint the first page of every [data-pdf-thumb] that scrolls into view. */
  function thumbnails(root = document) {
    const targets = [...root.querySelectorAll('[data-pdf-thumb]:not([data-thumb-done])')];
    if (!targets.length) return;
    const paint = async (node) => {
      node.dataset.thumbDone = '1';
      const url = node.dataset.pdfThumb;
      try {
        const doc = await openPdf(url);
        const canvas = document.createElement('canvas');
        await renderPage(doc, 1, canvas, 520);
        /* renderPage sizes the canvas in px for the full viewer; a thumbnail
           should scale to its card instead, so hand it back to the CSS. */
        canvas.style.width = '';
        canvas.style.height = '';
        canvas.setAttribute('role', 'img');
        canvas.setAttribute('aria-label', node.dataset.thumbAlt || 'Poster preview');
        node.replaceChildren(canvas);
      } catch (err) {
        node.replaceChildren(el('<div class="placeholder">Preview unavailable<br><small>Open the PDF instead</small></div>'));
      }
    };
    if (!('IntersectionObserver' in window)) { targets.forEach(paint); return; }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) { observer.unobserve(entry.target); paint(entry.target); }
      });
    }, { rootMargin: '400px 0px' });
    targets.forEach((node) => observer.observe(node));
  }

  /* ---------- loading state: the logo's cyclist, wheels turning ---------- */

  const spokes = (cx, cy, r) => [0, 45, 90, 135]
    .map((deg) => {
      const a = (deg * Math.PI) / 180;
      const dx = Math.cos(a) * r, dy = Math.sin(a) * r;
      return `<line x1="${cx - dx}" y1="${cy - dy}" x2="${cx + dx}" y2="${cy + dy}" stroke-width="1.6"/>`;
    }).join('');

  const wheel = (cx, cy) => `<g class="bike-wheel bike-ink" fill="none" stroke-linecap="round">
      <circle cx="${cx}" cy="${cy}" r="15" stroke-width="3.5"/>
      ${spokes(cx, cy, 13)}
      <circle cx="${cx}" cy="${cy}" r="2.4" class="bike-fill" stroke="none"/>
    </g>`;

  function loader(label = 'Loading', modifier = '') {
    return `<div class="bike-loader ${modifier}" role="status" aria-live="polite">
      <svg viewBox="0 0 120 78" aria-hidden="true">
        <g class="bike-body bike-ink" fill="none" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M28 50 L56 50 L44 28 Z"/>
          <path d="M56 50 L76 26 M44 28 L76 26 M76 26 L86 50"/>
          <path d="M44 28 L42 21 M35 20 H49"/>
          <path d="M76 26 L83 21"/>
          <path d="M60 14 L52 30 M60 14 L70 22 M60 14 L58 24 L64 34"/>
        </g>
        <circle cx="60" cy="7" r="6" class="bike-fill"/>
        ${wheel(28, 50)}
        ${wheel(86, 50)}
        <line x1="4" y1="70" x2="116" y2="70" class="bike-road" stroke-width="4" stroke-linecap="round"/>
      </svg>
      <span class="bike-loader__label">${esc(label)}</span>
    </div>`;
  }

  /* ---------- poster thumbnails ---------- */

  /* A pre-rendered WebP if tools/build_thumbs.py has run (the normal case:
     ~50KB instead of downloading a whole PDF), the in-browser pdf.js renderer
     only as a fallback for a poster whose thumbnail has not been built yet. */
  function thumbnailFor(poster, className = 'poster-card__thumb') {
    if (poster.thumb) {
      return `<div class="${className}">
        <img src="${esc(poster.thumb)}" alt="First page of ${esc(poster.title)}"
             ${poster.thumbWidth ? `width="${poster.thumbWidth}" height="${poster.thumbHeight}"` : ''}
             loading="lazy" decoding="async">
      </div>`;
    }
    if (poster.file) {
      return `<div class="${className}" data-pdf-thumb="${esc(poster.file)}"
                   data-thumb-alt="First page of ${esc(poster.title)}">
        ${loader('Pedalling', 'bike-loader--inline')}
      </div>`;
    }
    return `<div class="${className}">
      <div class="placeholder">\u{1F4EC}<br>PDF on its way<br><small>Abstract is here already</small></div>
    </div>`;
  }

  /* ---------- poster cards ---------- */

  function posterCard(poster, options = {}) {
    const seen = passport.has(poster.id);
    const themeChips = (poster.themeObjects || []).slice(0, 2).map((theme) =>
      `<span class="chip chip--solid" style="background:${theme.color}">${theme.emoji} ${esc(theme.short)}</span>`).join('');
    const thumb = thumbnailFor(poster);
    return `<a class="card poster-card" href="poster.html?id=${encodeURIComponent(poster.id)}">
      ${poster.slot ? `<span class="slot-badge">#${poster.slot.number}</span>` : ''}
      ${seen ? '<span class="seen-badge" title="You marked this as seen">✓</span>' : ''}
      ${thumb}
      <div class="poster-card__body">
        <h3 class="poster-card__title">${options.highlight ? options.highlight(poster.title) : esc(poster.title)}</h3>
        <p class="poster-card__authors">${esc(poster.authorLine)}</p>
        <div class="poster-card__foot">
          ${themeChips}
          ${poster.status === 'awaited' ? '<span class="chip chip--awaited">Coming soon</span>' : ''}
          ${poster.presentedOnline ? '<span class="chip chip--online">\u{1F4BB} Online</span>' : ''}
        </div>
      </div>
    </a>`;
  }

  /* ---------- chrome: header, footer, floating poll button ---------- */

  function pollButton(config, extraClass = '', labelOverride = '') {
    const poll = config.poll || {};
    const label = labelOverride || poll.label || 'Vote for your favourite';
    if (poll.url) {
      return `<a class="btn btn--vote ${extraClass}" href="${esc(poll.url)}" target="_blank" rel="noopener">
        <span aria-hidden="true">⭐</span> ${esc(label)}</a>`;
    }
    return `<button class="btn btn--vote ${extraClass}" type="button" data-poll-pending
      title="${esc(poll.opensText || 'Voting opens at the conference.')}">
      <span aria-hidden="true">⭐</span> ${esc(label)}</button>`;
  }

  function pollBanner(config, headline) {
    const poll = config.poll || {};
    return `<aside class="poll-banner">
      <div aria-hidden="true">\u{1F5F3}️</div>
      <div class="poll-banner__text">
        <h3>${esc(headline || poll.heading || 'Best poster award')}</h3>
        <p>${esc(poll.blurb || 'Vote for the poster that made you think hardest.')}</p>
      </div>
      ${pollButton(config)}
    </aside>`;
  }

  function wirePollPending(root = document) {
    root.querySelectorAll('[data-poll-pending]').forEach((button) => {
      if (button.dataset.wired) return;
      button.dataset.wired = '1';
      button.addEventListener('click', () => {
        const message = button.getAttribute('title');
        const note = el(`<span class="chip chip--awaited" style="margin-left:.6rem">${esc(message)}</span>`);
        button.insertAdjacentElement('afterend', note);
        setTimeout(() => note.remove(), 4000);
      });
    });
  }

  async function chrome(currentPage) {
    const config = await data.config();
    const header = document.querySelector('[data-site-header]');
    if (header) {
      header.className = 'site-header';
      header.innerHTML = `<div class="wrap-wide site-header__inner">
        <a class="brand" href="index.html">
          <img src="iPRES2026_Logos/Logo2.png" alt="iPRES 2026 Copenhagen">
          <span class="brand__tag">Poster hall</span>
        </a>
        <nav class="nav" aria-label="Main">
          ${NAV.map((item) => `<a href="${item.href}"${item.href === currentPage ? ' aria-current="page"' : ''}>${item.label}</a>`).join('')}
        </nav>
        <button class="icon-btn" type="button" data-theme-toggle aria-label="Switch between light and dark">
          ${document.documentElement.dataset.theme === 'dark' ? '☀️' : '\u{1F319}'}</button>
      </div>`;
      header.querySelector('[data-theme-toggle]').addEventListener('click', toggleTheme);
    }

    const footer = document.querySelector('[data-site-footer]');
    if (footer) {
      const conf = config.conference || {};
      footer.className = 'site-footer';
      footer.innerHTML = `<div class="wrap site-footer__inner">
        <div>
          <img src="iPRES2026_Logos/Logo_under.png" alt="iPRES 2026 Copenhagen">
          <p>The virtual poster hall for ${esc(conf.name || 'iPRES 2026')}${conf.city ? ` in ${esc(conf.city)}` : ''}.
          Every poster stays here after the conference, so you can catch the ones you missed.</p>
        </div>
        <div>
          <p><strong>Posters</strong> remain the copyright of their authors.<br>
          ${conf.website ? `<a href="${esc(conf.website)}">${esc(conf.name || 'Conference website')}</a><br>` : ''}
          <a href="posters.html">Browse everything</a> &middot;
          <a href="trails.html">Follow a trail</a> &middot;
          <a href="map.html">Find a poster in the room</a></p>
        </div>
      </div>`;
    }

    if (!document.querySelector('[data-no-poll-float]')) {
      document.body.insertAdjacentHTML('beforeend', pollButton(config, 'poll-float'));
    }
    wirePollPending();
    return config;
  }

  initTheme();

  return {
    esc, el, store, data, hall, byId, chrome, passport, renderPassport,
    thumbnails, thumbnailFor, pdfLib, openPdf, renderPage, posterCard, loader,
    pollBanner, pollButton, wirePollPending, BADGES,
  };
})();
