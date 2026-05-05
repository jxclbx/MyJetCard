// 配置参数
const ITEMS_PER_PAGE = 24; // 4x6 布局
let allData = [];          // 原始 JSON 数据
let filteredData = [];     // 过滤后的数据

// ✅ 新增：后端返回的分页信息（不改变你原有变量结构）
let totalPagesFromServer = 1;
let totalCountFromServer = 0;

// 1. 获取 URL 参数
const urlParams = new URLSearchParams(window.location.search);
let currentPage = parseInt(urlParams.get('page')) || 1;

// ✅ 排序：从 URL 读取，默认 -date（按拍摄日期倒序）
let currentOrdering = urlParams.get('ordering') || '-date';
let currentUniqueReg = urlParams.get('unique_reg') === '1';

// 2. 加载并处理数据
async function initGallery() {
    try {
        // 1. 获取所有 URL 参数 (转为对象)
        const searchParams = new URLSearchParams(window.location.search);
        const filters = Object.fromEntries(searchParams.entries());

        // 移除分页和排序参数（会手动加）
        delete filters.page;
        delete filters.ordering;
        delete filters.unique_reg;

        // ✅ 改：拼接后端 API 参数（保持你原本的"严格等值筛选"语义：key=value）
        const apiParams = new URLSearchParams(filters);
        apiParams.set('page', String(currentPage));
        apiParams.set('page_size', String(ITEMS_PER_PAGE));
        apiParams.set('ordering', currentOrdering);
        if (currentUniqueReg) {
            apiParams.set('unique_reg', '1');
        }

        const response = await fetch(`/api/${window.SITE_USER}/photos?${apiParams.toString()}`);
        const payload = await response.json();

        // ✅ 改：不再存全量 allData / filteredData（但变量名保留，减少改动）
        allData = [];
        filteredData = payload.results || [];

        // ✅ 新增：保存分页信息给 renderPagination 使用
        totalPagesFromServer = payload.total_pages || 1;
        totalCountFromServer = payload.count || 0;
        const totalRegsFromServer = payload.regs_count || 0;

        // 3. 动态更新标题（支持：n PHOTOS, m REGS）
        const filterCount = Object.keys(filters).length;
        if (filterCount > 0) {
            document.getElementById('gallery-title').innerText = 
                `FILTERED RESULTS (${totalCountFromServer} PHOTOS, ${totalRegsFromServer} REGS)`;
        } else {
            document.getElementById('gallery-title').innerText = "ALL PHOTOS";
        }

        const distinctRegsContainer = document.getElementById('distinct-regs-container');
        if (payload.distinct_regs && payload.distinct_regs.length > 0) {
            distinctRegsContainer.innerHTML = `<div class="font-bold text-yellow-700 mb-2 text-[10px] uppercase tracking-widest">Distinct Registrations (${payload.distinct_regs.length})</div><div>${payload.distinct_regs.join(', ')}</div>`;
            distinctRegsContainer.classList.remove('hidden');
        } else {
            distinctRegsContainer.innerHTML = '';
            distinctRegsContainer.classList.add('hidden');
        }

        renderPage(currentPage);
    } catch (err) {
        console.error("Gallery initialization failed:", err);
    }
}

// 3. 渲染指定页码的内容
function renderPage(page) {
    const grid = document.getElementById('photo-grid');
    if (!grid) return;
    grid.innerHTML = '';

    const pageData = filteredData;

    pageData.forEach(photo => {
        const card = document.createElement('div');
        card.className = 'photo-card overflow-hidden rounded-sm';
        const displayModel = photo.sub_model || photo.submodel || photo.model || '';
        card.innerHTML = `
            <a href="/${window.SITE_USER}/photo/?id=${photo.id}" class="block">
            <div class="aspect-video overflow-hidden bg-black">
                <img src="${photo.src_sm || photo.src}" class="w-full h-full object-cover" loading="lazy">
            </div>
            <div class="p-2 bg-[#282828] text-[10px] grid grid-cols-2 gap-x-2 gap-y-1 text-white leading-tight">
                <div class="text-left truncate min-w-0">${photo.airline}</div>
                <div class="text-right truncate min-w-0">${photo.reg}</div>
                <div class="text-left truncate min-w-0">${photo.date}</div>
                <div class="text-right truncate min-w-0">${displayModel}</div>
            </div>
            </a>
        `;
        grid.appendChild(card);
    });

    renderPagination();
    window.scrollTo(0, 0);
}

