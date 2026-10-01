/* ==========================================================
   公告数据大屏 - 前端逻辑
   数据全部来自 Flask 提供的 /api/* 接口
   ========================================================== */

const PALETTE = ['#f3c25f', '#38e1ff', '#409eff', '#43d18c', '#ff7c7c',
    '#a37bff', '#ff9f40', '#5ad1e6', '#f56c9c', '#8ba3c7'];

const charts = {};          // 图表实例集合，用于 resize 与刷新
let page = 1;               // 明细表当前页
let totalPages = 1;         // 明细表总页数
const pageSize = 20;

/* ------------------------------ 通用工具 ------------------------------ */
async function getJSON(url) {
    const res = await fetch(url);
    const json = await res.json();
    if (json.code !== 0) throw new Error(json.msg || '接口异常');
    return json;
}

/** 触发重新采集（POST 语义） */
async function postJSON(url) {
    const res = await fetch(url, { method: 'POST' });
    const json = await res.json();
    if (json.code !== 0) throw new Error(json.msg || '接口异常');
    return json;
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

/* 通用坐标轴深色样式 */
const AXIS = {
    axisLine: { lineStyle: { color: 'rgba(139,163,199,.35)' } },
    axisLabel: { color: '#8ba3c7', fontSize: 11 },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,.06)' } }
};

const BASE_TOOLTIP = {
    backgroundColor: 'rgba(9,18,36,.94)',
    borderColor: 'rgba(64,158,255,.45)',
    textStyle: { color: '#e6f0ff', fontSize: 12 }
};

function initChart(id) {
    if (charts[id]) return charts[id];
    const el = document.getElementById(id);
    if (!el) return null;
    charts[id] = echarts.init(el, null, { renderer: 'canvas' });
    return charts[id];
}

/* ------------------------------ 1. 总览指标 ------------------------------ */
async function loadOverview() {
    const { data } = await getJSON('/api/overview');
    setText('stockBadge', data.stock_code);
    setText('kpiTotal', data.total);
    setText('kpiCategory', data.category_count);
    setText('kpiSpan', data.span_days);
    setText('kpiLatest', data.date_end || '--');
    setText('updateTime', data.updated_at);
    setText('kpiSource', (data.sources || []).map(s => s.name).join(' / ') || '--');
}

/* ------------------------------ 2. 分类占比（玫瑰图） ------------------------------ */
async function loadCategory() {
    const { data } = await getJSON('/api/category');
    const chart = initChart('chartCategory');
    chart.setOption({
        color: PALETTE,
        tooltip: { ...BASE_TOOLTIP, trigger: 'item', formatter: '{b}: {c} 条 ({d}%)' },
        legend: {
            type: 'scroll', orient: 'vertical', right: 0, top: 'middle',
            textStyle: { color: '#8ba3c7', fontSize: 11 }, itemWidth: 10, itemHeight: 10
        },
        series: [{
            type: 'pie',
            radius: ['32%', '68%'],
            center: ['38%', '52%'],
            roseType: 'radius',
            itemStyle: { borderColor: '#12203a', borderWidth: 2 },
            label: { color: '#8ba3c7', fontSize: 11, formatter: '{b}\n{d}%' },
            labelLine: { length: 6, length2: 8 },
            data: data.map(d => ({ name: d.name, value: d.value }))
        }]
    }, true);
}

/* ------------------------------ 3. 月度趋势（面积折线） ------------------------------ */
async function loadTrend() {
    const { data } = await getJSON('/api/trend');
    const chart = initChart('chartTrend');
    chart.setOption({
        color: ['#38e1ff'],
        tooltip: { ...BASE_TOOLTIP, trigger: 'axis' },
        grid: { left: 46, right: 22, top: 26, bottom: 52 },
        xAxis: { type: 'category', data: data.map(d => d.month), ...AXIS, axisLabel: { ...AXIS.axisLabel, rotate: 45 } },
        yAxis: { type: 'value', name: '条数', nameTextStyle: { color: '#8ba3c7' }, ...AXIS },
        dataZoom: [{ type: 'slider', bottom: 8, height: 16, borderColor: 'transparent',
            backgroundColor: 'rgba(64,158,255,.10)', fillerColor: 'rgba(64,158,255,.25)',
            handleStyle: { color: '#409eff' }, textStyle: { color: '#8ba3c7', fontSize: 10 } }],
        series: [{
            type: 'line', smooth: true, symbol: 'circle', symbolSize: 5,
            data: data.map(d => d.value),
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(56,225,255,.45)' },
                    { offset: 1, color: 'rgba(56,225,255,0)' }
                ])
            },
            lineStyle: { width: 2 },
            markPoint: { data: [{ type: 'max', name: '峰值' }, { type: 'min', name: '谷值' }], symbolSize: 42 }
        }]
    }, true);
}

