/**
 * perf.js - API 性能监控浮动面板
 * 包装全局 fetch，记录每个 /api/ 请求的：
 *   - 总耗时（前端 fetch 从发起到拿到 response）
 *   - 后端耗时（从 X-Process-Time 响应头读取）
 *   - 网络耗时 = 总耗时 - 后端耗时
 * 在页面左下角渲染一个可折叠面板实时显示结果。
 */
(function () {
  // ========== 1. 创建浮动面板 ==========
  const panel = document.createElement('div');
  panel.id = 'perf-panel';
  panel.innerHTML = `
    <div id="perf-header" style="
      display:flex; justify-content:space-between; align-items:center;
      cursor:pointer; user-select:none; padding:6px 10px;
      background:#1a1a1a; border-radius:6px 6px 0 0;
    ">
      <span style="font-weight:700; font-size:11px; letter-spacing:0.05em;">⚡ API PERF</span>
      <span id="perf-toggle" style="font-size:10px; opacity:0.6;">▼</span>
    </div>
    <div id="perf-body" style="max-height:320px; overflow-y:auto; padding:4px 0;"></div>
  `;
  Object.assign(panel.style, {
    position: 'fixed',
    bottom: '12px',
    left: '12px',
    zIndex: '99999',
    background: '#222',
    color: '#eee',
    fontFamily: "'Inter', monospace, sans-serif",
    fontSize: '11px',
    borderRadius: '6px',
    boxShadow: '0 4px 24px rgba(0,0,0,0.5)',
    minWidth: '320px',
    maxWidth: '420px',
    opacity: '0.92',
    transition: 'opacity 0.2s',
  });
  panel.addEventListener('mouseenter', () => panel.style.opacity = '1');
  panel.addEventListener('mouseleave', () => panel.style.opacity = '0.92');

  document.addEventListener('DOMContentLoaded', () => document.body.appendChild(panel));

  // 折叠/展开
  let collapsed = false;
  panel.querySelector('#perf-header').addEventListener('click', () => {
    collapsed = !collapsed;
    panel.querySelector('#perf-body').style.display = collapsed ? 'none' : 'block';
    panel.querySelector('#perf-toggle').textContent = collapsed ? '▶' : '▼';
  });

  const body = panel.querySelector('#perf-body');

  function addEntry(url, totalMs, serverMs) {
    const netMs = Math.max(0, totalMs - serverMs);
    // 提取简短路径
    const shortUrl = url.replace(/^https?:\/\/[^/]+/, '').split('?')[0];

    const row = document.createElement('div');
    row.style.cssText = 'padding:4px 10px; border-bottom:1px solid #333; display:flex; gap:8px; align-items:center;';

    // 颜色标识：绿色 <100ms, 橙色 <300ms, 红色 >=300ms
    const totalColor = totalMs < 100 ? '#4ade80' : totalMs < 300 ? '#facc15' : '#f87171';

    row.innerHTML = `
      <span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:#aaa;" title="${url}">${shortUrl}</span>
      <span style="min-width:55px; text-align:right; color:${totalColor}; font-weight:700;">${totalMs.toFixed(0)}ms</span>
      <span style="min-width:90px; text-align:right; color:#888; font-size:10px;">svr ${serverMs.toFixed(0)}ms</span>
      <span style="min-width:80px; text-align:right; color:#888; font-size:10px;">net ${netMs.toFixed(0)}ms</span>
    `;

    // 最新的在最上面
    body.insertBefore(row, body.firstChild);

    // 最多保留 30 条
    while (body.children.length > 30) {
      body.removeChild(body.lastChild);
    }
  }

  // ========== 2. 包装全局 fetch ==========
  const originalFetch = window.fetch;
  window.fetch = async function (...args) {
    const url = typeof args[0] === 'string' ? args[0] : (args[0]?.url || '');
    const isApi = url.includes('/api/');

    if (!isApi) {
      return originalFetch.apply(this, args);
    }

    const start = performance.now();
    const response = await originalFetch.apply(this, args);
    const totalMs = performance.now() - start;

    let serverMs = 0;
    const serverHeader = response.headers.get('X-Process-Time');
    if (serverHeader) {
      serverMs = parseFloat(serverHeader) || 0;
    }

    addEntry(url, totalMs, serverMs);
    return response;
  };
})();
