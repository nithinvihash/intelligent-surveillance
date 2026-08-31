// PheNex Frontend - API Communication
// Configured for your existing HTML structure

const API_BASE = 'http://localhost:8000';

// DOM Elements (matching your HTML IDs)
const apiStatusEl = document.getElementById('api-status');
const wsStatusEl = document.getElementById('ws-status');
const videoStatusEl = document.getElementById('video-status');
const totalEventsEl = document.getElementById('total-events');
const totalObjectsEl = document.getElementById('total-objects');
const lineCrossingsEl = document.getElementById('line-crossings');
const zoneEntriesEl = document.getElementById('zone-entries');
const eventsContainerEl = document.getElementById('events-container');
const alertsContainerEl = document.getElementById('alerts-container');
const eventChartCanvas = document.getElementById('eventChart');

let eventChart = null;
let wsConnected = false;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    console.log('PheNex Dashboard initializing...');
    
    checkApiHealth();
    initWebSocket();
    loadStats();
    loadEvents();
    initChart();
    
    // Refresh stats every 5 seconds
    setInterval(loadStats, 5000);
    setInterval(loadEvents, 5000);
});

// ============= API HEALTH CHECK =============
function checkApiHealth() {
    fetch(`${API_BASE}/api/health`)
        .then(response => response.json())
        .then(data => {
            console.log('✅ Backend healthy:', data);
            if (apiStatusEl) {
                apiStatusEl.textContent = '✅ API: Connected';
                apiStatusEl.style.color = '#00ff88';
            }
        })
        .catch(error => {
            console.error('❌ Backend connection error:', error);
            if (apiStatusEl) {
                apiStatusEl.textContent = '❌ API: Offline';
                apiStatusEl.style.color = '#ff4444';
            }
        });
}

// ============= LOAD STATISTICS =============
function loadStats() {
    fetch(`${API_BASE}/api/stats`)
        .then(response => response.json())
        .then(data => {
            console.log('📊 Stats received:', data);
            
            // Update stat cards
            if (totalEventsEl) {
                totalEventsEl.textContent = data.total_events || 0;
            }
            
            if (totalObjectsEl) {
                totalObjectsEl.textContent = data.total_objects || 0;
            }
            
            if (lineCrossingsEl) {
                lineCrossingsEl.textContent = data.line_crossings || 0;
            }
            
            if (zoneEntriesEl) {
                zoneEntriesEl.textContent = data.zone_entries || 0;
            }
            
            // Update chart if available
            if (eventChart && data.events_by_type) {
                updateChart(data.events_by_type);
            }
        })
        .catch(error => {
            console.error('Error loading stats:', error);
            if (apiStatusEl) {
                apiStatusEl.textContent = '⚠️ API: Error';
                apiStatusEl.style.color = '#ffaa00';
            }
        });
}

// ============= LOAD EVENTS =============
function loadEvents() {
    fetch(`${API_BASE}/api/events?limit=50`)
        .then(response => response.json())
        .then(data => {
            console.log('📋 Events received:', data);
            
            // Handle different response formats
            let events = [];
            if (Array.isArray(data)) {
                events = data;
            } else if (data.events && Array.isArray(data.events)) {
                events = data.events;
            } else if (data.data && Array.isArray(data.data)) {
                events = data.data;
            }
            
            console.log('✅ Parsed events:', events.length);
            
            // Update events container
            if (eventsContainerEl) {
                if (events.length === 0) {
                    eventsContainerEl.innerHTML = '<p class="empty-state">No events yet</p>';
                    return;
                }
                
                eventsContainerEl.innerHTML = events.map(event => `
                    <div class="event-item">
                        <div class="event-header">
                            <span class="event-type">${event.type || 'unknown'}</span>
                            <span class="event-class badge">${event.class || 'N/A'}</span>
                            <span class="event-time">${formatTime(event.timestamp)}</span>
                        </div>
                        <div class="event-details">
                            <span>Track: ${event.track_id || 'N/A'}</span>
                            <span>Conf: ${(event.confidence || 0).toFixed(2)}</span>
                            <span>Risk: ${(event.risk_score || 0).toFixed(2)}</span>
                        </div>
                    </div>
                `).join('');
            }
            
            // Update alerts (high risk events)
            if (alertsContainerEl) {
                const alerts = events.filter(e => (e.risk_score || 0) > 0.7);
                
                if (alerts.length === 0) {
                    alertsContainerEl.innerHTML = '<p class="empty-state">No high-risk alerts</p>';
                    return;
                }
                
                alertsContainerEl.innerHTML = alerts.slice(0, 5).map(event => `
                    <div class="alert-item alert-${getSeverity(event.risk_score)}">
                        <div class="alert-header">
                            <span class="alert-type">${event.type || 'unknown'}</span>
                            <span class="alert-severity">${getSeverityLabel(event.risk_score)}</span>
                        </div>
                        <div class="alert-details">
                            ${event.class || 'Unknown'} - Risk: ${(event.risk_score || 0).toFixed(2)}
                        </div>
                        <div class="alert-time">${formatTime(event.timestamp)}</div>
                    </div>
                `).join('');
            }
        })
        .catch(error => {
            console.error('Error loading events:', error);
            if (eventsContainerEl) {
                eventsContainerEl.innerHTML = '<p class="empty-state" style="color: #f44;">Error loading events</p>';
            }
        });
}

