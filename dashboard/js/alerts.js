/* ─── Anomaly Alert Panel Manager ─────────────────────────────── */

class AlertManager {
    constructor(containerId, maxAlerts = 50) {
        this.container = document.getElementById(containerId);
        this.maxAlerts = maxAlerts;
        this.alertCount = 0;
    }

    addAlert(alert) {
        if (!this.container) return;

        this.alertCount++;
        const el = this._renderAlert(alert);
        this.container.insertBefore(el, this.container.firstChild);

        // Remove oldest if over limit
        while (this.container.children.length > this.maxAlerts) {
            this.container.removeChild(this.container.lastChild);
        }

        // Update counter in KPI bar
        updateText('anomaly-count', this.alertCount.toString());
    }

    _renderAlert(alert) {
        const div = document.createElement('div');
        div.className = `alert-item ${alert.severity || 'warning'}`;

        const icon = alert.severity === 'critical' ? '\u26A0' : '\u26A1';
        const zScore = typeof alert.z_score === 'number' ? alert.z_score.toFixed(2) : '--';
        const value = typeof alert.value === 'number' ? alert.value.toFixed(2) : '--';
        const ts = alert.timestamp ? timeAgo(alert.timestamp) : 'now';

        div.innerHTML = `
            <span class="alert-icon">${icon}</span>
            <div class="alert-content">
                <div class="alert-metric">${this._formatKey(alert.key || 'unknown')}</div>
                <div class="alert-details">Value: ${value} | Z-score: ${zScore}</div>
            </div>
            <span class="alert-time">${ts}</span>
        `;

        return div;
    }

    _formatKey(key) {
        // "iot:temperature:sensor-001" → "Temperature - sensor-001"
        const parts = key.split(':');
        if (parts.length >= 3) {
            return parts[1].charAt(0).toUpperCase() + parts[1].slice(1) + ' - ' + parts[2];
        }
        return key;
    }

    clear() {
        if (this.container) {
            this.container.innerHTML = '';
        }
        this.alertCount = 0;
    }
}
