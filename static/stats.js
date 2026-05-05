let charts = {};
echarts.registerTheme('inter', { textStyle: { fontFamily: "'Inter', system-ui, sans-serif" } });

let overviewCache = null; // /api/stats/overview/ 的结果缓存
let yearCache = {};       // { "2026": {monthly_counts, heatmap, heatmap_max} }

async function initStatsPage() {
    try {
        // 1) 拉取后端聚合好的 overview
        const res = await fetch(`/api/${window.SITE_USER}/stats/overview/`);
        overviewCache = await res.json();

        // 2) 初始化筛选菜单（airline/airport/model 下拉）
        initFilters(overviewCache.filters);

        // 3) 渲染所有图表
        renderAllStatistics(overviewCache);

        // 4) 监听窗口缩放
        window.addEventListener('resize', () => {
            Object.values(charts).forEach(c => c && c.resize && c.resize());
        });

    } catch (err) {
        console.error("Stats 初始化失败:", err);
    }
}

// --- 核心同步逻辑 ---
function syncGlobalYear(year) {
    const monthlySel = document.getElementById('monthly-year-select');
    const heatmapSel = document.getElementById('heatmap-year-select');

    if (monthlySel) monthlySel.value = year;
    if (heatmapSel) heatmapSel.value = year;

    updateMonthlyChart(year);
    updateHeatmapChart(year);
}

function renderAllStatistics(overview) {
    // A) 三个排行（饼图 + 表格）——用后端算好的 ranked
    renderRankedChartFromData(overview.ranked.airline, 'chart-airline', 'table-airline', 'Most photographed airlines');
    renderRankedChartFromData(overview.ranked.model, 'chart-model', 'table-model', 'Most photographed aircraft');
    renderRankedChartFromData(overview.ranked.airport, 'chart-airport', 'table-airport', 'Most visited airports');

    // B) 年份列表
    const years = (overview.years || []).slice().sort();
    const latestYear = overview.latest_year || years[years.length - 1];

    const populateYearSelect = (id) => {
        const select = document.getElementById(id);
        if (!select) return;
        select.innerHTML = years.slice().reverse().map(y => `<option value="${y}">${y}</option>`).join('');
    };
    populateYearSelect('monthly-year-select');
    populateYearSelect('heatmap-year-select');

    const monthlySel = document.getElementById('monthly-year-select');
    const heatmapSel = document.getElementById('heatmap-year-select');
    if (monthlySel) monthlySel.onchange = (e) => syncGlobalYear(e.target.value);
    if (heatmapSel) heatmapSel.onchange = (e) => syncGlobalYear(e.target.value);

    // C) 年度柱状图（用后端 yearly_counts）
    renderYearlyChart(years, overview.yearly_counts || {});

    // D) 默认同步到最新年份（会触发月度+热力图拉取）
    if (latestYear) syncGlobalYear(String(latestYear));
}

// --- 年度柱状图 ---
function renderYearlyChart(years, yearlyCountsMap) {
    const values = years.map(y => yearlyCountsMap[y] || 0);

    const chart = echarts.init(document.getElementById('chart-yearly'), 'inter');
    charts['chart-yearly'] = chart;

    chart.setOption({
        title: {
            text: 'Photos photographed per year',
            left: 'center',
            textStyle: { color: '#333', fontSize: 13, fontWeight: 'normal' }
        },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { top: '20%', bottom: '15%', containLabel: true },
        xAxis: {
            type: 'category',
            data: years,
            axisLine: { lineStyle: { color: '#ddd' } },
            axisLabel: { color: '#666', fontSize: 10 }
        },
        yAxis: {
            type: 'value',
            name: 'Photos photographed',
            nameLocation: 'middle',
            nameGap: 35,
            nameTextStyle: { color: '#999', fontSize: 10 },
            splitLine: { lineStyle: { type: 'dashed', color: '#eee' } },
            axisLabel: { color: '#666', fontSize: 10 }
        },
        series: [{
            data: values,
            type: 'bar',
            barWidth: '40%',
            itemStyle: { color: '#0054a6', borderRadius: [2, 2, 0, 0] }
        }]
    });

    chart.on('click', (params) => {
        window.location.href = `/${window.SITE_USER}/gallery/?year=${params.name}`;
    });
}

