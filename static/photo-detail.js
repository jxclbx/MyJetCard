const urlParams = new URLSearchParams(window.location.search);
const photoId = parseInt(urlParams.get('id'));

async function loadPhotoDetail() {
    if (!photoId) return;

    try {
        const r = await fetch(`/api/${window.SITE_USER}/photos/${photoId}/`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const photo = await r.json();

        if (photo) {
            const bigImg = document.getElementById('big-photo');
            if (bigImg) {
                bigImg.src = photo.src_lg || photo.src;
                bigImg.classList.add('cursor-zoom-in');
                bigImg.onclick = () => {
                    const overlay = document.getElementById('fullscreen-overlay');
                    const fullImg = document.getElementById('full-size-image');
                    fullImg.src = photo.src;
                    overlay.classList.remove('hidden');
                    document.body.style.overflow = 'hidden';
                };
            }

            document.title = `${photo.reg} - MyJetCard`;

            // --- 核心增强：辅助函数，用于同时更新文字和筛选链接 ---
            const updateLink = (id, key, value) => {
                const el = document.getElementById(id);
                if (el && value) {
                    el.innerText = value;
                    el.href = `/${window.SITE_USER}/gallery/?${key}=${encodeURIComponent(value)}`;
                }
            };

            // 1. 映射带筛选功能的链接
            updateLink('link-reg', 'reg', photo.reg);
            updateLink('link-model', 'model', photo.model);
            updateLink('link-airline', 'airline', photo.airline);
            updateLink('link-date', 'date', photo.date);

            // 机场显示全名 (If available in AIRPORT_DATA)
            const airportEl = document.getElementById('link-airport');
            if (airportEl && photo.airport) {
                const code = photo.airport.trim().toUpperCase();
                let displayName = photo.airport;
                if (window.AIRPORT_DATA && window.AIRPORT_DATA[code]) {
                    displayName = `${window.AIRPORT_DATA[code].n} (${code})`;
                } else if (typeof AIRPORT_DATA !== 'undefined' && AIRPORT_DATA[code]) {
                    displayName = `${AIRPORT_DATA[code].n} (${code})`;
                }
                airportEl.innerText = displayName;
                airportEl.href = `/${window.SITE_USER}/gallery/?airport=${encodeURIComponent(photo.airport)}`;
            }

            // 2. 映射不带筛选功能的纯文字字段
            // 细分机型 (Sub-model)
            const subModelEl = document.getElementById('info-sub-model');
            if (subModelEl) {
                // 如果 JSON 中有 sub_model 则显示，并在前面加个空格或括号区分
                subModelEl.innerText = photo.sub_model ? `(${photo.sub_model})` : "";
            }

            // 图片备注 (Remarks)
            const remarksEl = document.getElementById('info-remarks');
            if (remarksEl) {
                remarksEl.innerText = photo.remarks || "No remarks provided for this photo.";
            }

            const navReg = document.getElementById('nav-reg');
            if (navReg) navReg.innerText = photo.reg;

            const camEl = document.getElementById('info-camera');
            if (camEl) {
                // 直接使用API返回的实际名称，而不是ID
                const cameraName = photo.camera_name || "Unknown Camera";
                const lensName = photo.lens_name || "Unknown Lens";
                camEl.innerText = `${cameraName} | ${lensName}`;
            }

            // --- Render tag badges ---
            const tagsEl = document.getElementById('photo-tags');
            if (tagsEl) {
                const tagDefs = [
                    { key: 'featured', label: '⭐ Featured', color: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
                    { key: 'is_special_livery', label: '🎨 Special Livery', color: 'bg-purple-100 text-purple-800 border-purple-300' },
                    { key: 'is_cargo', label: '📦 Cargo', color: 'bg-orange-100 text-orange-800 border-orange-300' },
                    { key: 'is_bizjet', label: '💼 Business Jet', color: 'bg-blue-100 text-blue-800 border-blue-300' },
                    { key: 'is_helicopter', label: '🚁 Helicopter', color: 'bg-green-100 text-green-800 border-green-300' },
                    { key: 'is_rare', label: '💎 Rare', color: 'bg-red-100 text-red-800 border-red-300' },
                ];
                const badges = [];
                tagDefs.forEach(t => {
                    if (photo[t.key]) {
                        badges.push(`<a href="/${window.SITE_USER}/gallery/?${t.key}=true" class="inline-block text-xs font-bold px-3 py-1 rounded-full border ${t.color} hover:opacity-80 transition">${t.label}</a>`);
                    }
                });
                if (badges.length > 0) {
                    tagsEl.innerHTML = badges.join('');
                    tagsEl.style.display = 'flex';
                }
            }
        }
    } catch (err) {
        console.error("Failed to load database:", err);
    }
}

document.getElementById('fullscreen-overlay').onclick = function () {
    this.classList.add('hidden');
    document.body.style.overflow = 'auto';
};

loadPhotoDetail();

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
            if (e.key === 'Enter') {
                performNavSearch();
            }
        });
    }
});



