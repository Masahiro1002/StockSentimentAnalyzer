/**
 * app.js - Stock Sentiment Analyzer
 * Chart.js + Supabase JS SDK によるダッシュボードロジック
 */

// ============================================
// 設定・定数
// ============================================
const STORAGE_KEY = 'stock_sentiment_config';
const DEFAULT_DAYS = 60;

// ============================================
// Supabase 接続管理
// ============================================
let supabaseClient = null;

function getStoredConfig() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
}

function saveConfig(url, key) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ url, key }));
}

function initSupabase(url, anonKey) {
    supabaseClient = supabase.createClient(url, anonKey);
    return supabaseClient;
}

// ============================================
// データ取得
// ============================================
async function fetchSentimentData(ticker, days) {
    if (!supabaseClient) {
        throw new Error('Supabase が未接続です');
    }

    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);
    const startDateStr = startDate.toISOString().split('T')[0];

    const { data, error } = await supabaseClient
        .from('sentiment_data')
        .select('date, ticker, sentiment_score, close_price')
        .eq('ticker', ticker)
        .gte('date', startDateStr)
        .order('date', { ascending: true });

    if (error) {
        throw new Error(`データ取得エラー: ${error.message}`);
    }

    return data || [];
}

async function fetchTickers() {
    if (!supabaseClient) {
        throw new Error('Supabase が未接続です');
    }

    const { data, error } = await supabaseClient
        .from('tickers')
        .select('code, name')
        .eq('active', true);

    if (error) {
        throw new Error(`銘柄リスト取得エラー: ${error.message}`);
    }

    return data || [];
}

// ============================================
// Chart.js グラフ管理
// ============================================
let mainChart = null;

function createChart(data) {
    const ctx = document.getElementById('main-chart').getContext('2d');

    // 既存チャートがあれば破棄
    if (mainChart) {
        mainChart.destroy();
    }

    const labels = data.map(d => d.date);
    const prices = data.map(d => d.close_price);
    const sentiments = data.map(d => d.sentiment_score);

    mainChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: '株価（終値）',
                    data: prices,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.08)',
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#1e3a5f',
                    pointBorderWidth: 2,
                    yAxisID: 'y-price',
                    order: 1,
                },
                {
                    label: 'センチメント',
                    data: sentiments,
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.08)',
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#8b5cf6',
                    pointBorderColor: '#3b1f6e',
                    pointBorderWidth: 2,
                    yAxisID: 'y-sentiment',
                    order: 2,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    display: false,
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    borderColor: 'rgba(148, 163, 184, 0.2)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    titleFont: { family: "'Inter', sans-serif", size: 13, weight: '600' },
                    bodyFont: { family: "'Inter', sans-serif", size: 12 },
                    titleColor: '#f1f5f9',
                    bodyColor: '#94a3b8',
                    callbacks: {
                        label: function (context) {
                            if (context.datasetIndex === 0) {
                                return `株価: ¥${context.parsed.y?.toLocaleString() ?? '--'}`;
                            } else {
                                const val = context.parsed.y;
                                const emoji = val > 0.3 ? '😊' : val < -0.3 ? '😟' : '😐';
                                return `センチメント: ${val?.toFixed(3) ?? '--'} ${emoji}`;
                            }
                        },
                    },
                },
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(148, 163, 184, 0.06)',
                        drawBorder: false,
                    },
                    ticks: {
                        color: '#64748b',
                        font: { family: "'Inter', sans-serif", size: 11 },
                        maxTicksLimit: 12,
                        maxRotation: 45,
                    },
                },
                'y-price': {
                    type: 'linear',
                    position: 'left',
                    title: {
                        display: true,
                        text: '株価（円）',
                        color: '#3b82f6',
                        font: { family: "'Inter', sans-serif", size: 12, weight: '600' },
                    },
                    grid: {
                        color: 'rgba(59, 130, 246, 0.06)',
                        drawBorder: false,
                    },
                    ticks: {
                        color: '#3b82f6',
                        font: { family: "'Inter', sans-serif", size: 11 },
                        callback: (val) => `¥${val.toLocaleString()}`,
                    },
                },
                'y-sentiment': {
                    type: 'linear',
                    position: 'right',
                    min: -1.0,
                    max: 1.0,
                    title: {
                        display: true,
                        text: 'センチメント',
                        color: '#8b5cf6',
                        font: { family: "'Inter', sans-serif", size: 12, weight: '600' },
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                    ticks: {
                        color: '#8b5cf6',
                        font: { family: "'Inter', sans-serif", size: 11 },
                        stepSize: 0.25,
                        callback: (val) => val.toFixed(2),
                    },
                },
            },
            animation: {
                duration: 800,
                easing: 'easeOutQuart',
            },
        },
    });
}

