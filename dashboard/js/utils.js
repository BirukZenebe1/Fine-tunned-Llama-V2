/* ─── Utility Functions ───────────────────────────────────────── */

/**
 * Throttle function execution to at most once per interval.
 */
function throttle(fn, interval) {
    let lastCall = 0;
    return function (...args) {
        const now = Date.now();
        if (now - lastCall >= interval) {
            lastCall = now;
            return fn.apply(this, args);
        }
    };
}

/**
 * Format a number with locale-appropriate separators.
 */
function formatNumber(n, decimals = 1) {
    if (n === null || n === undefined || isNaN(n)) return '--';
    if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + 'M';
    if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return n.toFixed(decimals);
}

/**
 * Format a timestamp to a short time string.
 */
function formatTime(tsMs) {
    const d = new Date(tsMs);
    return d.toLocaleTimeString('en-US', { hour12: false });
}

/**
 * Format relative time (e.g., "2s ago", "1m ago").
 */
function timeAgo(tsMs) {
    const diff = Date.now() - tsMs;
    if (diff < 1000) return 'just now';
    if (diff < 60000) return Math.floor(diff / 1000) + 's ago';
    if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
    return Math.floor(diff / 3600000) + 'h ago';
}

/**
 * Apply a CSS class briefly for animation.
 */
function flashElement(el, className = 'highlight', duration = 500) {
    el.classList.add(className);
    setTimeout(() => el.classList.remove(className), duration);
}

/**
 * Safely update text content of an element by ID.
 */
function updateText(id, value) {
    const el = document.getElementById(id);
    if (el) {
        const oldValue = el.textContent;
        el.textContent = value;
        if (oldValue !== value) {
            flashElement(el);
        }
    }
}
