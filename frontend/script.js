/**
 * Smart API Health Monitor — Frontend Script
 * Handles login, registration, dashboard, chart, and API CRUD.
 */

const API_BASE_URL = window.location.origin + '/api';

// DOM references (null-safe — only some exist per page)
const apiCardsContainer = document.getElementById('apiCardsContainer');
const openAddModalBtn   = document.getElementById('openAddModalBtn');
const closeAddModalBtn  = document.getElementById('closeAddModalBtn');
const addApiModal       = document.getElementById('addApiModal');
const addApiForm        = document.getElementById('addApiForm');
const toast             = document.getElementById('toast');
const loginForm         = document.getElementById('loginForm');
const loginError        = document.getElementById('loginError');
const logoutBtn         = document.getElementById('logoutBtn');
const sessionUser       = document.getElementById('sessionUser');
const registerForm      = document.getElementById('registerForm');
const registerError     = document.getElementById('registerError');

let responseChart;
let refreshTimer;

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    if (loginForm) {
        initLoginPage();
        return;
    }

    if (registerForm) {
        initRegisterPage();
        return;
    }

    if (apiCardsContainer) {
        initDashboard();
    }
});

// ---------------------------------------------------------------------------
// Login page
// ---------------------------------------------------------------------------

async function initLoginPage() {
    const sessionData = await fetchAuthSession();
    if (sessionData.authenticated) {
        window.location.replace('/dashboard');
        return;
    }
    loginForm.addEventListener('submit', handleLogin);
}

async function handleLogin(event) {
    event.preventDefault();
    const button = event.target.querySelector('button[type="submit"]');
    const originalText = button.innerText;
    const email    = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;

    loginError.classList.add('hidden');
    loginError.textContent = '';
    button.disabled = true;
    button.innerText = 'Signing In…';

    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        const payload = await response.json();

        if (!response.ok) {
            showAuthError(loginError, payload.error || 'Unable to sign in.');
            return;
        }

        window.location.replace('/dashboard');
    } catch (_) {
        showAuthError(loginError, 'Unable to reach the server.');
    } finally {
        button.disabled  = false;
        button.innerText = originalText;
    }
}

// ---------------------------------------------------------------------------
// Register page
// ---------------------------------------------------------------------------

async function initRegisterPage() {
    const sessionData = await fetchAuthSession();
    if (sessionData.authenticated) {
        window.location.replace('/dashboard');
        return;
    }
    registerForm.addEventListener('submit', handleRegister);
}

async function handleRegister(event) {
    event.preventDefault();
    const button = event.target.querySelector('button[type="submit"]');
    const originalText = button.innerText;

    const email    = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;
    const confirm  = document.getElementById('reg-confirm').value;

    registerError.classList.add('hidden');
    registerError.textContent = '';

    // Client-side quick validation
    if (!email || !password || !confirm) {
        showAuthError(registerError, 'All fields are required.');
        return;
    }
    if (password.length < 8) {
        showAuthError(registerError, 'Password must be at least 8 characters.');
        return;
    }
    if (password !== confirm) {
        showAuthError(registerError, 'Passwords do not match.');
        return;
    }

    button.disabled  = true;
    button.innerText = 'Creating Account…';

    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, confirm_password: confirm }),
        });
        const payload = await response.json();

        if (!response.ok) {
            showAuthError(registerError, payload.error || 'Registration failed.');
            return;
        }

        // Account created + auto-logged-in by server → redirect to dashboard
        window.location.replace('/dashboard');
    } catch (_) {
        showAuthError(registerError, 'Unable to reach the server.');
    } finally {
        button.disabled  = false;
        button.innerText = originalText;
    }
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

async function initDashboard() {
    const sessionData = await requireAuthenticated();
    if (!sessionData) return;

    if (sessionUser) {
        sessionUser.textContent = sessionData.user.email;
    }

    wireDashboardEvents();
    await fetchStatus();
    refreshTimer = window.setInterval(fetchStatus, 5000);
}

function wireDashboardEvents() {
    if (openAddModalBtn) {
        openAddModalBtn.addEventListener('click', () => {
            addApiModal.classList.remove('hidden');
        });
    }

    if (closeAddModalBtn) {
        closeAddModalBtn.addEventListener('click', () => {
            addApiModal.classList.add('hidden');
        });
    }

    if (addApiModal) {
        addApiModal.addEventListener('click', (event) => {
            if (event.target === addApiModal) {
                addApiModal.classList.add('hidden');
            }
        });
    }

    if (addApiForm) {
        addApiForm.addEventListener('submit', handleAddApi);
    }

    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
}

// ---------------------------------------------------------------------------
// Shared auth helpers
// ---------------------------------------------------------------------------

