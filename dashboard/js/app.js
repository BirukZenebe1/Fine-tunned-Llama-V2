/* ─── Main Dashboard Application ──────────────────────────────── */

(function () {
    'use strict';

    // ─── State ───────────────────────────────────────────────────
    let chartManager;
    let alertManager;
    let ws;
    let msgPerSecCounter = 0;
    let startTime = Date.now();

    // ─── Initialization ──────────────────────────────────────────
    function init() {
        chartManager = new ChartManager();
        alertManager = new AlertManager('alerts-list', 50);

        initCharts();
        connectWebSocket();

        // Update KPI counters every second
        setInterval(updateKPIs, 1000);
    }

    function initCharts() {
        // Temperature line chart
        chartManager.createLineChart('temperature-chart', [
            { label: 'Avg', color: '#4fc3f7' },
            { label: 'Min', color: '#66bb6a' },
            { label: 'Max', color: '#ef5350' },
        ], '\u00B0C');

        // Humidity line chart
        chartManager.createLineChart('humidity-chart', [
            { label: 'Avg', color: '#ab47bc' },
            { label: 'Min', color: '#66bb6a' },
            { label: 'Max', color: '#ef5350' },
        ], '%');

        // Pressure line chart
        chartManager.createLineChart('pressure-chart', [
            { label: 'Avg', color: '#ffa726' },
            { label: 'Min', color: '#66bb6a' },
            { label: 'Max', color: '#ef5350' },
        ], 'hPa');

        // Activity bar chart
        chartManager.createBarChart('activity-chart', [
            { label: 'Page Views', color: '#4fc3f7' },
            { label: 'Clicks', color: '#ab47bc' },
            { label: 'Purchases', color: '#66bb6a' },
        ], 'Count');
    }

    // ─── WebSocket ───────────────────────────────────────────────
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        const port = window.location.port || (protocol === 'wss:' ? '443' : '80');
        const wsUrl = `${protocol}//${host}:${port}/ws/live`;

        ws = new DashboardWebSocket(wsUrl, handleMessage, {
            reconnectDelay: 1000,
            maxReconnectDelay: 30000,
            heartbeatInterval: 15000
        });
    }

    // ─── Message Router ──────────────────────────────────────────
    function handleMessage(msg) {
        msgPerSecCounter++;

        const data = msg.data || msg;
        if (!data) return;

        if (data.type === 'pong') return;

        if (data.type === 'window_flush') {
            handleWindowFlush(data);
        }
    }

    function handleWindowFlush(data) {
        const timeLabel = formatTime(data.timestamp || Date.now());

        // Group tumbling results by sensor type
        const iotTemp = { avg: [], min: [], max: [] };
        const iotHumidity = { avg: [], min: [], max: [] };
        const iotPressure = { avg: [], min: [], max: [] };
        const activity = { page_view: 0, click: 0, purchase: 0 };

        if (data.tumbling) {
            data.tumbling.forEach(r => {
                if (r.key.startsWith('iot:temperature:')) {
                    iotTemp.avg.push(r.avg);
                    iotTemp.min.push(r.min);
                    iotTemp.max.push(r.max);
                } else if (r.key.startsWith('iot:humidity:')) {
                    iotHumidity.avg.push(r.avg);
                    iotHumidity.min.push(r.min);
                    iotHumidity.max.push(r.max);
                } else if (r.key.startsWith('iot:pressure:')) {
                    iotPressure.avg.push(r.avg);
                    iotPressure.min.push(r.min);
                    iotPressure.max.push(r.max);
                } else if (r.key.startsWith('activity:')) {
                    const type = r.key.split(':')[1];
                    if (type in activity) activity[type] = r.count;
                }
            });
        }

        // Average across devices for each sensor type
        const avgOf = arr => arr.length ? arr.reduce((a, b) => a + b) / arr.length : null;

        if (iotTemp.avg.length) {
            chartManager.pushData('temperature-chart', timeLabel, [
                avgOf(iotTemp.avg), avgOf(iotTemp.min), avgOf(iotTemp.max)
            ]);
            updateGauge('temp-value', avgOf(iotTemp.avg), '\u00B0C');
        }
        if (iotHumidity.avg.length) {
            chartManager.pushData('humidity-chart', timeLabel, [
                avgOf(iotHumidity.avg), avgOf(iotHumidity.min), avgOf(iotHumidity.max)
            ]);
            updateGauge('humidity-value', avgOf(iotHumidity.avg), '%');
        }
        if (iotPressure.avg.length) {
            chartManager.pushData('pressure-chart', timeLabel, [
                avgOf(iotPressure.avg), avgOf(iotPressure.min), avgOf(iotPressure.max)
            ]);
            updateGauge('pressure-value', avgOf(iotPressure.avg), 'hPa');
        }

        // Update activity chart (rolling bar chart)
        chartManager.pushData('activity-chart', timeLabel, [
            activity.page_view, activity.click, activity.purchase
        ]);

        // Update sensor count KPI
        const sensorCount = (data.tumbling || []).filter(r => r.key.startsWith('iot:')).length;
        updateText('sensor-count', sensorCount.toString());

        // Process trends
        if (data.trends) {
            updateTrendIndicators(data.trends);
        }

        // Check for anomalies in the data
        if (data.tumbling) {
            data.tumbling.forEach(r => {
                if (r.key.startsWith('iot:') && r.p99 && r.avg) {
                    const ratio = Math.abs(r.p99 - r.avg) / (r.avg || 1);
                    if (ratio > 0.5) {
                        alertManager.addAlert({
                            key: r.key,
                            value: r.p99,
                            z_score: ratio * 3,
                            severity: ratio > 1.0 ? 'critical' : 'warning',
                            timestamp: data.timestamp,
                        });
                    }
                }
            });
        }
    }

    // ─── Gauge Updates ───────────────────────────────────────────
    function updateGauge(elementId, value, unit) {
        const el = document.getElementById(elementId);
        if (el && value !== null) {
            const formatted = value.toFixed(1);
            if (el.textContent !== formatted) {
                el.textContent = formatted;
                flashElement(el);
            }
        }
    }

    // ─── Trend Indicators ────────────────────────────────────────
    function updateTrendIndicators(trends) {
        const trendMap = {};
        trends.forEach(t => {
            const parts = t.key.split(':');
            if (parts[0] === 'iot' && parts.length >= 2) {
                const sensorType = parts[1];
                if (!trendMap[sensorType] || t.confidence > trendMap[sensorType].confidence) {
                    trendMap[sensorType] = t;
                }
            }
        });

        ['temperature', 'humidity', 'pressure'].forEach(sensor => {
            const indicator = document.getElementById(`trend-${sensor}`);
            if (indicator && trendMap[sensor]) {
                const t = trendMap[sensor];
                indicator.className = `trend-indicator trend-${t.direction}`;
                const arrows = { rising: '\u2191', falling: '\u2193', stable: '\u2192' };
                indicator.textContent = `${arrows[t.direction] || ''} ${t.direction}`;
            }
        });
    }

    // ─── KPI Updates ─────────────────────────────────────────────
    function updateKPIs() {
        updateText('throughput', msgPerSecCounter.toString());
        msgPerSecCounter = 0;

        // Uptime
        const uptimeSec = Math.floor((Date.now() - startTime) / 1000);
        const hours = Math.floor(uptimeSec / 3600);
        const mins = Math.floor((uptimeSec % 3600) / 60);
        const secs = uptimeSec % 60;
        updateText('uptime', `${hours}h ${mins}m ${secs}s`);
    }

    // ─── Start ───────────────────────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
