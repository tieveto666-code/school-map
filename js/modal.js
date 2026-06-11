const SchoolModal = (() => {
  const overlay = () => document.getElementById('modal-overlay');
  const content = () => document.getElementById('modal-content');

  function renderBaikeScores(baikeScores, year) {
    if (!baikeScores?.rows?.length) {
      return '<p class="no-data">暂无百度百科录取分数线数据，请访问词条查看</p>';
    }
    const rows = year
      ? baikeScores.rows.filter(r => String(r[0]) === String(year))
      : baikeScores.rows;
    const displayRows = rows.length ? rows : baikeScores.rows;
    const headers = baikeScores.headers || ['年份', '招生省份', '批次', '最低分/最低位次', '专业组'];
    return `
      <p class="baike-source">数据来源：${baikeScores.source || '百度百科'} ·
        <a href="${baikeScores.sourceUrl}" target="_blank" rel="noopener">查看词条</a></p>
      <table class="baike-table">
        <thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead>
        <tbody>${displayRows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody>
      </table>`;
  }

  function show(school, baikeScores, year) {
    const el = content();
    const logoPath = school.logo || school.l;
    const logoHtml = logoPath
      ? `<img class="modal-logo" src="${logoPath}" alt="${school.name}" onerror="this.outerHTML='<div class=\\'modal-logo-fallback\\'>${school.name[0]}</div>'">`
      : `<div class="modal-logo-fallback">${school.name[0]}</div>`;

    const photoHtml = school.photo
      ? `<img class="modal-photo" src="${school.photo}" alt="${school.name}校园" onerror="this.style.display='none'">`
      : '';

    const tags = [];
    if (school.is985) tags.push('<span class="tag tag-985">985</span>');
    if (school.is211) tags.push('<span class="tag tag-211">211</span>');
    if (school.isDoubleFirstClass) tags.push('<span class="tag">双一流</span>');
    tags.push(`<span class="tag">${school.schoolType || school.t}</span>`);
    (school.natures || school.ns || []).forEach(n => tags.push(`<span class="tag">${n}</span>`));

    const majorsHtml = school.majors?.length
      ? `<ul>${school.majors.map(m => `<li>${m}</li>`).join('')}</ul>`
      : '<p class="no-data">暂无学科评估数据</p>';

    const baikeUrl = school.baikeUrl || `https://baike.baidu.com/item/${encodeURIComponent(school.name)}`;
    const links = [];
    if (school.website) links.push(`<a class="modal-link" href="${school.website}" target="_blank" rel="noopener">学校官网 →</a>`);
    links.push(`<a class="modal-link" href="${baikeUrl}" target="_blank" rel="noopener">百度百科词条 →</a>`);

    const scores = baikeScores || school.baikeScores;

    el.innerHTML = `
      ${photoHtml}
      <div class="modal-header">
        ${logoHtml}
        <div>
          <div class="modal-title">${school.name}</div>
          <div class="modal-tags">${tags.join('')}</div>
        </div>
      </div>
      <div class="modal-section">
        <h4>基本信息</h4>
        <p>所在地：${school.province || school.p} ${school.location || ''}</p>
        <p>主管部门：${school.department || '—'}</p>
      </div>
      ${school.intro ? `<div class="modal-section"><h4>学校简介</h4><p>${school.intro}</p></div>` : ''}
      <div class="modal-section"><h4>重点专业</h4>${majorsHtml}</div>
      <div class="modal-section">
        <h4>录取分数线（百度百科）</h4>
        <div class="score-info">${renderBaikeScores(scores, year)}</div>
      </div>
      <div class="modal-links">${links.join(' ')}</div>
    `;

    overlay().classList.remove('hidden');
  }

  function hide() {
    overlay().classList.add('hidden');
  }

  function bindEvents() {
    document.getElementById('modal-close').addEventListener('click', hide);
    overlay().addEventListener('click', e => { if (e.target === overlay()) hide(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') hide(); });
  }

  return { show, hide, bindEvents };
})();