// ============================================
// KPIカード更新
// ============================================
function updateKPIs(data) {
    if (!data || data.length === 0) {
        return;
    }

    // 株価があるレコードのうち最新のもの
    const priceRecords = data.filter(d => d.close_price != null);
    const latestPrice = priceRecords.length > 0 ? priceRecords[priceRecords.length - 1] : null;
    const prevPrice = priceRecords.length > 1 ? priceRecords[priceRecords.length - 2] : null;

    // センチメントがあるレコード（蓄積分のみ）
    const sentimentRecords = data.filter(d => d.sentiment_score != null);
    const latestSentiment = sentimentRecords.length > 0 ? sentimentRecords[sentimentRecords.length - 1] : null;

    // 最新株価
    const priceEl = document.getElementById('kpi-price');
    const priceChangeEl = document.getElementById('kpi-price-change');
    if (latestPrice) {
        priceEl.textContent = `¥${Number(latestPrice.close_price).toLocaleString()}`;
        if (prevPrice) {
            const diff = latestPrice.close_price - prevPrice.close_price;
            const pct = ((diff / prevPrice.close_price) * 100).toFixed(2);
            priceChangeEl.textContent = `${diff >= 0 ? '+' : ''}${pct}%`;
            priceChangeEl.className = `kpi-change ${diff >= 0 ? 'positive' : 'negative'}`;
        }
    }

    // 最新センチメント（蓄積分から取得）
    const sentEl = document.getElementById('kpi-sentiment');
    const sentLabelEl = document.getElementById('kpi-sentiment-label');
    if (latestSentiment) {
        const score = latestSentiment.sentiment_score;
        sentEl.textContent = `${score >= 0 ? '+' : ''}${Number(score).toFixed(3)}`;
        let label, cls;
        if (score > 0.3) { label = '😊 ポジティブ'; cls = 'positive'; }
        else if (score < -0.3) { label = '😟 ネガティブ'; cls = 'negative'; }
        else { label = '😐 中立'; cls = ''; }
        sentLabelEl.textContent = label;
        sentLabelEl.className = `kpi-change ${cls}`;
    } else {
        sentEl.textContent = '--';
        sentLabelEl.textContent = 'データなし';
    }

    // トレンド（センチメント蓄積分の7日移動平均の傾き）
    const trendEl = document.getElementById('kpi-trend');
    const trendLabelEl = document.getElementById('kpi-trend-label');
    if (sentimentRecords.length >= 7) {
        const recent7 = sentimentRecords.slice(-7);
        const avgRecent = recent7.reduce((s, d) => s + d.sentiment_score, 0) / 7;
        const prev7 = sentimentRecords.slice(-14, -7);
        if (prev7.length >= 7) {
            const avgPrev = prev7.reduce((s, d) => s + d.sentiment_score, 0) / 7;
            const trendDiff = avgRecent - avgPrev;
            trendEl.textContent = trendDiff >= 0 ? '↗ 上昇' : '↘ 下降';
            trendLabelEl.textContent = `7日平均: ${avgRecent >= 0 ? '+' : ''}${avgRecent.toFixed(3)}`;
            trendLabelEl.className = `kpi-change ${trendDiff >= 0 ? 'positive' : 'negative'}`;
        } else {
            trendEl.textContent = `${avgRecent >= 0 ? '+' : ''}${avgRecent.toFixed(3)}`;
            trendLabelEl.textContent = '7日移動平均';
        }
    } else if (sentimentRecords.length > 0) {
        const avg = sentimentRecords.reduce((s, d) => s + d.sentiment_score, 0) / sentimentRecords.length;
        trendEl.textContent = `${avg >= 0 ? '+' : ''}${avg.toFixed(3)}`;
        trendLabelEl.textContent = `${sentimentRecords.length}日平均`;
    }

    // データ件数
    document.getElementById('kpi-count').textContent = `${sentimentRecords.length} / ${data.length}`;
    document.getElementById('kpi-last-update').textContent = `最終: ${(latestPrice || data[data.length - 1]).date}`;
}

