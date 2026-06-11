const MajorRanking = (() => {
  let majors = [];
  let majorTree = [];
  let schoolNameToIdx = Object.create(null);
  let onSchoolClick = null;
  let activeCode = '';
  let activeDiscipline = '';
  let catalogFilter = '';
  let searchTimer = null;
  let catalogTimer = null;

  const TAG_CLASS = {
    '985': 'tag-985',
    '211': 'tag-211',
    '双一流': 'tag-dfc',
    '一本': 'tag-yiben',
    '二本': 'tag-erben',
    '其他': 'tag-qita',
  };

  function init(opts = {}) {
    onSchoolClick = opts.onSchoolClick || null;
    schoolNameToIdx = opts.schoolNameToIdx || Object.create(null);
    bindEvents();
  }

  function bindEvents() {
    const search = document.getElementById('major-search');
    const list = document.getElementById('major-suggest-list');
    const toggle = document.getElementById('toggle-ranking-panel');
    const openCatalog = document.getElementById('open-major-catalog');
    const catalogOverlay = document.getElementById('major-catalog-overlay');
    const catalogClose = document.getElementById('major-catalog-close');
    const catalogSearch = document.getElementById('major-catalog-search');

    if (search) {
      search.addEventListener('input', () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => showSuggestions(search.value.trim()), 120);
      });
      search.addEventListener('focus', () => showSuggestions(search.value.trim()));
      search.addEventListener('keydown', e => {
        if (e.key !== 'Enter') return;
        e.preventDefault();
        const first = list?.querySelector('.major-suggest-item[data-code]');
        if (!first) return;
        selectMajor(first.dataset.code, first.dataset.name);
        list.classList.add('hidden');
      });
    }

    if (list) {
      list.addEventListener('click', e => {
        const item = e.target.closest('.major-suggest-item');
        if (!item) return;
        selectMajor(item.dataset.code, item.dataset.name);
        list.classList.add('hidden');
      });
    }

    document.addEventListener('click', e => {
      if (!e.target.closest('#major-search-wrap')) {
        list?.classList.add('hidden');
      }
    });

    document.getElementById('major-rank-list')?.addEventListener('click', e => {
      const row = e.target.closest('[data-school-name]');
      if (!row || !onSchoolClick) return;
      const idx = schoolNameToIdx[row.dataset.schoolName];
      if (idx != null) onSchoolClick(idx);
    });

    toggle?.addEventListener('click', () => {
      const panel = document.getElementById('ranking-panel');
      panel?.classList.toggle('collapsed');
      toggle.textContent = panel?.classList.contains('collapsed') ? '+' : '−';
    });

    openCatalog?.addEventListener('click', e => {
      e.preventDefault();
      openCatalogModal();
    });
    catalogClose?.addEventListener('click', () => closeCatalogModal());
    catalogOverlay?.addEventListener('click', e => {
      if (e.target === catalogOverlay) closeCatalogModal();
    });

    catalogSearch?.addEventListener('input', () => {
      clearTimeout(catalogTimer);
      catalogTimer = setTimeout(() => {
        catalogFilter = catalogSearch.value.trim();
        renderCatalogDetail();
      }, 120);
    });

    document.getElementById('major-catalog-nav')?.addEventListener('click', e => {
      const btn = e.target.closest('.major-catalog-nav-item');
      if (!btn) return;
      activeDiscipline = btn.dataset.discipline || '';
      renderCatalogNav();
      renderCatalogDetail();
    });

    document.getElementById('major-catalog-detail')?.addEventListener('click', e => {
      const item = e.target.closest('.major-catalog-major');
      if (!item) return;
      selectMajor(item.dataset.code, item.dataset.name);
      closeCatalogModal();
    });

    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') closeCatalogModal();
    });
  }

  function buildMajorTree(items) {
    const disciplines = Object.create(null);
    for (const m of items) {
      const d = m.discipline || '其他';
      const c = m.majorClass || '其他';
      if (!disciplines[d]) disciplines[d] = Object.create(null);
      if (!disciplines[d][c]) disciplines[d][c] = [];
      disciplines[d][c].push(m);
    }
    return Object.keys(disciplines).sort((a, b) => a.localeCompare(b, 'zh-CN')).map(name => ({
      name,
      classes: Object.keys(disciplines[name]).sort((a, b) => a.localeCompare(b, 'zh-CN')).map(className => ({
        name: className,
        majors: disciplines[name][className].sort((a, b) => a.name.localeCompare(b.name, 'zh-CN')),
      })),
    }));
  }

  async function loadIndex() {
    const resp = await fetch('data/majors/index.json');
    if (!resp.ok) throw new Error('专业目录加载失败');
    const data = await resp.json();
    majors = data.majors || [];
    majorTree = buildMajorTree(majors);
    if (majorTree.length && !activeDiscipline) {
      activeDiscipline = majorTree[0].name;
    }
    return data.meta;
  }

  function openCatalogModal() {
    if (!majors.length) return;
    catalogFilter = '';
    const catalogSearch = document.getElementById('major-catalog-search');
    if (catalogSearch) catalogSearch.value = '';
    const countEl = document.getElementById('major-catalog-count');
    if (countEl) countEl.textContent = String(majors.length);
    if (!activeDiscipline && majorTree.length) {
      activeDiscipline = majorTree[0].name;
    }
    renderCatalogNav();
    renderCatalogDetail();
    document.getElementById('major-catalog-overlay')?.classList.remove('hidden');
  }

  function closeCatalogModal() {
    document.getElementById('major-catalog-overlay')?.classList.add('hidden');
  }

  function renderCatalogNav() {
    const nav = document.getElementById('major-catalog-nav');
    if (!nav) return;

    if (catalogFilter) {
      nav.innerHTML = '<button type="button" class="major-catalog-nav-item active" data-discipline="">搜索结果</button>';
      return;
    }

    nav.innerHTML = majorTree.map(d => `
      <button type="button" class="major-catalog-nav-item${d.name === activeDiscipline ? ' active' : ''}"
        data-discipline="${d.name}">${d.name}</button>
    `).join('');
  }

  function filterMajors(list) {
    if (!catalogFilter) return list;
    return list.filter(m =>
      m.name.includes(catalogFilter)
      || m.code.includes(catalogFilter)
      || (m.discipline && m.discipline.includes(catalogFilter))
      || (m.majorClass && m.majorClass.includes(catalogFilter))
      || m.path?.some(p => p.includes(catalogFilter))
    );
  }

  function renderCatalogDetail() {
    const detail = document.getElementById('major-catalog-detail');
    if (!detail) return;

    if (catalogFilter) {
      const pool = filterMajors(majors);
      if (!pool.length) {
        detail.innerHTML = '<p class="major-catalog-empty">未找到匹配专业</p>';
        return;
      }
      detail.innerHTML = `
        <div class="major-catalog-group">
          <div class="major-catalog-group-title">搜索到 ${pool.length} 个专业</div>
          <div class="major-catalog-majors">${pool.map(renderCatalogMajor).join('')}</div>
        </div>`;
      return;
    }

    const discipline = majorTree.find(d => d.name === activeDiscipline);
    if (!discipline) {
      detail.innerHTML = '<p class="major-catalog-empty">请选择学科门类</p>';
      return;
    }

    detail.innerHTML = discipline.classes.map(group => `
      <div class="major-catalog-group">
        <div class="major-catalog-group-title">${group.name}（${group.majors.length}）</div>
        <div class="major-catalog-majors">${group.majors.map(renderCatalogMajor).join('')}</div>
      </div>
    `).join('');
  }

  function renderCatalogMajor(m) {
    const badge = m.ranked
      ? '<span class="major-catalog-badge ranked">有排名</span>'
      : '<span class="major-catalog-badge">暂无排名</span>';
    return `<button type="button" class="major-catalog-major${m.ranked ? '' : ' no-rank'}"
      data-code="${m.code}" data-name="${m.name}">${m.name}${badge}</button>`;
  }

  function showSuggestions(query) {
    const list = document.getElementById('major-suggest-list');
    if (!list) return;

    let pool = majors.filter(m => m.ranked);
    if (query) {
      pool = pool.filter(m =>
        m.name.includes(query)
        || m.code.includes(query)
        || (m.discipline && m.discipline.includes(query))
        || (m.majorClass && m.majorClass.includes(query))
        || m.path?.some(p => p.includes(query))
      );
    }

    pool = pool.slice(0, 30);
    if (!pool.length) {
      list.innerHTML = query
        ? '<li class="major-suggest-empty">未找到匹配专业，可打开「专业目录」浏览</li>'
        : '<li class="major-suggest-empty">输入关键词搜索，或点击「专业目录」浏览全部</li>';
      list.classList.remove('hidden');
      return;
    }

    list.innerHTML = pool.map(m => `
      <li class="major-suggest-item" data-code="${m.code}" data-name="${m.name}">
        <span class="major-suggest-name">${m.name}</span>
        <span class="major-suggest-meta">${m.discipline}${m.majorClass ? ' · ' + m.majorClass : ''}</span>
      </li>
    `).join('');
    list.classList.remove('hidden');
  }

  async function selectMajor(code, name) {
    activeCode = code;
    const search = document.getElementById('major-search');
    if (search) search.value = name || code;

    const summary = document.getElementById('major-rank-summary');
    const container = document.getElementById('major-rank-list');
    if (!container) return;

    summary.textContent = '正在加载排名…';
    container.innerHTML = '';

    const major = majors.find(m => m.code === code);
    if (major && !major.ranked) {
      summary.textContent = `${major.name} · 暂无软科排名（开设院校少于 4 所）`;
      container.innerHTML = '<p class="major-rank-empty">该专业暂无排名数据，可在教育部专业目录中查看开设院校</p>';
      return;
    }

    try {
      const resp = await fetch(`data/majors/rankings/${code}.json`);
      if (!resp.ok) throw new Error('暂无该专业排名数据');
      const data = await resp.json();
      renderRanking(data);
    } catch (err) {
      summary.textContent = err.message || '加载失败';
      container.innerHTML = '<p class="major-rank-empty">暂无排名数据</p>';
    }
  }

  function renderRanking(data) {
    const summary = document.getElementById('major-rank-summary');
    const container = document.getElementById('major-rank-list');
    const records = data.records || [];

    summary.textContent = records.length
      ? `${data.majorName} · ${data.year}软科排名 · 共 ${records.length} 所`
      : `${data.majorName} · 暂无上榜院校`;

    if (!records.length) {
      container.innerHTML = '<p class="major-rank-empty">该专业暂无排名数据</p>';
      return;
    }

    container.innerHTML = `<ol class="major-rank-ol">${records.map(r => {
      const tag = r.tag || '其他';
      const tagCls = TAG_CLASS[tag] || TAG_CLASS['其他'];
      const score = r.score != null ? `<span class="major-rank-score">${r.score}</span>` : '';
      const grade = r.grade ? `<span class="major-rank-grade">${r.grade}</span>` : '';
      const clickable = schoolNameToIdx[r.schoolName] != null ? ' is-clickable' : '';
      return `<li class="major-rank-row${clickable}" data-school-name="${r.schoolName}">
        <span class="major-rank-no">${r.rank}</span>
        <span class="major-rank-info">
          <span class="major-rank-school">${r.schoolName}</span>
          <span class="major-rank-sub">${r.province || ''}</span>
        </span>
        <span class="major-rank-meta">
          <span class="tag ${tagCls}">${tag}</span>
          ${grade}${score}
        </span>
      </li>`;
    }).join('')}</ol>`;
  }

  function setSchoolLookup(lookup) {
    schoolNameToIdx = Object.create(null);
    for (let i = 0; i < lookup.length; i++) {
      schoolNameToIdx[lookup[i].n] = i;
    }
  }

  return { init, loadIndex, selectMajor, setSchoolLookup };
})();
