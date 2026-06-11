const SchoolMap = (() => {
  let chart = null;
  let schoolLookup = [];
  let pendingUpdate = null;
  let hoverIdx = null;
  let lastSelectedProv = null;

  const PROVINCE_MAP = {
    '北京': '北京市', '天津': '天津市', '河北': '河北省', '山西': '山西省',
    '内蒙古': '内蒙古自治区', '辽宁': '辽宁省', '吉林': '吉林省', '黑龙江': '黑龙江省',
    '上海': '上海市', '江苏': '江苏省', '浙江': '浙江省', '安徽': '安徽省',
    '福建': '福建省', '江西': '江西省', '山东': '山东省', '河南': '河南省',
    '湖北': '湖北省', '湖南': '湖南省', '广东': '广东省', '广西': '广西壮族自治区',
    '海南': '海南省', '重庆': '重庆市', '四川': '四川省', '贵州': '贵州省',
    '云南': '云南省', '西藏': '西藏自治区', '陕西': '陕西省', '甘肃': '甘肃省',
    '青海': '青海省', '宁夏': '宁夏回族自治区', '新疆': '新疆维吾尔自治区',
  };

  const GEO_PROVINCES = [
    '北京市', '天津市', '河北省', '山西省', '内蒙古自治区', '辽宁省', '吉林省', '黑龙江省',
    '上海市', '江苏省', '浙江省', '安徽省', '福建省', '江西省', '山东省', '河南省',
    '湖北省', '湖南省', '广东省', '广西壮族自治区', '海南省', '重庆市', '四川省', '贵州省',
    '云南省', '西藏自治区', '陕西省', '甘肃省', '青海省', '宁夏回族自治区', '新疆维吾尔自治区',
  ];

  const BLUE = {
    normal: '#e2e8f0',
    hover: '#bfdbfe',
    border: '#2563eb',
  };

  const MAP_BORDER = { borderColor: '#94a3b8', borderWidth: 0.8 };

  function mapAreaStyle(areaColor) {
    return { areaColor, ...MAP_BORDER };
  }

  function mapInteractStates(hoverColor = BLUE.hover) {
    return {
      emphasis: {
        focus: 'none',
        itemStyle: { areaColor: hoverColor, borderColor: BLUE.border, borderWidth: 1.2 },
        label: { show: true, color: '#1e293b', fontSize: 11 },
      },
      blur: {
        itemStyle: mapAreaStyle(BLUE.normal),
      },
      select: {
        disabled: true,
        itemStyle: mapAreaStyle(BLUE.normal),
      },
    };
  }

  function provinceRegionNormal(name, selectedProv) {
    const isSelected = name === selectedProv;
    if (isSelected) {
      return {
        name,
        itemStyle: {
          areaColor: BLUE.normal,
          borderColor: BLUE.border,
          borderWidth: 2.5,
          shadowColor: 'rgba(37,99,235,0.3)',
          shadowBlur: 6,
        },
        emphasis: {
          focus: 'none',
          itemStyle: {
            areaColor: BLUE.normal,
            borderColor: BLUE.border,
            borderWidth: 3,
          },
        },
        blur: {
          itemStyle: {
            areaColor: BLUE.normal,
            borderColor: BLUE.border,
            borderWidth: 2.5,
          },
        },
        select: {
          disabled: true,
          itemStyle: mapAreaStyle(BLUE.normal),
        },
      };
    }
    return {
      name,
      itemStyle: mapAreaStyle(BLUE.normal),
      emphasis: {
        focus: 'none',
        itemStyle: { areaColor: BLUE.hover, borderColor: BLUE.border, borderWidth: 1 },
      },
      blur: {
        itemStyle: mapAreaStyle(BLUE.normal),
      },
      select: {
        disabled: true,
        itemStyle: mapAreaStyle(BLUE.normal),
      },
    };
  }

  const MAP_GRADIENT = ['#eff6ff', '#93c5fd', '#2563eb'];
  const NATIONAL_CENTER = [105, 36];
  const NATIONAL_ZOOM = 1.2;

  const GEO_ROAM = {
    roam: true,
    scaleLimit: { min: 0.3, max: 60 },
  };

  function assetBase() {
    const p = window.location.pathname.replace(/\/[^/]*$/, '');
    return `${window.location.origin}${p}`;
  }

  function logoHref(idx) {
    const s = schoolLookup[idx];
    if (!s?.c) return null;
    const base = assetBase();
    if (s.l) return `${base}/${s.l.replace(/^\//, '')}`;
    return `${base}/assets/logos/${s.c}.svg`;
  }

  function buildProvinceData(indices, selectedProv) {
    const counts = Object.create(null);
    for (let i = 0; i < indices.length; i++) {
      const p = schoolLookup[indices[i]].p;
      counts[p] = (counts[p] || 0) + 1;
    }
    const uniformStyle = selectedProv
      ? { areaColor: BLUE.normal, borderColor: '#94a3b8', borderWidth: 0.8 }
      : null;
    return GEO_PROVINCES.map(name => {
      const item = {
        name,
        value: counts[name] || 0,
        itemStyle: uniformStyle ? { ...uniformStyle } : mapAreaStyle(BLUE.normal),
        emphasis: {
          itemStyle: { areaColor: BLUE.hover, borderColor: BLUE.border, borderWidth: 1.2 },
        },
        blur: {
          itemStyle: mapAreaStyle(BLUE.normal),
        },
        select: {
          disabled: true,
          itemStyle: mapAreaStyle(BLUE.normal),
        },
      };
      return item;
    });
  }

  function getGeoZoom() {
    if (!chart) return NATIONAL_ZOOM;
    const geo = chart.getOption()?.geo;
    const g = Array.isArray(geo) ? geo[0] : geo;
    return g?.zoom ?? NATIONAL_ZOOM;
  }

  function computeMinSeparation(count, zoom, symbolSize) {
    const z = Math.max(zoom, 1);
    const sizeFactor = symbolSize / 12;
    if (count <= 60) return Math.max(0.014, (0.38 * sizeFactor) / z);
    if (count <= 120) return Math.max(0.01, (0.28 * sizeFactor) / z);
    if (count <= 300) return Math.max(0.006, (0.17 * sizeFactor) / z);
    return Math.max(0.0032, (0.09 * sizeFactor) / z);
  }

  function repulsePair(a, b, minSep) {
    let dx = b.lng - a.lng;
    let dy = b.lat - a.lat;
    let d2 = dx * dx + dy * dy;
    const min2 = minSep * minSep;
    if (d2 >= min2) return;

    if (d2 < 1e-16) {
      const ang = ((a.i + 1) * (b.i + 3) * 137.508) % 360 * Math.PI / 180;
      dx = Math.cos(ang) * 1e-8;
      dy = Math.sin(ang) * 1e-8;
      d2 = dx * dx + dy * dy;
    }
    const d = Math.sqrt(d2);
    const push = (minSep - d) * 0.62;
    const ux = dx / d;
    const uy = dy / d;
    a.lng -= ux * push;
    a.lat -= uy * push;
    b.lng += ux * push;
    b.lat += uy * push;
  }

  function spreadOverlappingPoints(indices, minSep) {
    if (indices.length <= 1 || minSep <= 0) {
      return indices.map(idx => {
        const s = schoolLookup[idx];
        return { idx, lng: s.lng, lat: s.lat };
      });
    }

    const nodes = indices.map((idx, i) => {
      const s = schoolLookup[idx];
      return { idx, i, ox: s.lng, oy: s.lat, lng: s.lng, lat: s.lat };
    });

    const maxDrift = minSep * 5;
    const iterations = nodes.length > 400 ? 18 : nodes.length > 150 ? 26 : 38;
    const cellSize = minSep;

    for (let t = 0; t < iterations; t++) {
      if (nodes.length > 120) {
        const grid = new Map();
        for (const n of nodes) {
          const key = `${Math.floor(n.lng / cellSize)},${Math.floor(n.lat / cellSize)}`;
          if (!grid.has(key)) grid.set(key, []);
          grid.get(key).push(n);
        }
        for (const n of nodes) {
          const cx = Math.floor(n.lng / cellSize);
          const cy = Math.floor(n.lat / cellSize);
          for (let gx = cx - 1; gx <= cx + 1; gx++) {
            for (let gy = cy - 1; gy <= cy + 1; gy++) {
              const bucket = grid.get(`${gx},${gy}`);
              if (!bucket) continue;
              for (const m of bucket) {
                if (m.i >= n.i) continue;
                repulsePair(n, m, minSep);
              }
            }
          }
        }
      } else {
        for (let i = 0; i < nodes.length; i++) {
          for (let j = i + 1; j < nodes.length; j++) {
            repulsePair(nodes[i], nodes[j], minSep);
          }
        }
      }
    }

    for (const n of nodes) {
      const dx = n.lng - n.ox;
      const dy = n.lat - n.oy;
      const d = Math.hypot(dx, dy);
      if (d > maxDrift) {
        const s = maxDrift / d;
        n.lng = n.ox + dx * s;
        n.lat = n.oy + dy * s;
      }
    }

    return nodes;
  }

  function buildScatterData(indices) {
    const count = indices.length;
    const baseSize = count <= 50 ? 20 : count <= 100 ? 17 : count <= 300 ? 13 : 10;
    const minSep = computeMinSeparation(count, getGeoZoom(), baseSize);
    const positions = spreadOverlappingPoints(indices, minSep);
    const data = new Array(positions.length);

    for (let i = 0; i < positions.length; i++) {
      const { idx, lng, lat } = positions[i];
      const s = schoolLookup[idx];
      const isHover = hoverIdx === idx;

      data[i] = {
        name: s.n,
        value: [lng, lat],
        idx,
        symbol: 'circle',
        symbolSize: isHover ? baseSize + 6 : baseSize,
        itemStyle: {
          color: isHover ? '#dc2626' : '#2563eb',
          borderColor: '#fff',
          borderWidth: 1.5,
          shadowBlur: isHover ? 8 : 2,
          shadowColor: 'rgba(37,99,235,0.45)',
        },
        z: isHover ? 20 : 10,
      };
    }
    return data;
  }

  function calcFitView(indices) {
    if (!indices.length) return { center: NATIONAL_CENTER, zoom: NATIONAL_ZOOM };
    let minLng = Infinity;
    let maxLng = -Infinity;
    let minLat = Infinity;
    let maxLat = -Infinity;
    for (let i = 0; i < indices.length; i++) {
      const s = schoolLookup[indices[i]];
      if (s.lng < minLng) minLng = s.lng;
      if (s.lng > maxLng) maxLng = s.lng;
      if (s.lat < minLat) minLat = s.lat;
      if (s.lat > maxLat) maxLat = s.lat;
    }

    const count = indices.length;
    const minSpan = 0.004;
    const pad = count <= 50 ? 0.004 : count <= 100 ? 0.006 : count <= 200 ? 0.02 : 0.06;
    const lngSpan = Math.max(maxLng - minLng, minSpan) + pad;
    const latSpan = Math.max(maxLat - minLat, minSpan) + pad;
    const span = Math.max(lngSpan, latSpan);

    const zoomBase = count <= 50 ? 120000 : count <= 100 ? 90000 : count <= 200 ? 35000 : 500;
    const maxZoom = count <= 100 ? 28 : count <= 200 ? 24 : 18;
    const zoom = Math.min(maxZoom, Math.max(5, Math.log2(zoomBase / span)));

    return {
      center: [(minLng + maxLng) / 2, (minLat + maxLat) / 2],
      zoom,
    };
  }

  function buildRegions(selectedProv) {
    return GEO_PROVINCES.map(name => provinceRegionNormal(name, selectedProv || ''));
  }

  function clearMapHighlight() {
    if (!chart) return;
    chart.dispatchAction({ type: 'downplay', seriesIndex: 0 });
    chart.dispatchAction({ type: 'unselect', seriesIndex: 0 });
    chart.dispatchAction({ type: 'downplay', geoIndex: 0 });
    chart.dispatchAction({ type: 'unselect', geoIndex: 0 });
    for (const name of GEO_PROVINCES) {
      chart.dispatchAction({ type: 'downplay', seriesIndex: 0, name });
      chart.dispatchAction({ type: 'unselect', seriesIndex: 0, name });
      chart.dispatchAction({ type: 'downplay', geoIndex: 0, name });
      chart.dispatchAction({ type: 'unselect', geoIndex: 0, name });
    }
    chart.dispatchAction({ type: 'hideTip' });
  }

  function scatterSeriesOption(indices) {
    return {
      id: 'school-scatter',
      data: buildScatterData(indices),
      large: false,
      clip: false,
    };
  }

  function initBaseOption() {
    chart.setOption({
      color: MAP_GRADIENT,
      backgroundColor: '#f8fafc',
      animation: false,
      animationDurationUpdate: 0,
      tooltip: {
        trigger: 'item',
        confine: true,
        transitionDuration: 0,
        formatter(params) {
          if (params.seriesType === 'scatter') {
            const s = schoolLookup[params.data.idx];
            if (!s) return '';
            const href = logoHref(params.data.idx);
            const img = href
              ? `<img src="${href}" style="width:28px;height:28px;border-radius:4px;vertical-align:middle;margin-right:6px" onerror="this.style.display='none'">`
              : '';
            return `${img}<b>${s.n}</b><br/>${s.p} · ${s.t}`;
          }
          if (params.seriesType === 'map') {
            const raw = params.data?.value ?? params.value;
            const val = Number.isFinite(Number(raw)) ? Number(raw) : 0;
            return `${params.name}<br/>符合筛选：<b>${val}</b> 所`;
          }
          return params.name;
        },
      },
      visualMap: {
        show: true,
        min: 0,
        max: 100,
        left: 20,
        bottom: 40,
        seriesIndex: 0,
        calculable: false,
        text: ['多', '少'],
        inRange: { color: MAP_GRADIENT },
        outOfRange: { color: BLUE.normal },
        textStyle: { color: '#64748b', fontSize: 11 },
        emphasis: {
          itemStyle: { areaColor: BLUE.hover, borderColor: BLUE.border },
        },
      },
      geo: {
        id: 'china-geo',
        map: 'china',
        ...GEO_ROAM,
        zoom: NATIONAL_ZOOM,
        center: NATIONAL_CENTER,
        label: { show: false },
        selectedMode: false,
        itemStyle: mapAreaStyle(BLUE.normal),
        ...mapInteractStates(),
        select: { disabled: true },
        stateAnimation: { duration: 0 },
        regions: buildRegions(''),
      },
      series: [
        {
          id: 'province-map',
          name: '院校分布',
          type: 'map',
          map: 'china',
          geoIndex: 0,
          zlevel: 0,
          silent: false,
          selectedMode: false,
          select: { disabled: true },
          data: [],
          ...mapInteractStates(),
        },
        {
          id: 'school-scatter',
          name: '院校',
          type: 'scatter',
          coordinateSystem: 'geo',
          geoIndex: 0,
          zlevel: 1,
          z: 10,
          large: false,
          clip: false,
          data: [],
        },
      ],
    });
  }

  async function init(containerId, schools) {
    const el = document.getElementById(containerId);
    chart = echarts.init(el, null, { renderer: 'canvas' });
    schoolLookup = schools;

    const geoResp = await fetch('data/geo/china.json');
    echarts.registerMap('china', await geoResp.json());
    initBaseOption();

    chart.on('mouseover', p => {
      if (p.seriesType === 'scatter' && p.data?.idx != null && hoverIdx !== p.data.idx) {
        hoverIdx = p.data.idx;
        refreshScatterOnly();
      }
    });
    chart.on('mouseout', p => {
      if (p.seriesType === 'map' || p.componentType === 'geo') {
        if (p.name) {
          chart.dispatchAction({ type: 'downplay', seriesIndex: 0, name: p.name });
          chart.dispatchAction({ type: 'downplay', geoIndex: 0, name: p.name });
          chart.dispatchAction({ type: 'unselect', seriesIndex: 0, name: p.name });
          chart.dispatchAction({ type: 'unselect', geoIndex: 0, name: p.name });
        } else {
          clearMapHighlight();
        }
      }
    });
    chart.on('globalout', () => {
      clearMapHighlight();
      if (hoverIdx != null) {
        hoverIdx = null;
        refreshScatterOnly();
      }
    });

    let roamTimer;
    chart.on('georoam', () => {
      clearTimeout(roamTimer);
      roamTimer = setTimeout(() => refreshScatterOnly(), 120);
    });

    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => chart?.resize(), 150);
    });
    return chart;
  }

  let lastIndices = [];

  function refreshScatterOnly() {
    chart.setOption({
      series: [scatterSeriesOption(lastIndices)],
    }, { lazyUpdate: false });
  }

  function flushUpdate(indices, selectedProv, resetView) {
    lastIndices = indices;
    const provinceData = buildProvinceData(indices, selectedProv);
    const maxVal = Math.max(...provinceData.map(d => d.value), 1);
    const hasSelection = !!selectedProv;

    clearMapHighlight();

    const regions = buildRegions(selectedProv);

    const geoPatch = {
      id: 'china-geo',
      map: 'china',
      ...GEO_ROAM,
      selectedMode: false,
      regions,
      itemStyle: mapAreaStyle(BLUE.normal),
      ...mapInteractStates(),
      select: { disabled: true },
      stateAnimation: { duration: 0 },
    };

    if (resetView) {
      const view = hasSelection ? calcFitView(indices) : { center: NATIONAL_CENTER, zoom: NATIONAL_ZOOM };
      geoPatch.center = view.center;
      geoPatch.zoom = view.zoom;
    }

    chart.setOption({
      visualMap: {
        show: !hasSelection,
        min: 0,
        max: maxVal,
        seriesIndex: hasSelection ? -1 : 0,
        calculable: false,
        inRange: { color: MAP_GRADIENT },
        outOfRange: { color: BLUE.normal },
        emphasis: {
          itemStyle: { areaColor: BLUE.hover, borderColor: BLUE.border },
        },
      },
      geo: geoPatch,
      series: [
        {
          id: 'province-map',
          data: provinceData,
          selectedMode: false,
          select: { disabled: true },
          ...mapInteractStates(),
        },
        scatterSeriesOption(indices),
      ],
    }, { lazyUpdate: false, replaceMerge: ['geo'] });

    requestAnimationFrame(() => clearMapHighlight());
  }

  function update(indices, selectedProv, opts = {}) {
    if (!chart) return;
    const provChanged = selectedProv !== lastSelectedProv;
    lastSelectedProv = selectedProv;
    const resetView = opts.resetView === true || provChanged;

    if (pendingUpdate) cancelAnimationFrame(pendingUpdate);
    pendingUpdate = requestAnimationFrame(() => {
      pendingUpdate = null;
      flushUpdate(indices, selectedProv, resetView);
    });
  }

  function onClick(handler) {
    chart.off('click');
    chart.on('click', params => {
      if (params.seriesType === 'scatter' && params.data?.idx != null) {
        handler({ type: 'school', idx: params.data.idx });
        return;
      }
      const provShort = params.name;
      if (!provShort) return;
      if (params.seriesType === 'map' || params.componentType === 'geo') {
        handler({ type: 'province', province: PROVINCE_MAP[provShort] || provShort });
      }
    });
  }

  return { init, update, onClick, PROVINCE_MAP };
})();
