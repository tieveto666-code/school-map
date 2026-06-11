(() => {
  let schoolIndex = [];
  let schoolDetails = {};
  let baikeScores = {};
  let provinceNameToCode = {};
  let currentScores = {};
  let filteredIndices = [];
  let selectedProv = '';
  let filterTimer = null;

  let byProvince = Object.create(null);
  let byType = Object.create(null);
  let byNature = Object.create(null);

  const DATA_VERSION = 'demo';
  const DEFAULT_TYPES = new Set();
  const TYPE_OPTIONS = ['985', '211', '双一流', '其他'];
  const NATURE_OPTIONS = ['研究型', '医学', '军队', '师范', '政法', '财经', '艺术', '民族', '综合', '民办'];

  function isMilitarySchool(s) {
    return (s.ns || []).includes('军队') || s.t === '军队院校' || String(s.c || '').startsWith('9100');
  }

  function matchesNature(s, nature) {
    if (nature === '军队') return isMilitarySchool(s);
    return (s.ns || []).includes(nature);
  }

  function renderScopeNote(meta) {
    const total = meta.total || 0;
    const moe = meta.moeUndergraduate || (total - (meta.militaryAcademies || 0));
    const mil = meta.militaryAcademies || 0;
    const updated = meta.updatedAt || '';

    let lines;
    let short;
    if (meta.demo) {
      lines = [
        `平台<b>代码完整可用</b>；当前加载的是<b>模拟演示数据</b>，共 <b>${total}</b> 所示例院校（${moe} 所普通高校示例 + ${mil} 所军队院校示例）。`,
        `不含真实院校名单，不可用于升学决策或统计分析。`,
        `真实数据需您自行从公开渠道获取，替换 data/schools.*.json 等文件，详见 README.md 与 DATA_SOURCES.md。`,
      ];
      short = `演示数据 ${total} 所（${updated}）；代码完整，数据需自行获取。`;
    } else {
      const officialMoe = 1365;
      const moeDiff = moe - officialMoe;
      lines = [
        `合计 <b>${total}</b> 所 = 教育部普通高校（本科）<b>${moe}</b> 所 + 军队院校（本科）<b>${mil}</b> 所。`,
        `仅统计办学层次为「本科」的院校；不含专科/高职、成人高校及港澳台高校。`,
        `军队院校单独维护，按学校标识码去重，筛选请用「学校性质 → 军队」。`,
      ];
      if (moeDiff > 0) {
        lines.push(`教育部本科部分基于 EOL 2024 全量表 + 2025 补丁，比官方 ${officialMoe} 所多 ${moeDiff} 所，待官方 XLS 校准。`);
      }
      short = `本科普通高校 ${moe} 所 + 军队本科 ${mil} 所 = ${total} 所（${updated}）；不含专科/高职。`;
    }

    const html = lines.map(t => `<p>${t}</p>`).join('');
    const note = $('scope-note-text');
    if (note) note.textContent = short;

    const tip = $('scope-tip');
    if (tip) {
      tip.innerHTML = html;
      tip.hidden = false;
    }
  }

  const $ = id => document.getElementById(id);

  function debounce(fn, ms) {
    return (...args) => { clearTimeout(filterTimer); filterTimer = setTimeout(() => fn(...args), ms); };
  }

  function setLoading(show, text) {
    const el = $('loading-overlay');
    if (!el) return;
    el.classList.toggle('hidden', !show);
    if (text) el.querySelector('.loading-text').textContent = text;
  }

  function getCheckedValues(containerId) {
    return [...document.querySelectorAll(`#${containerId} input:checked`)].map(i => i.value);
  }

  function setCheckedValues(containerId, values) {
    const set = new Set(values);
    document.querySelectorAll(`#${containerId} input`).forEach(i => { i.checked = set.has(i.value); });
  }

  function buildCheckboxGroup(containerId, options, defaults) {
    const box = $(containerId);
    box.innerHTML = options.map(v =>
      `<label class="chk-item"><input type="checkbox" value="${v}"${defaults.has(v) ? ' checked' : ''}> ${v}</label>`
    ).join('');
  }

  function getFullSchool(idx) {
    const s = schoolIndex[idx];
    const d = schoolDetails[s.c] || {};
    return {
      code: s.c, name: s.n, province: s.p, lat: s.lat, lng: s.lng,
      schoolType: s.t, natures: s.ns || [], l: s.l,
      ...d, name: s.n, province: s.p,
    };
  }

  function buildIndexes() {
    byProvince = Object.create(null);
    byType = Object.create(null);
    byNature = Object.create(null);
    for (let i = 0; i < schoolIndex.length; i++) {
      const s = schoolIndex[i];
      (byProvince[s.p] ||= []).push(i);
      (byType[s.t] ||= []).push(i);
      for (const n of s.ns || []) (byNature[n] ||= []).push(i);
      if (isMilitarySchool(s) && !(s.ns || []).includes('军队')) {
        (byNature['军队'] ||= []).push(i);
      }
    }
  }

  function intersectSets(a, b) {
    if (!a) return b;
    if (!b) return a;
    const setB = new Set(b);
    return a.filter(i => setB.has(i));
  }

  function unionTypes(types) {
    if (!types.length) return null;
    const set = new Set();
    for (let i = 0; i < schoolIndex.length; i++) {
      if (types.includes(schoolIndex[i].t)) set.add(i);
    }
    return [...set];
  }

  function unionNatures(natures) {
    if (!natures.length) return null;
    const set = new Set();
    for (let i = 0; i < schoolIndex.length; i++) {
      const s = schoolIndex[i];
      for (const n of natures) {
        if (matchesNature(s, n)) set.add(i);
      }
    }
    return [...set];
  }

  async function loadDetailsBackground() {
    const [detResp, bkResp] = await Promise.all([
      fetch(`data/schools.details.json?v=${DATA_VERSION}`, { cache: 'no-store' }),
      fetch('data/baike/scores.json').catch(() => null),
    ]);
    if (detResp.ok) schoolDetails = await detResp.json();
    if (bkResp?.ok) baikeScores = await bkResp.json();
  }

  async function loadScoresForProvince(provName, year) {
    const code = provinceNameToCode[provName];
    if (!code) { currentScores = {}; return { byYear: {} }; }
    const byYear = {};
    for (const y of [2023, 2024, 2025]) {
      try {
        const resp = await fetch(`data/scores/${code}/${y}.json`);
        if (!resp.ok) continue;
        const data = await resp.json();
        byYear[y] = (data.records || []).map(r => ({
          code: r.schoolCode,
          minScore: r.minScore,
        }));
        if (String(y) === String(year)) {
          currentScores = Object.create(null);
          (data.records || []).forEach(r => { currentScores[r.schoolCode] = r; });
        }
      } catch { /* skip */ }
    }
    return { byYear, code };
  }

  async function loadData() {
    setLoading(true, '正在加载院校数据…');
    const cacheBust = `v=${DATA_VERSION}`;
    const [indexResp, provResp] = await Promise.all([
      fetch(`data/schools.index.json?${cacheBust}`, { cache: 'no-store' }),
      fetch(`data/provinces.json?${cacheBust}`, { cache: 'no-store' }),
    ]);
    if (!indexResp.ok) throw new Error(`院校索引加载失败 (${indexResp.status})`);
    const indexData = await indexResp.json();
    schoolIndex = indexData.schools;
    const meta = indexData.meta || {};
    const metaEl = $('data-meta');
    if (metaEl) {
      metaEl.textContent = meta.total
        ? `数据 ${meta.updatedAt || ''} · 共 ${meta.total} 所${meta.militaryAcademies ? `（含军队 ${meta.militaryAcademies} 所）` : ''}`
        : '';
    }
    renderScopeNote(meta);
    if (!meta.militaryAcademies) {
      console.warn('[school-map] 当前院校索引不含军队院校，请重新上传 data/schools.index.json 并刷新');
    }
    const provList = await provResp.json();
    provList.forEach(p => { provinceNameToCode[p.name] = p.code; });

    buildIndexes();
    buildCheckboxGroup('filter-types', TYPE_OPTIONS, DEFAULT_TYPES);
    buildCheckboxGroup('filter-natures', NATURE_OPTIONS, new Set());

    const provSelect = $('filter-province');
    [...new Set(schoolIndex.map(s => s.p))].sort().forEach(p => {
      const opt = document.createElement('option');
      opt.value = p; opt.textContent = p;
      provSelect.appendChild(opt);
    });

    loadDetailsBackground();

    setLoading(true, '正在初始化地图…');
    await SchoolMap.init('map-container', schoolIndex, {});

    selectedProv = '';
    applyFilters();
    AnalyticsPanel.init({
      onSchoolClick(idx) {
        const school = getFullSchool(idx);
        const bk = baikeScores[school.code] || school.baikeScores;
        SchoolModal.show(school, bk, $('filter-year').value);
      },
    });
    MajorRanking.init({
      onSchoolClick(idx) {
        const school = getFullSchool(idx);
        const bk = baikeScores[school.code] || school.baikeScores;
        SchoolModal.show(school, bk, $('filter-year').value);
      },
    });
    MajorRanking.setSchoolLookup(schoolIndex);
    loadMajorRankingsBackground();
    setLoading(false);
  }

  async function loadMajorRankingsBackground() {
    try {
      const meta = await MajorRanking.loadIndex();
      const el = $('major-rank-summary');
      if (el && meta) {
        el.textContent = `${meta.year}软科专业排名 · 共 ${meta.rankedMajors} 个可排专业，请搜索选择`;
      }
    } catch {
      const el = $('major-rank-summary');
      if (el) el.textContent = '专业排名数据未就绪';
    }
  }

  async function applyFilters(opts = {}) {
    const name = $('search-name').value.trim().toLowerCase();
    selectedProv = $('filter-province').value;
    const types = getCheckedValues('filter-types');
    const natures = getCheckedValues('filter-natures');
    const year = $('filter-year').value;
    const scoreMin = parseInt($('score-min').value, 10) || 0;
    const scoreMax = parseInt($('score-max').value, 10) || 9999;
    const hasScoreFilter = $('score-min').value || $('score-max').value;

    let pool = unionTypes(types);
    pool = intersectSets(pool, unionNatures(natures));
    if (selectedProv) pool = intersectSets(pool, byProvince[selectedProv]);
    if (pool === null) pool = schoolIndex.map((_, i) => i);

    let scoreMeta = { byYear: {} };
    if (selectedProv || hasScoreFilter) {
      scoreMeta = await loadScoresForProvince(selectedProv || '北京市', year);
    } else {
      currentScores = {};
    }

    const result = [];
    for (let i = 0; i < pool.length; i++) {
      const idx = pool[i];
      const s = schoolIndex[idx];
      if (name && !s.n.toLowerCase().includes(name)) continue;
      if (hasScoreFilter) {
        const rec = currentScores[s.c];
        if (!rec) continue;
        if (rec.minScore < scoreMin || rec.minScore > scoreMax) continue;
      }
      result.push(idx);
    }

    filteredIndices = result;
    $('total-count').textContent = result.length;
    SchoolMap.update(result, selectedProv, { resetView: !!opts.resetView });

    const provForAnalytics = opts.analyticsProv || selectedProv;
    if (provForAnalytics) {
      const provIndices = result.filter(i => schoolIndex[i].p === provForAnalytics);
      AnalyticsPanel.show(provForAnalytics, provIndices, schoolIndex, scoreMeta, currentScores, year);
    } else {
      AnalyticsPanel.hide();
    }
  }

  const debouncedFilter = debounce(() => applyFilters(), 280);

  function bindEvents() {
    $('search-name').addEventListener('input', debouncedFilter);
    $('filter-province').addEventListener('change', () => applyFilters());
    $('filter-year').addEventListener('change', () => applyFilters());
    $('score-min').addEventListener('change', () => applyFilters());
    $('score-max').addEventListener('change', () => applyFilters());

    ['filter-types', 'filter-natures'].forEach(id => {
      $(id).addEventListener('change', () => applyFilters());
    });

    $('reset-filters').addEventListener('click', () => {
      $('search-name').value = '';
      $('filter-province').value = '';
      setCheckedValues('filter-types', []);
      setCheckedValues('filter-natures', []);
      $('filter-year').value = '2025';
      $('score-min').value = '';
      $('score-max').value = '';
      selectedProv = '';
      applyFilters({ resetView: true });
    });

    $('toggle-panel').addEventListener('click', () => {
      $('filter-panel').classList.toggle('collapsed');
      $('toggle-panel').textContent = $('filter-panel').classList.contains('collapsed') ? '+' : '−';
      setTimeout(() => SchoolMap.update(filteredIndices, selectedProv), 320);
    });

    $('close-analytics').addEventListener('click', () => AnalyticsPanel.hide());

    SchoolMap.onClick(ev => {
      if (ev.type === 'school') {
        const school = getFullSchool(ev.idx);
        const bk = baikeScores[school.code] || school.baikeScores;
        SchoolModal.show(school, bk, $('filter-year').value);
      } else if (ev.type === 'province') {
        const nextProv = selectedProv === ev.province ? '' : ev.province;
        selectedProv = nextProv;
        $('filter-province').value = nextProv;
        applyFilters({ analyticsProv: nextProv || undefined, resetView: true });
      }
    });

    SchoolModal.bindEvents();
  }

  async function init() {
    try {
      await loadData();
      bindEvents();
    } catch (err) {
      setLoading(false);
      $('map-container').innerHTML = '<div style="padding:40px;text-align:center;color:#64748b"><h3>数据加载失败</h3><p>' + err.message + '</p></div>';
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();