// 洗牌（保留）
function shuffle(array) {
  return array.sort(() => Math.random() - 0.5);
}

// 同步 gear-list -> gear-list-mobile
function syncGear() {
  const desktop = document.getElementById('gear-list');
  const mobile = document.getElementById('gear-list-mobile');
  if (desktop && mobile && mobile.innerHTML.trim() === '') {
    mobile.innerHTML = desktop.innerHTML;
  }
}

// ✅ 拉取站点配置：/api/site/
async function fetchSite() {
  try {
    const r = await fetch(`/api/${window.SITE_USER}/site/`);
    if (!r.ok) return null;
    const data = await r.json();
    return data && data.site ? data.site : null;
  } catch (e) {
    return null;
  }
}

function applySiteToHeader(site) {
  const nameEl = document.getElementById('site-display-name');

  if (!site) {
    if (nameEl) nameEl.innerText = window.SITE_USER;
    return;
  }

  const banner = document.getElementById('site-banner');
  if (banner && site.banner) {
    banner.style.backgroundImage = `url('${site.banner}')`;
  }

  const avatar = document.getElementById('site-avatar');
  if (avatar && site.avatar) {
    avatar.src = site.avatar;
  }
}

function renderPhotographerInfo(site) {
  const gearListContainer = document.getElementById('gear-list');
  if (!gearListContainer) return;

  const location = site?.location || "Not specified";
  const hobbies = site?.hobbies || "Not specified";

  // 新 [{id,name}]
  let cameras = site?.gear?.cameras;
  let lenses = site?.gear?.lenses;

  if (!Array.isArray(cameras)) cameras = [];
  if (!Array.isArray(lenses)) lenses = [];

  let gearHtml = '';

  gearHtml += `
    <div class="mb-5">
      <h4 class="text-[11px] font-black text-blue-600 uppercase tracking-[0.2em] mb-2 flex items-center">
        <i class="fa fa-map-marker-alt w-6 mr-2"></i> LOCATION
      </h4>
      <p class="text-gray-900 font-bold ml-8">${location}</p>
    </div>`;

  // cameras
  if (cameras.length) {
    gearHtml += `
      <div class="mb-5">
        <h4 class="text-[11px] font-black text-blue-600 uppercase tracking-[0.2em] mb-2 flex items-center">
          <i class="fa fa-camera w-6 mr-2"></i> CAMERA BODIES
        </h4>
        <div class="space-y-1.5">`;

    cameras.forEach(item => {
      const name = item?.name || "";
      if (name) gearHtml += `<p class="text-gray-900 font-bold ml-8">${name}</p>`;
    });

    gearHtml += `</div></div>`;
  }

  // lenses
  if (lenses.length) {
    gearHtml += `
      <div class="mb-5">
        <h4 class="text-[11px] font-black text-blue-600 uppercase tracking-[0.2em] mb-2 flex items-center">
          <i class="fa fa-circle-notch w-6 mr-2"></i> LENSES
        </h4>
        <div class="space-y-1.5">`;

    lenses.forEach(item => {
      const name = item?.name || "";
      if (name) gearHtml += `<p class="text-gray-900 font-bold ml-8">${name}</p>`;
    });

    gearHtml += `</div></div>`;
  }

  gearHtml += `
    <div class="mb-5">
      <h4 class="text-[11px] font-black text-blue-600 uppercase tracking-[0.2em] mb-2 flex items-center">
        <i class="fa fa-star w-6 mr-2"></i> HOBBIES
      </h4>
      <div class="space-y-1.5">
        <p class="text-gray-900 font-bold ml-8">${hobbies}</p>
      </div>
    </div>`;

  gearListContainer.innerHTML = gearHtml;

  // Show onboarding prompt if the user is viewing their own profile and it's mostly empty
  if (window.LOGGED_IN_USER && window.LOGGED_IN_USER === window.SITE_USER) {
    if (!site?.location && !site?.hobbies && !cameras.length && !lenses.length) {
      const prompt = document.getElementById('profile-prompt');
      if (prompt) {
        prompt.classList.remove('hidden');
      }
    }
  }

  // 同步到手机端
  syncGear();
  setTimeout(syncGear, 300);
  setTimeout(syncGear, 800);
}


