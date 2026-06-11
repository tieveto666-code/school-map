const AnalyticsPanel = (() => {
  let pieChart = null;
  let lineChart = null;
  let onSchoolClick = null;
  let listBound = false;

  const TYPE_RANK = {
    '985': 0, '211': 1, '双一流': 2, '军队院校': 3,
    '普通一本': 4, '普通二本': 5, '其他': 6,
  };

  function init(opts = {}) {
    onSchoolClick = opts.onSchoolClick || null;
    const pieEl = document.getElementById('analytics-pie');
    const lineEl = document.getElementById('analytics-line');
    if (pieEl) pieChart = echarts.init(pieEl, null, { renderer: 'canvas' });
    if (lineEl) lineChart = echarts.init(lineEl, null, { renderer: 'canvas' });

    const listEl = document.getElementById('analytics-school-list');
    if (listEl && !listBound) {
      listBound = true;
      listEl.addEventListener('click', e => {
        const item = e.target.closest('[data-idx]');
        if (!item || !onSchoolClick) return;
        const idx = parseInt(item.dataset.idx, 10);
        if (Number.isFinite(idx)) onSchoolClick(idx);
      });
    }

    window.addEventListener('resize', () => {
      pieChart?.resize();
      lineChart?.resize();
    });
  }

  function countByType(indices, lookup) {
    const counts = Object.create(null);
    for (const i of indices) {
      const t = lookup[i].t;
      counts[t] = (counts[t] || 0) + 1;
    }
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }

  function typeTagClass(t) {
    if (t === '985') return 'tag-985';
    if (t === '211') return 'tag-211';
    if (t === '双一流') return 'tag-dfc';
    if (t === '普通一本') return 'tag-yiben';
    if (t === '普通二本') return 'tag-erben';
    return 'tag-qita';
  }

  function buildSchoolList(indices, lookup) {
    return [...indices].sort((a, b) => {
      const sa = lookup[a];
      const sb = lookup[b];
      const diff = (TYPE_RANK[sa.t] ?? 99) - (TYPE_RANK[sb.t] ?? 99);
      if (diff !== 0) return diff;
      return sa.n.localeCompare(sb.n, 'zh-CN');
    });
  }

  function avgScoresForYears(indices, lookup, byYear, years) {
    const codes = new Set(indices.map(i => lookup[i].c));
    return years.map(y => {
      const rows = byYear[y] || [];
      const scores = rows
        .filter(r => (typeof r === 'object' ? codes.has(r.code) : false))
        .map(r => r.minScore);
      if (!scores.length) return null;
      return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
    });
  }

  function renderSchoolList(indices, lookup, scores) {
    const listEl = document.getElementById('analytics-school-list');
    const titleEl = document.querySelector('.analytics-list-title');
    if (!listEl) return;

    const sorted = buildSchoolList(indices, lookup);

    if (titleEl) {
      titleEl.textContent = sorted.length
        ? `本省院校列表（筛选结果 ${sorted.length} 所）`
        : '本省院校列表（当前筛选无匹配）';
    }

    if (!sorted.length) {
      listEl.innerHTML = '<p class="school-list-empty">当前筛选条件下暂无院校</p>';
      return;
    }

    listEl.innerHTML = `<ul class="school-list">${sorted.map(idx => {
      const s = lookup[idx];
      const rec = scores?.[s.c];
      const scoreHtml = rec
        ? `<span class="school-list-score">${rec.minScore} 分</span>`
        : '';
      return `<li class="school-list-item" data-idx="${idx}" title="点击查看详情">
        <span class="school-list-name">${s.n}</span>
        <span class="school-list-meta">
          <span class="tag ${typeTagClass(s.t)}">${s.t}</span>
          ${scoreHtml}
        </span>
      </li>`;
    }).join('')}</ul>`;
  }

  function show(province, indices, lookup, scoreMeta, scores, year) {
    const panel = document.getElementById('analytics-panel');
    if (!panel) return;
    panel.classList.remove('hidden');
    document.getElementById('analytics-title').textContent = province;
    document.getElementById('analytics-summary').textContent =
      `${province}共 ${indices.length} 所院校（已套用左侧筛选条件）`;

    const typeData = countByType(indices, lookup);
    pieChart?.setOption({
      animation: false,
      color: ['#2563eb', '#1d4ed8', '#3b82f6', '#60a5fa', '#64748b', '#475569', '#334155'],
      tooltip: { trigger: 'item', formatter: '{b}: {c}所 ({d}%)' },
      legend: { bottom: 0, type: 'scroll', textStyle: { fontSize: 10 } },
      series: [{
        type: 'pie', radius: ['36%', '60%'], center: ['50%', '42%'],
        data: typeData.length ? typeData : [{ name: '暂无', value: 1 }],
        label: { fontSize: 10 },
        itemStyle: { borderColor: '#fff', borderWidth: 1 },
      }],
    }, true);

    const trendYears = [2023, 2024, 2025];
    const byYear = scoreMeta?.byYear || {};
    const avgScores = avgScoresForYears(indices, lookup, byYear, trendYears);

    lineChart?.setOption({
      animation: false,
      tooltip: { trigger: 'axis' },
      grid: { left: 42, right: 12, top: 20, bottom: 28 },
      xAxis: { type: 'category', data: trendYears.map(String), axisLabel: { fontSize: 10 } },
      yAxis: { type: 'value', name: '平均分', nameTextStyle: { fontSize: 10 }, axisLabel: { fontSize: 10 } },
      series: [{
        type: 'line', smooth: true, data: avgScores,
        itemStyle: { color: '#2563eb' },
        areaStyle: { color: 'rgba(37,99,235,.1)' },
      }],
    }, true);

    renderSchoolList(indices, lookup, scores);

    setTimeout(() => { pieChart?.resize(); lineChart?.resize(); }, 100);
  }

  function hide() {
    document.getElementById('analytics-panel')?.classList.add('hidden');
  }

  return { init, show, hide };
})();