async function fetchAuthSession() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/session`);
        return await response.json();
    } catch (_) {
        return { authenticated: false };
    }
}

async function requireAuthenticated() {
    const sessionData = await fetchAuthSession();
    if (!sessionData.authenticated) {
        if (refreshTimer) window.clearInterval(refreshTimer);
        window.location.replace('/');
        return null;
    }
    return sessionData;
}

async function handleLogout() {
    try {
        await fetch(`${API_BASE_URL}/auth/logout`, { method: 'POST' });
    } finally {
        window.location.replace('/');
    }
}

function showAuthError(element, message) {
    element.textContent = message;
    element.classList.remove('hidden');
}

// ---------------------------------------------------------------------------
// API CRUD
// ---------------------------------------------------------------------------

async function handleAddApi(event) {
    event.preventDefault();
    const button = event.target.querySelector('button[type="submit"]');
    const originalText = button.innerText;
    button.innerText = 'Adding…';
    button.disabled  = true;

    const payload = {
        name:      document.getElementById('name').value.trim(),
        url:       document.getElementById('url').value.trim(),
        interval:  parseInt(document.getElementById('interval').value, 10),
        threshold: parseInt(document.getElementById('threshold').value, 10),
    };

    try {
        const response = await fetch(`${API_BASE_URL}/add_api`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await handleApiResponse(response);
        showToast(data.message || 'API added successfully', 'success');
        addApiModal.classList.add('hidden');
        addApiForm.reset();
        await fetchStatus();
    } catch (error) {
        if (error.message !== 'AUTH_REQUIRED') {
            showToast(error.message || 'Failed to add API', 'error');
        }
    } finally {
        button.innerText = originalText;
        button.disabled  = false;
    }
}

async function fetchStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/get_status`);
        const data = await handleApiResponse(response);
        renderCards(data);
        updateLineChartHistory(data);
    } catch (error) {
        if (error.message !== 'AUTH_REQUIRED') {
            console.error('Error fetching status', error);
            showToast('Error loading API status', 'error');
        }
    }
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