// 4. 渲染分页按钮
function renderPagination() {
    const totalPages = totalPagesFromServer;
    ['pagination', 'pagination-bottom'].forEach(id => {
        const pagination = document.getElementById(id);
        if (!pagination) return;
        pagination.innerHTML = '';

        if (totalPages <= 1) return;

        const createBtn = (content, targetPage, active = false, disabled = false) => {
            const btn = document.createElement('button');
            btn.innerHTML = content;
            btn.className = `px-3 text-[11px] transition min-w-[32px] h-[32px] flex items-center justify-center ${active ? 'bg-black text-white font-bold' :
                disabled ? 'bg-gray-300 text-gray-500 cursor-not-allowed' : 'bg-white text-black hover:bg-gray-200'
                }`;

            if (!disabled && !active) {
                btn.onclick = () => {
                    currentPage = targetPage;
                    const newUrl = new URL(window.location);
                    newUrl.searchParams.set('page', targetPage);
                    newUrl.searchParams.set('ordering', currentOrdering);
                    window.history.pushState({}, '', newUrl);
                    initGallery();
                };
            }
            return btn;
        };

        pagination.appendChild(createBtn('<i class="fa fa-angle-left"></i>', currentPage - 1, false, currentPage === 1));

        const range = 1;
        let pages = [];
        if (totalPages <= 7) {
            for (let i = 1; i <= totalPages; i++) pages.push(i);
        } else {
            pages.push(1);
            if (currentPage > range + 2) pages.push('...');
            let start = Math.max(2, currentPage - range);
            let end = Math.min(totalPages - 1, currentPage + range);
            for (let i = start; i <= end; i++) pages.push(i);
            if (currentPage < totalPages - (range + 1)) pages.push('...');
            pages.push(totalPages);
        }

        pages.forEach(p => {
            if (p === '...') {
                const spacer = document.createElement('div');
                spacer.className = 'w-2 sm:w-4';
                pagination.appendChild(spacer);
            } else {
                pagination.appendChild(createBtn(p, p, p === currentPage));
            }
        });

        pagination.appendChild(createBtn('<i class="fa fa-angle-right"></i>', currentPage + 1, false, currentPage === totalPages));
    });
}

function syncSortButtons() {
    const container = document.getElementById('sort-toggle');
    if (!container) return;

    const arrows = { '': '↕', 'desc': '↓', 'asc': '↑' };
    const field = currentOrdering.replace(/^-/, '');
    const dir = currentOrdering.startsWith('-') ? 'desc' : 'asc';

    container.querySelectorAll('.sort-btn').forEach(btn => {
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

// 排序按钮事件
function initSortToggle() {
    syncSortButtons();

    const container = document.getElementById('sort-toggle');
    if (!container) return;
    
    const cycle = { '': 'desc', 'desc': 'asc', 'asc': 'desc' };

    container.addEventListener('click', (e) => {
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

        currentOrdering = (newDir === 'desc' ? '-' : '') + field;
        currentPage = 1;

        const newUrl = new URL(window.location);
        newUrl.searchParams.set('ordering', currentOrdering);
        newUrl.searchParams.set('page', '1');
        window.history.pushState({}, '', newUrl);

        syncSortButtons();
        initGallery();
    });
}

function initUniqueRegToggle() {
    const cb = document.getElementById('unique-reg-toggle');
    if (!cb) return;

    cb.checked = currentUniqueReg;

    cb.addEventListener('change', (e) => {
        currentUniqueReg = e.target.checked;
        currentPage = 1;

        const newUrl = new URL(window.location);
        if (currentUniqueReg) {
            newUrl.searchParams.set('unique_reg', '1');
        } else {
            newUrl.searchParams.delete('unique_reg');
        }
        newUrl.searchParams.set('page', '1');
        window.history.pushState({}, '', newUrl);

        initGallery();
    });
}

// 启动
initSortToggle();
initUniqueRegToggle();
initGallery();

window.onpopstate = function (event) {
    const newParams = new URLSearchParams(window.location.search);
    currentPage = parseInt(newParams.get('page')) || 1;
    currentOrdering = newParams.get('ordering') || '-date';
    currentUniqueReg = newParams.get('unique_reg') === '1';
    
    syncSortButtons();
    const cb = document.getElementById('unique-reg-toggle');
    if (cb) cb.checked = currentUniqueReg;

    initGallery();
};

function performNavSearch() {
    const input = document.getElementById('nav-search-input');
    if (!input) return;
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