/* ------------------------------ 4. 年度分布（柱状） ------------------------------ */
async function loadYear() {
    const { data } = await getJSON('/api/year');
    const chart = initChart('chartYear');
    chart.setOption({
        tooltip: { ...BASE_TOOLTIP, trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { left: 46, right: 20, top: 26, bottom: 34 },
        xAxis: { type: 'category', data: data.map(d => d.name + '年'), ...AXIS },
        yAxis: { type: 'value', ...AXIS },
        series: [{
            type: 'bar', barWidth: '45%',
            data: data.map(d => d.value),
            itemStyle: {
                borderRadius: [4, 4, 0, 0],
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: '#f3c25f' }, { offset: 1, color: 'rgba(243,194,95,.25)' }
                ])
            },
            label: { show: true, position: 'top', color: '#f3c25f', fontSize: 11 }
        }]
    }, true);
}

/* ------------------------------ 5. 季度分布（横向柱） ------------------------------ */
async function loadQuarter() {
    const { data } = await getJSON('/api/quarter');
    const chart = initChart('chartQuarter');
    chart.setOption({
        tooltip: { ...BASE_TOOLTIP, trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { left: 60, right: 34, top: 20, bottom: 26 },
        xAxis: { type: 'value', ...AXIS },
        yAxis: {
            type: 'category', ...AXIS,
            data: data.map(d => 'Q' + d.name).reverse(),
            splitLine: { show: false }
        },
        series: [{
            type: 'bar', barWidth: '46%',
            data: data.map(d => d.value).reverse(),
            itemStyle: {
                borderRadius: [0, 4, 4, 0],
                color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                    { offset: 0, color: 'rgba(67,209,140,.35)' }, { offset: 1, color: '#43d18c' }
                ])
            },
            label: { show: true, position: 'right', color: '#43d18c', fontSize: 11 }
        }]
    }, true);
}

/* ------------------------------ 6. 星期分布（雷达） ------------------------------ */
async function loadWeekday() {
    const { data } = await getJSON('/api/weekday');
    const chart = initChart('chartWeekday');
    chart.setOption({
        color: ['#38e1ff'],
        tooltip: { ...BASE_TOOLTIP },
        radar: {
            indicator: data.map(d => ({ name: d.name, max: Math.max(...data.map(x => x.value)) * 1.2 || 10 })),
            radius: '66%',
            axisName: { color: '#8ba3c7', fontSize: 11 },
            splitLine: { lineStyle: { color: 'rgba(255,255,255,.10)' } },
            splitArea: { areaStyle: { color: ['rgba(64,158,255,.05)', 'rgba(64,158,255,.02)'] } },
            axisLine: { lineStyle: { color: 'rgba(255,255,255,.12)' } }
        },
        series: [{
            type: 'radar',
            data: [{
                value: data.map(d => d.value),
                name: '披露条数',
                areaStyle: { color: 'rgba(56,225,255,.28)' },
                lineStyle: { color: '#38e1ff', width: 2 },
                itemStyle: { color: '#38e1ff' }
            }]
        }]
    }, true);
}

/* ------------------------------ 7. 最新公告播报 ------------------------------ */
async function loadNews() {
    const { data } = await getJSON('/api/recent?limit=30');
    const box = document.getElementById('newsList');
    box.innerHTML = data.map(n => {
        const title = n.url
            ? `<a href="${n.url}" target="_blank" rel="noopener">${escapeHtml(n.title)}</a>`
            : escapeHtml(n.title);
        return `<div class="news-item">
                    <span class="news-date">${n.publish_date}</span>
                    <span class="news-tag">${n.category}</span>
                    <span class="news-title">${title}</span>
                </div>`;
    }).join('') || '<div class="news-item muted">暂无数据</div>';
}