// ✅ 首页主逻辑
async function initHome() {
  // 0) 先拿 site 配置并渲染到 header + photographer info
  const site = await fetchSite();
  applySiteToHeader(site);
  renderPhotographerInfo(site);

  // 1) 取 /api/home
  const res = await fetch(`/api/${window.SITE_USER}/home?latest_page=1&latest_page_size=24`);
  const payload = await res.json();

  const summary = payload.summary || {};
  const airports = payload.airports || [];
  const pinned = payload.pinned || [];
  const featured = payload.featured || [];
  const randomPhotos = payload.random || [];
  const charts = payload.charts || {};

  // 2) 统计
  document.getElementById('total-count').innerText = (summary.total || 0).toLocaleString();
  document.getElementById('count-airlines').innerText = summary.airlines || 0;
  document.getElementById('count-airports').innerText = summary.airports || 0;
  document.getElementById('count-regs').innerText = summary.regs || 0;

  // 3) 地图（你机场坐标仍在 airport-coords.js 里，所以 AIRPORT_COORDS 还要保留）
  const map = L.map('map', { zoomControl: false, attributionControl: false, maxZoom: 9 });
  // 使用高德地图 (Gaode/AMap) - 国内最稳，且配置了极简风格
  L.tileLayer('http://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7&x={x}&y={y}&z={z}', {
    subdomains: ['1', '2', '3', '4'],
    minZoom: 1,
    maxZoom: 9
  }).addTo(map);

  // （备注：Esri 注记层是可选的，这里只保留底图以维持极简风格）

  const markersGroup = L.featureGroup();

  airports.forEach(code => {
    if (typeof AIRPORT_COORDS !== 'undefined' && AIRPORT_COORDS[code]) {
      const marker = L.circleMarker(AIRPORT_COORDS[code], {
        radius: 7,
        color: 'white',
        fillColor: '#3b82f6',
        fillOpacity: 1,
        weight: 2,
        className: 'cursor-pointer'
      });

      marker.on('click', () => {
        window.location.href = `/${window.SITE_USER}/gallery/?airport=${encodeURIComponent(code)}`;
      });

      let tooltipText = `<b>${code}</b>`;
      if (typeof AIRPORT_DATA !== 'undefined' && AIRPORT_DATA[code]) {
        tooltipText = `<b>${AIRPORT_DATA[code].n} (${code})</b>`;
      }
      marker.bindTooltip(tooltipText, { direction: 'top', offset: [0, -5] });
      marker.addTo(markersGroup);
    }
  });

  markersGroup.addTo(map);
  if (airports.length > 0 && markersGroup.getLayers().length > 0) {
    map.fitBounds(markersGroup.getBounds(), { padding: [50, 50] });
  }

  // 4) 网格渲染（保留）
  const renderGrid = (containerId, photos, append = false) => {
    const container = document.getElementById(containerId);
    if (!container) return;

    const html = photos.map(p => {
      const detailUrl = `/${window.SITE_USER}/photo/?id=${p.id}`;
      const displayModel = p.sub_model || p.submodel || p.model || '';
      return `
      <div class="jet-card overflow-hidden">
        <a href="${detailUrl}" class="block">
          <div class="aspect-video overflow-hidden bg-black">
            <img src="${p.src_sm || p.src}" class="w-full h-full object-cover" loading="lazy">
          </div>
          <div class="p-2 bg-[#282828] text-[10px] grid grid-cols-2 gap-x-2 gap-y-1 text-white leading-tight">
            <div class="text-left truncate min-w-0">${p.airline}</div>
            <div class="text-right truncate min-w-0">${p.reg}</div>
            <div class="text-left truncate min-w-0">${p.date}</div>
            <div class="text-right truncate min-w-0">${displayModel}</div>
          </div>
        </a>
      </div>`;
    }).join('');

    if (append) container.insertAdjacentHTML('beforeend', html);
    else container.innerHTML = html;
  };

  // 5) pinned/featured/random
  renderGrid('pinned-grid', pinned);
  renderGrid('featured-grid', featured);
  renderGrid('random-grid', randomPhotos);

  // 6) Latest uploads：无限滚动走 /api/photos
  const PAGE_SIZE = 24;
  let latestPage = 1;
  let latestTotalPages = 1;
  let latestLoading = false;
  let latestOrdering = '-date'; // ✅ 默认按拍摄日期倒序

  const sentinel = document.getElementById('latest-sentinel');
  const loadingEl = document.getElementById('latest-loading');

  async function fetchLatest(page) {
    const params = new URLSearchParams();
    params.set("ordering", latestOrdering);
    params.set("page", String(page));
    params.set("page_size", String(PAGE_SIZE));

    const r = await fetch(`/api/${window.SITE_USER}/photos?${params.toString()}`);
    return await r.json(); // {count,total_pages,page,results}
  }

  async function loadMoreLatest(initial = false) {
    if (latestLoading) return;
    if (!initial && latestPage > latestTotalPages) return;

    latestLoading = true;
    if (loadingEl) loadingEl.classList.remove('hidden');

    try {
      const data = await fetchLatest(latestPage);
      latestTotalPages = data.total_pages || 1;

      renderGrid('latest-grid', data.results || [], !initial);
      latestPage += 1;
    } finally {
      latestLoading = false;
      if (loadingEl) loadingEl.classList.add('hidden');
    }
  }

  await loadMoreLatest(true);

  if (sentinel) {
    new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        setTimeout(() => loadMoreLatest(false), 300);
      }
    }, { rootMargin: '0px' }).observe(sentinel);
  }

  // ✅ 排序切换按钮事件 — 3-state: neutral(↕) → desc(↓) → asc(↑)
  const latestSortToggle = document.getElementById('latest-sort-toggle');
  if (latestSortToggle) {
    const arrows = { '': '↕', 'desc': '↓', 'asc': '↑' };
    const cycle = { '': 'desc', 'desc': 'asc', 'asc': 'desc' };

    function syncSortButtons() {
      const field = latestOrdering.replace(/^-/, '');
      const dir = latestOrdering.startsWith('-') ? 'desc' : 'asc';
      latestSortToggle.querySelectorAll('.sort-btn').forEach(btn => {
        const bf = btn.getAttribute('data-field');
        if (bf === field) {
          btn.setAttribute('data-dir', dir);
          btn.textContent = `${bf === 'date' ? 'Date' : 'Upload'} ${arrows[dir]}`;
          btn.classList.add('active');
        } else {
          btn.setAttribute('data-dir', '');
          btn.textContent = `${bf === 'date' ? 'Date' : 'Upload'} ${arrows['']}`;
          btn.classList.remove('active');
        }
      });
    }
    syncSortButtons();

    latestSortToggle.addEventListener('click', (e) => {
      const btn = e.target.closest('.sort-btn');
      if (!btn) return;

      const field = btn.getAttribute('data-field');
      const curDir = btn.getAttribute('data-dir');
      const isActive = btn.classList.contains('active');

      let newDir;
      if (!isActive) {
        newDir = 'desc';
      } else {
        newDir = cycle[curDir] || 'desc';
      }

      latestOrdering = (newDir === 'desc' ? '-' : '') + field;
      latestPage = 1;
      latestTotalPages = 1;

      syncSortButtons();

      // 清空并重新加载
      loadMoreLatest(true);
    });
  }

  // 7) 图表（改为用后端聚合 charts）
  initCharts(charts);
}