// ============================================
// データテーブル更新
// ============================================
function updateTable(data) {
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = '';

    // 新しい順に表示
    const sorted = [...data].reverse();

    for (const row of sorted) {
        const tr = document.createElement('tr');

        // 日付
        const tdDate = document.createElement('td');
        tdDate.textContent = row.date;
        tr.appendChild(tdDate);

        // 終値
        const tdPrice = document.createElement('td');
        tdPrice.textContent = row.close_price != null ? `¥${Number(row.close_price).toLocaleString()}` : '--';
        tr.appendChild(tdPrice);

        // センチメントスコア
        const tdScore = document.createElement('td');
        const score = row.sentiment_score;
        tdScore.textContent = score != null ? `${score >= 0 ? '+' : ''}${Number(score).toFixed(3)}` : '--';
        tr.appendChild(tdScore);

        // 評価バッジ
        const tdBadge = document.createElement('td');
        const badge = document.createElement('span');
        badge.classList.add('sentiment-badge');
        if (score != null) {
            if (score > 0.2) {
                badge.classList.add('positive');
                badge.textContent = '😊 ポジティブ';
            } else if (score < -0.2) {
                badge.classList.add('negative');
                badge.textContent = '😟 ネガティブ';
            } else {
                badge.classList.add('neutral');
                badge.textContent = '😐 中立';
            }
        }
        tdBadge.appendChild(badge);
        tr.appendChild(tdBadge);

        tbody.appendChild(tr);
    }
}

// ============================================
// メイン処理
// ============================================
let currentTicker = null;
let currentDays = DEFAULT_DAYS;

async function loadTickers() {
    try {
        const tickers = await fetchTickers();
        const select = document.getElementById('ticker-select');
        select.innerHTML = '';

        for (const t of tickers) {
            const option = document.createElement('option');
            option.value = t.code;
            option.textContent = `${t.code} - ${t.name}`;
            select.appendChild(option);
        }

        // 最初の銘柄を選択してデータ読み込み
        if (tickers.length > 0) {
            currentTicker = tickers[0].code;
            select.value = currentTicker;
            loadData();
        }
    } catch (err) {
        console.error('銘柄リスト取得失敗:', err);
    }
}

async function loadData() {
    if (!currentTicker) return;

    const loading = document.getElementById('chart-loading');
    loading.style.display = 'flex';

    try {
        const data = await fetchSentimentData(currentTicker, currentDays);

        if (data.length === 0) {
            loading.innerHTML = '<p>📭 データがありません。バッチ処理を実行してデータを収集してください。</p>';
            return;
        }

        loading.style.display = 'none';
        createChart(data);
        updateKPIs(data);
        updateTable(data);

    } catch (err) {
        loading.innerHTML = `<p style="color: var(--accent-red);">❌ ${err.message}</p>`;
        console.error(err);
    }
}

function showConfigModal() {
    document.getElementById('config-modal').style.display = 'flex';
}

function hideConfigModal() {
    document.getElementById('config-modal').style.display = 'none';
}

// ============================================
// イベントリスナー
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    // Supabase 設定の復元チェック
    const config = getStoredConfig();
    if (config && config.url && config.key) {
        initSupabase(config.url, config.key);
        loadTickers();
    } else {
        showConfigModal();
    }

    // 設定保存ボタン
    document.getElementById('config-save').addEventListener('click', () => {
        const url = document.getElementById('config-url').value.trim();
        const key = document.getElementById('config-key').value.trim();

        if (!url || !key) {
            alert('Supabase URL と Anon Key を入力してください。');
            return;
        }

        saveConfig(url, key);
        initSupabase(url, key);
        hideConfigModal();
        loadTickers();
    });

    // 期間切り替え
    document.querySelectorAll('.btn-period').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.btn-period').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentDays = parseInt(btn.dataset.days);
            loadData();
        });
    });

    // 銘柄切り替え
    document.getElementById('ticker-select').addEventListener('change', (e) => {
        currentTicker = e.target.value;
        loadData();
    });

    // 更新ボタン
    document.getElementById('refresh-btn').addEventListener('click', () => {
        loadData();
    });

    // 設定ボタン（ヘッダー）
    document.getElementById('settings-btn').addEventListener('click', () => {
        const config = getStoredConfig();
        if (config) {
            document.getElementById('config-url').value = config.url || '';
            document.getElementById('config-key').value = config.key || '';
        }
        showConfigModal();
    });

    // モーダル閉じるボタン
    document.getElementById('config-close').addEventListener('click', () => {
        hideConfigModal();
    });
});
