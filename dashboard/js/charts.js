/* ─── Chart.js Manager ────────────────────────────────────────── */

class ChartManager {
    constructor() {
        this.charts = {};
        this.maxDataPoints = 60;
    }

    createLineChart(canvasId, datasets, yAxisLabel = '') {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: datasets.map(ds => ({
                    label: ds.label,
                    data: [],
                    borderColor: ds.color,
                    backgroundColor: ds.color + '20',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHitRadius: 10,
                    tension: 0.3,
                    fill: true,
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 300 },
                interaction: { intersect: false, mode: 'index' },
                plugins: {
                    legend: {
                        labels: { color: '#a0a0c0', font: { size: 11 } }
                    },
                    decimation: { enabled: true, algorithm: 'lttb', samples: 50 }
                },
                scales: {
                    x: {
                        ticks: { color: '#6a6a8a', maxTicksLimit: 8, font: { size: 10 } },
                        grid: { color: 'rgba(100,100,160,0.1)' }
                    },
                    y: {
                        title: { display: !!yAxisLabel, text: yAxisLabel, color: '#a0a0c0' },
                        ticks: { color: '#6a6a8a', font: { size: 10 } },
                        grid: { color: 'rgba(100,100,160,0.1)' }
                    }
                }
            }
        });
        this.charts[canvasId] = chart;
        return chart;
    }

    createBarChart(canvasId, datasets, yAxisLabel = '') {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: datasets.map(ds => ({
                    label: ds.label,
                    data: [],
                    backgroundColor: ds.color + '80',
                    borderColor: ds.color,
                    borderWidth: 1,
                    borderRadius: 4,
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 300 },
                plugins: {
                    legend: {
                        labels: { color: '#a0a0c0', font: { size: 11 } }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#6a6a8a', maxTicksLimit: 8, font: { size: 10 } },
                        grid: { color: 'rgba(100,100,160,0.1)' }
                    },
                    y: {
                        title: { display: !!yAxisLabel, text: yAxisLabel, color: '#a0a0c0' },
                        ticks: { color: '#6a6a8a', font: { size: 10 } },
                        grid: { color: 'rgba(100,100,160,0.1)' },
                        beginAtZero: true
                    }
                }
            }
        });
        this.charts[canvasId] = chart;
        return chart;
    }

    pushData(chartId, label, values) {
        const chart = this.charts[chartId];
        if (!chart) return;

        chart.data.labels.push(label);
        values.forEach((val, i) => {
            if (chart.data.datasets[i]) {
                chart.data.datasets[i].data.push(val);
            }
        });

        // Rolling window
        while (chart.data.labels.length > this.maxDataPoints) {
            chart.data.labels.shift();
            chart.data.datasets.forEach(ds => ds.data.shift());
        }

        chart.update('none'); // Skip animation for performance
    }

    updateBarData(chartId, labels, dataSets) {
        const chart = this.charts[chartId];
        if (!chart) return;

        chart.data.labels = labels;
        dataSets.forEach((data, i) => {
            if (chart.data.datasets[i]) {
                chart.data.datasets[i].data = data;
            }
        });
        chart.update('none');
    }
}