function renderCards(apis) {
    if (!apiCardsContainer) return;

    // Update stats bar
    updateStats(apis);

    // Update count badge
    const countBadge = document.getElementById('apiCount');
    if (countBadge) countBadge.textContent = apis.length;

    if (apis.length === 0) {
        apiCardsContainer.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📡</span>
                <h3>No APIs tracked yet</h3>
                <p>Click <strong>⊕ Add API</strong> to start monitoring your endpoints.</p>
            </div>`;
        return;
    }

    const stateIcon = { OK: '✅', SLOW: '⚠️', FAIL: '🔴', PENDING: '⏳' };
    const stateLabel = { OK: 'Healthy', SLOW: 'Slow', FAIL: 'Down', PENDING: 'Pending' };

    apiCardsContainer.innerHTML = apis.map((api) => {
        // Compute response bar width (cap at 100%, treat > 2000ms as 100%)
        const barPct = Math.min(100, ((api.response_time || 0) / 2000) * 100).toFixed(1);
        const urlDisplay = escHtml(api.url || '').replace(/^https?:\/\//, '');
        return `
        <div class="api-card state-${api.state}">
            <div class="card-header">
                <div class="card-name-wrap">
                    <div class="card-api-icon">${stateIcon[api.state] || '🔵'}</div>
                    <h3 title="${escHtml(api.name)}">${escHtml(api.name)}</h3>
                </div>
                <span class="status-badge">${stateLabel[api.state] || api.state}</span>
            </div>
            <div class="card-metrics">
                <div class="metric-row">
                    <span class="metric-label">Response Time</span>
                    <span class="metric-value highlight">${api.response_time != null ? api.response_time + ' ms' : 'N/A'}</span>
                </div>
                <div class="response-bar-wrap">
                    <div class="response-bar-track"><div class="response-bar-fill" style="width:${barPct}%"></div></div>
                </div>
                <div class="metric-row">
                    <span class="metric-label">HTTP Status</span>
                    <span class="metric-value">${api.status_code || 'N/A'}</span>
                </div>
            </div>
            <div class="url-chip">🌐 ${urlDisplay}</div>
            <div class="card-meta">
                <span>⏱ ${api.interval}s interval</span>
                <span>⚡ ${api.threshold}ms threshold</span>
            </div>
            <button class="delete-btn" data-id="${api.id}" onclick="deleteApi(${api.id})">🗑 Remove</button>
        </div>
    `;
    }).join('');
}

function updateStats(apis) {
    const total = apis.length;
    const ok    = apis.filter(a => a.state === 'OK').length;
    const slow  = apis.filter(a => a.state === 'SLOW').length;
    const fail  = apis.filter(a => a.state === 'FAIL').length;
    const uptimePct = total > 0 ? (((ok + slow) / total) * 100).toFixed(1) : '—';

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('statTotal',  total || '—');
    set('statOk',     ok    || '—');
    set('statSlow',   slow  || '—');
    set('statFail',   fail  || '—');
    set('statUptime', total > 0 ? uptimePct + '%' : '—');
}

/** Minimal HTML escaping to prevent XSS via API names. */
function escHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

async function deleteApi(id) {
    if (!window.confirm('Are you sure you want to stop tracking this API?')) return;

    try {
        const response = await fetch(`${API_BASE_URL}/delete_api/${id}`, { method: 'DELETE' });
        const data = await handleApiResponse(response);
        showToast(data.message || 'API deleted', 'success');
        await fetchStatus();
    } catch (error) {
        if (error.message !== 'AUTH_REQUIRED') {
            showToast(error.message || 'Failed to delete API', 'error');
        }
    }
}

// Expose for inline onclick handlers
window.deleteApi = deleteApi;

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------

function showToast(message, type = 'info') {
    if (!toast) return;
    const textEl = document.getElementById('toastText');
    if (textEl) {
        textEl.textContent = message;
    } else {
        toast.textContent = message;
    }
    toast.className   = `toast ${type}`;
    window.clearTimeout(toast._hideTimer);
    toast._hideTimer = window.setTimeout(() => {
        toast.classList.add('hidden');
    }, 3800);
}

// ---------------------------------------------------------------------------
// Response handling
// ---------------------------------------------------------------------------

async function handleApiResponse(response) {
    const data = await response.json().catch(() => ({}));

    if (response.status === 401) {
        window.location.replace('/');
        throw new Error('AUTH_REQUIRED');
    }

    if (!response.ok) {
        throw new Error(data.error || 'Request failed');
    }

    return data;
}

// ---------------------------------------------------------------------------
// Chart
// ---------------------------------------------------------------------------

async function updateLineChartHistory(apis) {
    const ctxElement = document.getElementById('responseChart');
    if (!ctxElement || typeof Chart === 'undefined') return;

    if (!responseChart) {
        Chart.defaults.color = '#94A3B8';
        Chart.defaults.borderColor = 'rgba(20, 184, 166, 0.12)';

        // Premium indigo/violet/sky palette
        const PALETTE = [
            '#2DD4BF', '#0EA5E9', '#8B5CF6', '#34D399',
            '#6366F1', '#FBBF24', '#F87171', '#EC4899'
        ];

        responseChart = new Chart(ctxElement, {
            type: 'line',
            data: { labels: [], datasets: [] },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 900, easing: 'easeInOutQuart' },
                elements: {
                    line:  { tension: 0.42, borderWidth: 2.5 },
                    point: { radius: 4, hoverRadius: 8, borderWidth: 2.5, backgroundColor: '#090D16', hoverBorderWidth: 3 },
                },
                plugins: {
                    legend: {
                        labels: {
                            color: '#94A3B8',
                            font: { family: 'Inter', size: 12, weight: '600' },
                            usePointStyle: true,
                            pointStyleWidth: 10,
                            padding: 20,
                        },
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: '#0F172A',
                        borderColor: 'rgba(20, 184, 166, 0.35)',
                        borderWidth: 1.5,
                        titleColor: '#FFFFFF',
                        bodyColor: '#94A3B8',
                        padding: 14,
                        cornerRadius: 12,
                        titleFont: { family: 'Manrope', weight: '700', size: 13 },
                        bodyFont:  { family: 'JetBrains Mono', size: 12 },
                        boxShadow: '0 8px 32px rgba(0,0,0,0.30)',
                        callbacks: {
                            label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y} ms`,
                        }
                    },
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(20, 184, 166, 0.08)', drawBorder: false },
                        ticks: { color: '#94A3B8', font: { size: 11, family: 'Inter' } },
                        border: { display: false },
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(20, 184, 166, 0.08)', drawBorder: false },
                        ticks: { color: '#94A3B8', font: { size: 11, family: 'Inter' } },
                        border: { display: false },
                        title: {
                            display: true,
                            text: 'Response Time (ms)',
                            color: '#94A3B8',
                            font: { size: 11, family: 'Inter', weight: '600' },
                        },
                    },
                },
            },
        });
        responseChart._palette = PALETTE;
    }

    const datasets = [];
    let commonLabels = [];

    for (let i = 0; i < apis.length; i++) {
        const api = apis[i];
        try {
            const response = await fetch(`${API_BASE_URL}/logs/${api.id}`);
            const logs = await handleApiResponse(response);

            if (logs.length > commonLabels.length) {
                commonLabels = logs.map((log) => {
                    const d = new Date(log.timestamp);
                    return [
                        d.getHours().toString().padStart(2, '0'),
                        d.getMinutes().toString().padStart(2, '0'),
                        d.getSeconds().toString().padStart(2, '0'),
                    ].join(':');
                });
            }

            const palette = responseChart._palette || ['#6366F1','#8B5CF6','#0EA5E9','#10B981'];
            const color   = palette[i % palette.length];
            const bgColor = color + '20';

            datasets.push({
                label:           api.name,
                data:            logs.map((log) => log.response_time),
                borderColor:     color,
                backgroundColor: bgColor,
                borderWidth:     2,
                fill:            true,
            });
        } catch (error) {
            if (error.message !== 'AUTH_REQUIRED') {
                console.error('Error fetching logs for chart', error);
            }
        }
    }

    responseChart.data.labels   = commonLabels.length > 0 ? commonLabels : ['No Data'];
    responseChart.data.datasets = datasets;
    responseChart.update();
}