/* ------------------------------ 8. 明细表格 ------------------------------ */
async function loadTable() {
    const category = document.getElementById('filterCategory').value;
    const keyword = document.getElementById('filterKeyword').value.trim();
    const url = `/api/list?page=${page}&size=${pageSize}`
        + `&category=${encodeURIComponent(category)}&keyword=${encodeURIComponent(keyword)}`;

    const json = await getJSON(url);
    const body = document.getElementById('tableBody');

    body.innerHTML = json.data.map(r => `
        <tr>
            <td>${r.publish_date}</td>
            <td><span class="tag">${r.category}</span></td>
            <td title="${escapeHtml(r.title)}">${escapeHtml(r.title)}</td>
            <td class="muted">${r.doc_type || '-'}</td>
            <td>${r.url ? `<a class="link" href="${r.url}" target="_blank" rel="noopener">查看原文</a>`
            : '<span class="muted">-</span>'}</td>
        </tr>`).join('') || '<tr><td colspan="5" class="muted" style="text-align:center">暂无数据</td></tr>';

    totalPages = json.pages || 1;
    // 越界时回退到最后一页，避免空白表格
    if (page > totalPages) {
        page = totalPages;
        return loadTable();
    }
    setText('pageInfo', `${json.page} / ${totalPages}`);
    setText('totalHint', `共 ${json.total} 条记录`);
}

async function loadCategoryOptions() {
    const { data } = await getJSON('/api/category');
    const sel = document.getElementById('filterCategory');
    const cur = sel.value;
    sel.innerHTML = '<option value="">全部分类</option>'
        + data.map(d => `<option value="${d.name}">${d.name}</option>`).join('');
    sel.value = cur;
}

/* ------------------------------ 9. 重新采集 ------------------------------ */
let polling = null;

async function startRefresh() {
    const mask = document.getElementById('modalMask');
    const logBox = document.getElementById('modalLog');
    const closeBtn = document.getElementById('btnCloseModal');
    const btn = document.getElementById('btnRefresh');

    btn.disabled = true;
    closeBtn.disabled = true;
    mask.classList.add('show');
    logBox.textContent = '已提交采集任务，等待后端响应...\n';
    btn.textContent = '采集中...';

    try {
        await postJSON('/api/refresh');
    } catch (e) {
        logBox.textContent += '\n提交失败：' + e.message;
        btn.disabled = false;
        closeBtn.disabled = false;
        btn.textContent = '重新采集';
        return;
    }

    // 轮询任务状态
    polling = setInterval(async () => {
        let st;
        try {
            st = (await getJSON('/api/refresh/status')).data;
        } catch (e) {
            return;
        }
        logBox.textContent = (st.log || []).join('\n');
        logBox.scrollTop = logBox.scrollHeight;

        if (!st.running) {
            clearInterval(polling);
            polling = null;
            btn.disabled = false;
            closeBtn.disabled = false;
            btn.textContent = '重新采集';
            logBox.textContent += '\n\n=== 采集完成，正在刷新大屏 ===';
            await refreshAll();      // 数据已更新，重载全部视图
            logBox.textContent += '\n大屏已刷新。';
        }
    }, 800);
}

/* ------------------------------ 统一刷新入口 ------------------------------ */
async function refreshAll() {
    await Promise.all([
        loadOverview(), loadCategory(), loadTrend(), loadYear(),
        loadQuarter(), loadWeekday(), loadNews(), loadCategoryOptions()
    ]).catch(e => console.error('加载失败:', e));
    await loadTable().catch(e => console.error('表格加载失败:', e));
}

/* ------------------------------ 工具：HTML 转义 ------------------------------ */
function escapeHtml(str) {
    if (str == null) return '';
    return String(str).replace(/[&<>"']/g, c => (
        { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
}

/* ------------------------------ 事件绑定与启动 ------------------------------ */
window.addEventListener('DOMContentLoaded', () => {
    refreshAll();

    document.getElementById('btnRefresh').addEventListener('click', startRefresh);

    document.getElementById('btnSearch').addEventListener('click', () => {
        page = 1;
        loadTable();
    });

    document.getElementById('filterKeyword').addEventListener('keydown', e => {
        if (e.key === 'Enter') { page = 1; loadTable(); }
    });

    document.getElementById('filterCategory').addEventListener('change', () => {
        page = 1;
        loadTable();
    });

    document.getElementById('btnPrev').addEventListener('click', () => {
        if (page > 1) { page--; loadTable(); }
    });

    document.getElementById('btnNext').addEventListener('click', () => {
        if (page < totalPages) { page++; loadTable(); }
    });

    document.getElementById('btnCloseModal').addEventListener('click', () => {
        document.getElementById('modalMask').classList.remove('show');
    });

    // 窗口缩放时自适应
    window.addEventListener('resize', () => {
        Object.values(charts).forEach(c => c && c.resize());
    });
});