// --- 月度柱状图：改为后端提供 monthly_counts ---
async function updateMonthlyChart(year) {
    const data = await getYearData(year);
    const monthlyCounts = data.monthly_counts || Array(12).fill(0);

    const chart = echarts.init(document.getElementById('chart-monthly'), 'inter');
    charts['chart-monthly'] = chart;

    chart.setOption({
        title: {
            text: `Monthly photographed in ${year}`,
            left: 'center',
            textStyle: { color: '#333', fontSize: 13, fontWeight: 'normal' }
        },
        tooltip: { trigger: 'axis', formatter: '{b}: {c} photos' },
        grid: { top: '20%', bottom: '15%', containLabel: true },
        xAxis: {
            type: 'category',
            data: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            axisLabel: { fontSize: 10, color: '#666' },
            axisLine: { lineStyle: { color: '#ddd' } }
        },
        yAxis: {
            type: 'value',
            splitLine: { lineStyle: { type: 'dashed', color: '#eee' } },
            axisLabel: { color: '#666', fontSize: 10 }
        },
        series: [{
            data: monthlyCounts,
            type: 'bar',
            barWidth: '50%',
            itemStyle: { color: '#0054a6', borderRadius: [2, 2, 0, 0] }
        }]
    });

    chart.on('click', (params) => {
        const monthIndex = params.dataIndex + 1;
        const monthStr = monthIndex.toString().padStart(2, '0');
        window.location.href = `/${window.SITE_USER}/gallery/?month=${year}-${monthStr}`;
    });
}

