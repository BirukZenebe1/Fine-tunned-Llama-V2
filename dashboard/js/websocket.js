/* ─── WebSocket Client with Auto-Reconnect ───────────────────── */

class DashboardWebSocket {
    constructor(url, onMessage, options = {}) {
        this.url = url;
        this.onMessage = onMessage;
        this.reconnectDelay = options.reconnectDelay || 1000;
        this.maxReconnectDelay = options.maxReconnectDelay || 30000;
        this.heartbeatInterval = options.heartbeatInterval || 15000;
        this._currentDelay = this.reconnectDelay;
        this._ws = null;
        this._heartbeatTimer = null;
        this._messageCount = 0;
        this._lastMessageTime = 0;
        this.connect();
    }

    connect() {
        this._updateStatus('connecting');
        this._ws = new WebSocket(this.url);

        this._ws.onopen = () => {
            this._currentDelay = this.reconnectDelay;
            this._startHeartbeat();
            this._updateStatus('connected');
            // Subscribe to all channels
            this._ws.send(JSON.stringify({
                type: 'subscribe',
                channels: ['iot', 'activity', 'alerts', 'trends', 'metrics']
            }));
        };

        this._ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this._messageCount++;
                this._lastMessageTime = Date.now();
                this.onMessage(data);
            } catch (e) {
                console.warn('Failed to parse WebSocket message:', e);
            }
        };

        this._ws.onclose = (event) => {
            this._stopHeartbeat();
            this._updateStatus('disconnected');
            if (!event.wasClean) {
                this._scheduleReconnect();
            }
        };

        this._ws.onerror = () => {
            this._updateStatus('error');
        };
    }

    _scheduleReconnect() {
        this._updateStatus('reconnecting');
        const jitter = Math.random() * 0.3 * this._currentDelay;
        const delay = this._currentDelay + jitter;
        setTimeout(() => this.connect(), delay);
        this._currentDelay = Math.min(this._currentDelay * 2, this.maxReconnectDelay);
    }

    _startHeartbeat() {
        this._heartbeatTimer = setInterval(() => {
            if (this._ws && this._ws.readyState === WebSocket.OPEN) {
                this._ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, this.heartbeatInterval);
    }

    _stopHeartbeat() {
        if (this._heartbeatTimer) {
            clearInterval(this._heartbeatTimer);
            this._heartbeatTimer = null;
        }
    }

    _updateStatus(status) {
        const dot = document.querySelector('.status-dot');
        const text = document.querySelector('.status-text');
        if (dot) {
            dot.className = 'status-dot ' + status;
        }
        if (text) {
            const labels = {
                connecting: 'Connecting...',
                connected: 'Connected',
                disconnected: 'Disconnected',
                reconnecting: 'Reconnecting...',
                error: 'Error'
            };
            text.textContent = labels[status] || status;
        }
    }

    get messagesPerSecond() {
        const elapsed = (Date.now() - this._lastMessageTime) / 1000;
        if (elapsed > 5) return 0;
        return this._messageCount;
    }

    resetCounter() {
        const count = this._messageCount;
        this._messageCount = 0;
        return count;
    }
}