// ============= WEBSOCKET REAL-TIME UPDATES =============
function initWebSocket() {
    try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//localhost:8000/ws`;
        
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('✅ WebSocket connected');
            wsConnected = true;
            if (wsStatusEl) {
                wsStatusEl.textContent = '✅ WebSocket: Connected';
                wsStatusEl.style.color = '#00ff88';
            }
        };
        
        ws.onmessage = (event) => {
            console.log('📨 WebSocket message received');
            // Refresh data when events arrive
            loadStats();
            loadEvents();
        };
        
        ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            if (wsStatusEl) {
                wsStatusEl.textContent = '❌ WebSocket: Error';
                wsStatusEl.style.color = '#ff4444';
            }
        };
        
        ws.onclose = () => {
            console.log('⚠️ WebSocket closed, reconnecting...');
            wsConnected = false;
            if (wsStatusEl) {
                wsStatusEl.textContent = '⚠️ WebSocket: Reconnecting...';
                wsStatusEl.style.color = '#ffaa00';
            }
            // Try to reconnect after 3 seconds
            setTimeout(initWebSocket, 3000);
        };
    } catch (error) {
        console.error('WebSocket init error:', error);
        if (wsStatusEl) {
            wsStatusEl.textContent = '❌ WebSocket: Failed';
            wsStatusEl.style.color = '#ff4444';
        }
    }
}

// ============= CHART INITIALIZATION =============
function initChart() {
    if (!eventChartCanvas) {
        console.warn('Chart canvas not found');
        return;
    }
    
    const ctx = eventChartCanvas.getContext('2d');
    eventChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Line Crossing', 'Zone Entry', 'ANPR'],
            datasets: [{
                label: 'Events',
                data: [0, 0, 0],
                backgroundColor: [
                    'rgba(0, 255, 136, 0.8)',
                    'rgba(0, 150, 255, 0.8)',
                    'rgba(255, 200, 0, 0.8)'
                ],
                borderColor: [
                    'rgba(0, 255, 136, 1)',
                    'rgba(0, 150, 255, 1)',
                    'rgba(255, 200, 0, 1)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: '#fff'
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#aaa'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    ticks: {
                        color: '#aaa'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    });
}

// ============= UPDATE CHART =============
function updateChart(eventsData) {
    if (!eventChart) return;
    
    eventChart.data.datasets[0].data = [
        eventsData.line_crossed || 0,
        eventsData.zone_entry || 0,
        eventsData.anpr || 0
    ];
    eventChart.update();
}

// ============= UTILITY FUNCTIONS =============
function formatTime(timestamp) {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString();
}

function getSeverity(riskScore) {
    if (riskScore >= 0.8) return 'critical';
    if (riskScore >= 0.6) return 'high';
    return 'medium';
}

function getSeverityLabel(riskScore) {
    if (riskScore >= 0.8) return '🔴 CRITICAL';
    if (riskScore >= 0.6) return '🟠 HIGH';
    return '🟡 MEDIUM';
}

// ============= CONTROL FUNCTIONS =============
function exportEvents() {
    fetch(`${API_BASE}/api/events/export`)
        .then(response => response.json())
        .then(data => {
            const json = JSON.stringify(data, null, 2);
            const blob = new Blob([json], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `events_${Date.now()}.json`;
            a.click();
            URL.revokeObjectURL(url);
            alert('✅ Events exported successfully');
        })
        .catch(error => alert('❌ Export failed: ' + error));
}

function clearEvents() {
    if (confirm('⚠️ Clear all events? This cannot be undone.')) {
        fetch(`${API_BASE}/api/events/clear`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                alert('✅ Events cleared');
                loadStats();
                loadEvents();
            })
            .catch(error => alert('❌ Clear failed: ' + error));
    }
}

function refreshDashboard() {
    console.log('🔄 Manual refresh triggered');
    checkApiHealth();
    loadStats();
    loadEvents();
    alert('✅ Dashboard refreshed');
}

// ============= PAGE VISIBILITY HANDLING =============
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
        console.log('📱 Page became visible, refreshing...');
        loadStats();
        loadEvents();
    }
});

console.log('✅ App.js loaded successfully');