// --- 热力图：改为后端提供 heatmap 数据 ---
async function updateHeatmapChart(year) {
    const data = await getYearData(year);
    const heatmapData = data.heatmap || []; // 形如：[[dateStr, count], ...]
    const maxVal = (typeof data.heatmap_max === 'number') ? data.heatmap_max : 5;

    const chart = echarts.init(document.getElementById('chart-heatmap'), 'inter');
    charts['chart-heatmap'] = chart;

    chart.setOption({
        visualMap: {
            show: false,
            min: 0,
            max: maxVal,
            inRange: { color: ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'] }
        },
        calendar: {
            top: 30,
            left: 30,
            right: 30,
            range: year,
            cellSize: ['auto', 13],
            dayLabel: { fontSize: 10, firstDay: 1, color: '#999' },
            monthLabel: { fontSize: 10, color: '#999' },
            itemStyle: { borderWidth: 2, borderColor: '#fff' },
            splitLine: { show: false }
        },
        series: { type: 'heatmap', coordinateSystem: 'calendar', data: heatmapData }
    });

    chart.on('click', (params) => {
        if (params.data && params.data[0]) {
            window.location.href = `/${window.SITE_USER}/gallery/?date=${params.data[0]}`;
        }
    });
}

// --- 饼图 + 表格：改为直接吃后端 ranked 数据 ---
function renderRankedChartFromData(sorted, chartId, tableId, titleText) {
    sorted = Array.isArray(sorted) ? sorted : [];
    const total = sorted.reduce((s, x) => s + (x.value || 0), 0) || 1;
    const isAirport = (tableId === 'table-airport');

    // 表格：最多 15 条
    const tbody = document.getElementById(tableId);
    if (tbody) {
        tbody.innerHTML = sorted.slice(0, 15).map((item, index) => {
            let displayName = item.name;
            if (isAirport && typeof AIRPORT_DATA !== 'undefined' && AIRPORT_DATA[item.name]) {
                displayName = `${AIRPORT_DATA[item.name].n} (${item.name})`;
            }
            let field = '';
            if (chartId === 'chart-airline') field = 'airline';
            else if (chartId === 'chart-model') field = 'model';
            else if (chartId === 'chart-airport') field = 'airport';
            const url = `/${window.SITE_USER}/gallery/?${field}=${encodeURIComponent(item.name)}`;

            return `
            <tr>
                <td class="font-bold text-gray-400 w-8">${index + 1}</td>
                <td class="font-bold whitespace-nowrap overflow-hidden text-ellipsis max-w-[150px]"><a href="${url}" class="hover:underline hover:text-blue-500">${displayName}</a></td>
                <td class="text-right">${item.value}</td>
                <td class="text-right text-blue-500 font-medium">${((item.value / total) * 100).toFixed(1)}%</td>
            </tr>
        `;
        }).join('');
    }

    // 饼图：前 9 + Other
    let chartData = sorted.slice(0, 9).map(item => {
        let name = item.name;
        if (isAirport && typeof AIRPORT_DATA !== 'undefined' && AIRPORT_DATA[item.name]) {
            name = AIRPORT_DATA[item.name].n;
        }
        return { name, value: item.value, original_key: item.name };
    });
    const otherVal = sorted.slice(9).reduce((sum, curr) => sum + (curr.value || 0), 0);
    if (otherVal > 0) chartData = chartData.concat([{ name: 'Other', value: otherVal }]);

    const chart = echarts.init(document.getElementById(chartId), 'inter');
    charts[chartId] = chart;

    chart.setOption({
        title: {
            text: titleText,
            left: 'center',
            textStyle: { color: '#333', fontSize: 13, fontWeight: 'normal' }
        },
        tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
        series: [{
            type: 'pie',
            radius: '65%',
            center: ['50%', '60%'],
            itemStyle: { borderRadius: 0, borderColor: '#fff', borderWidth: 1 },
            label: {
                show: true,
                position: 'outside',
                formatter: '{b}',
                fontSize: 10,
                color: '#666'
            },
            data: chartData,
            color: ['#002a52', '#003d73', '#005199', '#0066bf', '#1a80d9', '#3396ed', '#55aaf0', '#7bbef5', '#a0d2f9', '#c5e4fc']
        }]
    });

    chart.on('click', (params) => {
        if (params.name === 'Other') return;

        let field = '';
        if (chartId === 'chart-airline') field = 'airline';
        else if (chartId === 'chart-model') field = 'model';
        else if (chartId === 'chart-airport') field = 'airport';

        if (field && params.data && params.data.original_key) {
            window.location.href = `/${window.SITE_USER}/gallery/?${field}=${encodeURIComponent(params.data.original_key)}`;
        }
    });
}

// --- 基础过滤逻辑 ---
function createStatsAutocomplete(input, getItems) {
    if (!input) return;
    const wrapper = input.parentElement;
    const list = document.createElement('ul');
    list.style.position = 'absolute';
    list.style.top = '100%';
    list.style.left = '0';
    list.style.width = '100%';
    list.style.maxHeight = '350px';
    list.style.overflowY = 'auto';
    list.style.backgroundColor = '#fff';
    list.style.border = '1px solid #ddd';
    list.style.borderRadius = '2px';
    list.style.boxShadow = '0 4px 6px -1px rgba(0,0,0,0.1)';
    list.style.zIndex = '1000';
    list.style.display = 'none';
    list.style.margin = '0';
    list.style.padding = '0';
    list.style.listStyle = 'none';
    wrapper.appendChild(list);

    function show() { list.style.display = 'block'; }
    function hide() { setTimeout(() => { list.style.display = 'none'; }, 200); }

    function updateList(query) {
        list.innerHTML = '';
        const items = getItems() || [];
        const normalizedQuery = (query || '').trim().toLowerCase();
        const filtered = normalizedQuery
            ? items.filter(i => i.toLowerCase().includes(normalizedQuery))
            : items;

        if (filtered.length === 0) {
            hide();
            return;
        }

        filtered.slice(0, 500).forEach(item => {
            const li = document.createElement('li');
            li.style.padding = '8px 12px';
            li.style.cursor = 'pointer';
            li.style.fontSize = '12px';
            li.style.borderBottom = '1px solid #f9f9f9';

            // Highlight match
            if (normalizedQuery) {
                const idx = item.toLowerCase().indexOf(normalizedQuery);
                const before = item.substring(0, idx);
                const match = item.substring(idx, idx + normalizedQuery.length);
                const after = item.substring(idx + normalizedQuery.length);
                li.innerHTML = `${before}<strong>${match}</strong>${after}`;
            } else {
                li.textContent = item;
            }

            li.onclick = () => {
                input.value = item;
                list.style.display = 'none';
            };
            li.onmouseover = () => { li.style.backgroundColor = '#f3f4f6'; };
            li.onmouseout = () => { li.style.backgroundColor = 'transparent'; };
            list.appendChild(li);
        });
        show();
    }

    input.addEventListener('input', (e) => updateList(e.target.value));
    input.addEventListener('focus', (e) => updateList(e.target.value));
    input.addEventListener('blur', hide);
}

function initFilters(filters) {
    createStatsAutocomplete(document.getElementById('select-airline'), () => (filters && filters.airlines) || []);
    createStatsAutocomplete(document.getElementById('select-airport'), () => (filters && filters.airports) || []);
    createStatsAutocomplete(document.getElementById('select-model'), () => (filters && filters.models) || []);
}


// 跳转到 gallery（Django 路由）
function applyFilters() {
    const filters = {
        airline: document.getElementById('select-airline').value,
        airport: document.getElementById('select-airport').value,
        model: document.getElementById('select-model').value,
        featured: document.getElementById('select-featured').value,
        is_special_livery: document.getElementById('select-is_special_livery').value,
        is_cargo: document.getElementById('select-is_cargo').value,
        is_bizjet: document.getElementById('select-is_bizjet').value,
        is_helicopter: document.getElementById('select-is_helicopter').value,
        is_rare: document.getElementById('select-is_rare').value,
    };
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => { if (v) params.append(k, v); });
    window.location.href = `/${window.SITE_USER}/gallery/?${params.toString()}`;
}

// --- 年数据缓存层 ---
async function getYearData(year) {
    year = String(year);
    if (yearCache[year]) return yearCache[year];

    const res = await fetch(`/api/${window.SITE_USER}/stats/year/?year=${encodeURIComponent(year)}`);
    const data = await res.json();
    yearCache[year] = data;
    return data;
}

initStatsPage();

function performNavSearch() {
    const input = document.getElementById('nav-search-input');
    const query = input.value.trim();
    if (query) {
        window.location.href = `/${window.SITE_USER}/gallery/?q=${encodeURIComponent(query)}`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('nav-search-input');
    if (searchInput) {
        searchInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') performNavSearch();
        });
    }
});


