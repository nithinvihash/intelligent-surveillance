const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

let ws = null;
let eventChart = null;
let eventCounts = {
    'line_crossed': 0,
    'zone_entry': 0,
    'zone_exit': 0
};

document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard loading...');
    initWebSocket();
    updateStats();
    
    // Update stats every 5 seconds
    setInterval(updateStats, 5000);
    
    // Check API connection every 10 seconds
    setInterval(() => {
        fetch(`${API_URL}/api/health`)
            .then(() => updateStatus('api-status', 'API: Connected', 'connected'))
            .catch(() => updateStatus('api-status', 'API: Disconnected', 'error'));
    }, 10000);
});

function initWebSocket() {
    console.log('Connecting to WebSocket...');
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        console.log('✓ WebSocket connected');
        updateStatus('ws-status', 'WebSocket: Connected', 'connected');
    };

    ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            
            if (message.type === 'event') {
                handleNewEvent(message.data);
            } else if (message.type === 'heartbeat') {
                // Heartbeat received
            }
        } catch (e) {
            console.error('WebSocket message parse error:', e);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateStatus('ws-status', 'WebSocket: Error', 'error');
    };

    ws.onclose = () => {
        console.log('WebSocket closed, reconnecting...');
        updateStatus('ws-status', 'WebSocket: Reconnecting...', 'error');
        setTimeout(initWebSocket, 3000);
    };
}

function handleNewEvent(event) {
    console.log('📢 New event:', event);

    // Add to event log
    addEventToLog(event);

    // Add to alerts if high risk
    if (event.risk_score > 0.6) {
        addAlert(event);
        playAlertSound();
    }

    // Update event counts
    eventCounts[event.type] = (eventCounts[event.type] || 0) + 1;
    updateChart();
}

function addEventToLog(event) {
    const container = document.getElementById('events-container');
    
    if (container.querySelector('.empty-state')) {
        container.innerHTML = '';
    }

    const eventEl = document.createElement('div');
    eventEl.className = 'event-item';
    
    const time = new Date(event.timestamp * 1000).toLocaleTimeString();
    const riskClass = event.risk_score > 0.7 ? 'high-risk' : 'normal-risk';

    eventEl.innerHTML = `
        <div class="event-time">${time}</div>
        <div class="event-type">${event.type.replace('_', ' ').toUpperCase()}</div>
        <div class="event-details">
            Track #${event.track_id} | ${event.class} | Conf: ${(event.confidence * 100).toFixed(0)}%
        </div>
        <div class="event-risk ${riskClass}">Risk: ${(event.risk_score * 100).toFixed(0)}%</div>
    `;

    container.insertBefore(eventEl, container.firstChild);

    while (container.children.length > 20) {
        container.removeChild(container.lastChild);
    }
}

function addAlert(event) {
    const container = document.getElementById('alerts-container');
    
    if (container.querySelector('.empty-state')) {
        container.innerHTML = '';
    }

    const alertEl = document.createElement('div');
    alertEl.className = 'alert-item high-priority';

    const time = new Date(event.timestamp * 1000).toLocaleTimeString();

    alertEl.innerHTML = `
        <div class="alert-time">${time}</div>
        <div class="alert-message">
            ⚠️ HIGH PRIORITY: ${event.type.replace('_', ' ').toUpperCase()} - 
            Track #${event.track_id} (${event.class})
        </div>
        <div class="alert-risk">Risk Score: ${(event.risk_score * 100).toFixed(0)}%</div>
    `;

    container.insertBefore(alertEl, container.firstChild);

    while (container.children.length > 10) {
        container.removeChild(container.lastChild);
    }
}

function updateStats() {
    fetch(`${API_URL}/api/stats`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('total-events').textContent = data.total_events || 0;
            document.getElementById('total-objects').textContent = data.total_objects || 0;
            document.getElementById('line-crossings').textContent = data.line_crossings || 0;
            document.getElementById('zone-entries').textContent = data.zone_entries || 0;
            
            updateStatus('api-status', 'API: Connected', 'connected');
        })
        .catch(err => {
            console.error('Stats fetch error:', err);
            updateStatus('api-status', 'API: Error', 'error');
        });
}

function updateChart() {
    const ctx = document.getElementById('eventChart');
    
    if (!eventChart) {
        eventChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Line Crossed', 'Zone Entry', 'Zone Exit'],
                datasets: [{
                    label: 'Events',
                    data: [
                        eventCounts['line_crossed'] || 0,
                        eventCounts['zone_entry'] || 0,
                        eventCounts['zone_exit'] || 0
                    ],
                    backgroundColor: ['#3498db', '#2ecc71', '#e74c3c']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    } else {
        eventChart.data.datasets[0].data = [
            eventCounts['line_crossed'] || 0,
            eventCounts['zone_entry'] || 0,
            eventCounts['zone_exit'] || 0
        ];
        eventChart.update();
    }
}

function updateStatus(elementId, text, status) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = text;
        el.className = status === 'connected' ? 'status-connected' : 'status-error';
    }
}

function playAlertSound() {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gain = audioContext.createGain();
        
        oscillator.connect(gain);
        gain.connect(audioContext.destination);
        
        oscillator.frequency.value = 1000;
        gain.gain.setValueAtTime(0.3, audioContext.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    } catch (e) {
        console.log('Audio not available');
    }
}