// 用后端聚合 charts，保持你原来的 echarts 配置尽量不动
function initCharts(charts) {
  echarts.registerTheme('inter', { textStyle: { fontFamily: "'Inter', system-ui, sans-serif" } });

  const yearly = charts.yearly || { years: [], counts: [] };
  const airline = charts.airline || { data: [] };

  const years = yearly.years || [];
  const yearlyCounts = yearly.counts || [];
  const topAirlines = airline.data || [];

  const chartYearly = echarts.init(document.getElementById('chart-growth'), 'inter');
  chartYearly.setOption({
    title: { text: 'Photos photographed per year', left: 'center', textStyle: { color: '#333', fontSize: 13, fontWeight: 'normal' } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '10%', right: '10%', bottom: '15%', top: '20%', containLabel: true },
    xAxis: { type: 'category', data: years, axisLine: { lineStyle: { color: '#ddd' } } },
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed', color: '#eee' } } },
    series: [{ name: 'Photos photographed', type: 'bar', data: yearlyCounts, barWidth: '40%', itemStyle: { color: '#0054a6', borderRadius: [2, 2, 0, 0] } }]
  });

  const chartAirline = echarts.init(document.getElementById('chart-airline'), 'inter');
  chartAirline.setOption({
    title: { text: 'Most photographed airlines', left: 'center', textStyle: { color: '#333', fontSize: 13, fontWeight: 'normal' } },
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      name: 'Airlines', type: 'pie', radius: '58%', center: ['50%', '52%'], data: topAirlines,
      color: ['#002a52', '#004080', '#0060b8', '#1a80d9', '#4da6f0', '#80c2f5', '#b3ddfb'],
      label: { position: 'outside', formatter: '{b}', fontSize: 10, color: '#333' },
      itemStyle: { borderColor: '#fff', borderWidth: 1 }
    }]
  });

  chartYearly.on('click', (params) => {
    window.location.href = `/${window.SITE_USER}/gallery/?year=${params.name}`;
  });

  chartAirline.on('click', (params) => {
    if (params.name === 'Other') return;
    window.location.href = `/${window.SITE_USER}/gallery/?airline=${encodeURIComponent(params.name)}`;
  });

  window.addEventListener('resize', () => {
    chartYearly.resize();
    chartAirline.resize();
  });
}

function performNavSearch() {
  const input = document.getElementById('nav-search-input');
  const query = input?.value?.trim();
  if (query) window.location.href = `/${window.SITE_USER}/gallery/?q=${encodeURIComponent(query)}`;
}

document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('nav-search-input');
  if (searchInput) {
    searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') performNavSearch();
    });
  }
});

initHome();
