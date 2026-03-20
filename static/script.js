// Global variables
let refreshInterval = null;
let tickInterval = null;
let isConnecting = false;

// DOM Elements
const connectBtn = document.getElementById('connect-btn');
const disconnectBtn = document.getElementById('disconnect-btn');
const startBotBtn = document.getElementById('start-bot');
const stopBotBtn = document.getElementById('stop-bot');
const manualBuyBtn = document.getElementById('manual-buy');
const manualSellBtn = document.getElementById('manual-sell');
const closeAllBtn = document.getElementById('close-all');
const saveSettingsBtn = document.getElementById('save-settings');
const connectionStatus = document.getElementById('connection-status');
const botStatus = document.getElementById('bot-status');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Page loaded, initializing...');
    loadSettings();
    setupEventListeners();
    refreshData(); // Initial data load
});

function setupEventListeners() {
    console.log('Setting up event listeners');
    
    connectBtn.addEventListener('click', (e) => {
        e.preventDefault();
        connectToMT5();
    });
    
    disconnectBtn.addEventListener('click', (e) => {
        e.preventDefault();
        disconnectFromMT5();
    });
    
    startBotBtn.addEventListener('click', (e) => {
        e.preventDefault();
        startBot();
    });
    
    stopBotBtn.addEventListener('click', (e) => {
        e.preventDefault();
        stopBot();
    });
    
    manualBuyBtn.addEventListener('click', (e) => {
        e.preventDefault();
        manualTrade('BUY');
    });
    
    manualSellBtn.addEventListener('click', (e) => {
        e.preventDefault();
        manualTrade('SELL');
    });
    
    closeAllBtn.addEventListener('click', (e) => {
        e.preventDefault();
        closeAllPositions();
    });
    
    saveSettingsBtn.addEventListener('click', (e) => {
        e.preventDefault();
        saveSettings();
    });
}

async function connectToMT5() {
    if (isConnecting) return;
    
    const symbol = document.getElementById('symbol-select').value;
    isConnecting = true;
    connectBtn.disabled = true;
    connectBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Connecting...';
    
    try {
        console.log('Connecting to MT5 with symbol:', symbol);
        const response = await fetch('/api/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol })
        });
        
        const data = await response.json();
        console.log('Connection response:', data);
        
        if (data.status === 'success') {
            connectionStatus.textContent = 'Connected';
            connectionStatus.className = 'badge bg-success me-2';
            disconnectBtn.disabled = false;
            startBotBtn.disabled = false;
            manualBuyBtn.disabled = false;
            manualSellBtn.disabled = false;
            closeAllBtn.disabled = false;
            
            // Start refreshing data
            startDataRefresh();
            startTickSimulation();
            
            showNotification('Connected to MT5 successfully', 'success');
            refreshData(); // Immediate refresh
        } else {
            showNotification('Connection failed: ' + data.message, 'danger');
            connectionStatus.textContent = 'Connection Failed';
            connectionStatus.className = 'badge bg-danger me-2';
        }
    } catch (error) {
        console.error('Connection error:', error);
        showNotification('Error connecting to MT5: ' + error.message, 'danger');
        connectionStatus.textContent = 'Connection Error';
        connectionStatus.className = 'badge bg-danger me-2';
    } finally {
        isConnecting = false;
        connectBtn.disabled = false;
        connectBtn.innerHTML = '<i class="bi bi-link"></i> Connect to MT5';
    }
}

async function disconnectFromMT5() {
    try {
        console.log('Disconnecting from MT5');
        const response = await fetch('/api/disconnect', { method: 'POST' });
        const data = await response.json();
        
        if (data.status === 'success') {
            connectionStatus.textContent = 'Disconnected';
            connectionStatus.className = 'badge bg-secondary me-2';
            disconnectBtn.disabled = true;
            startBotBtn.disabled = true;
            stopBotBtn.disabled = true;
            manualBuyBtn.disabled = true;
            manualSellBtn.disabled = true;
            closeAllBtn.disabled = true;
            botStatus.textContent = 'Bot Stopped';
            botStatus.className = 'badge bg-danger';
            
            // Stop refreshing data
            stopDataRefresh();
            stopTickSimulation();
            
            showNotification('Disconnected from MT5', 'info');
        } else {
            showNotification('Disconnect failed: ' + data.message, 'danger');
        }
    } catch (error) {
        console.error('Disconnect error:', error);
        showNotification('Error disconnecting', 'danger');
    }
}

async function startBot() {
    try {
        console.log('Starting bot');
        const response = await fetch('/api/start', { method: 'POST' });
        const data = await response.json();
        
        if (data.status === 'success') {
            botStatus.textContent = 'Bot Running';
            botStatus.className = 'badge bg-success';
            startBotBtn.disabled = true;
            stopBotBtn.disabled = false;
            showNotification('Bot started', 'success');
        } else {
            showNotification('Start failed: ' + data.message, 'danger');
        }
    } catch (error) {
        console.error('Start bot error:', error);
        showNotification('Error starting bot', 'danger');
    }
}

async function stopBot() {
    try {
        console.log('Stopping bot');
        const response = await fetch('/api/stop', { method: 'POST' });
        const data = await response.json();
        
        if (data.status === 'success') {
            botStatus.textContent = 'Bot Stopped';
            botStatus.className = 'badge bg-danger';
            startBotBtn.disabled = false;
            stopBotBtn.disabled = true;
            showNotification('Bot stopped', 'info');
        } else {
            showNotification('Stop failed: ' + data.message, 'danger');
        }
    } catch (error) {
        console.error('Stop bot error:', error);
        showNotification('Error stopping bot', 'danger');
    }
}

async function manualTrade(type) {
    const lotSize = parseFloat(document.getElementById('manual-lot').value);
    
    if (isNaN(lotSize) || lotSize <= 0) {
        showNotification('Invalid lot size', 'danger');
        return;
    }
    
    try {
        console.log(`Executing ${type} trade with lot size: ${lotSize}`);
        const response = await fetch('/api/execute_trade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, lot_size: lotSize })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showNotification(`${type} order placed successfully`, 'success');
            refreshData(); // Refresh immediately
        } else {
            showNotification('Trade failed: ' + data.message, 'danger');
        }
    } catch (error) {
        console.error('Trade error:', error);
        showNotification('Error executing trade', 'danger');
    }
}

async function closeAllPositions() {
    if (!confirm('Are you sure you want to close all positions?')) return;
    
    try {
        console.log('Closing all positions');
        const response = await fetch('/api/close_all', { method: 'POST' });
        const data = await response.json();
        
        if (data.status === 'success') {
            showNotification('All positions closed', 'success');
            refreshData();
        } else {
            showNotification('Failed to close positions: ' + data.message, 'danger');
        }
    } catch (error) {
        console.error('Close all error:', error);
        showNotification('Error closing positions', 'danger');
    }
}

async function closePosition(ticket) {
    if (!confirm(`Close position ${ticket}?`)) return;
    
    try {
        console.log(`Closing position: ${ticket}`);
        const response = await fetch(`/api/close_position/${ticket}`, { method: 'DELETE' });
        const data = await response.json();
        
        if (data.status === 'success') {
            showNotification(`Position ${ticket} closed`, 'success');
            refreshData();
        } else {
            showNotification('Failed to close position: ' + data.message, 'danger');
        }
    } catch (error) {
        console.error('Close position error:', error);
        showNotification('Error closing position', 'danger');
    }
}

async function saveSettings() {
    const settings = {
        scan_tf: document.getElementById('scan-tf').value,
        fast_ema: parseInt(document.getElementById('fast-ema').value),
        slow_ema: parseInt(document.getElementById('slow-ema').value),
        lot_size: parseFloat(document.getElementById('lot-size').value),
        max_grids: parseInt(document.getElementById('max-grids').value),
        gap_pips: parseFloat(document.getElementById('gap-pips').value),
        break_even_s: parseFloat(document.getElementById('break-even').value)
    };
    
    try {
        console.log('Saving settings:', settings);
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showNotification('Settings saved successfully', 'success');
        } else {
            showNotification('Save failed: ' + data.message, 'danger');
        }
    } catch (error) {
        console.error('Save settings error:', error);
        showNotification('Error saving settings', 'danger');
    }
}

async function loadSettings() {
    try {
        console.log('Loading settings');
        const response = await fetch('/api/settings');
        const settings = await response.json();
        
        document.getElementById('scan-tf').value = settings.scan_tf || 'H1';
        document.getElementById('fast-ema').value = settings.fast_ema || 13;
        document.getElementById('slow-ema').value = settings.slow_ema || 48;
        document.getElementById('lot-size').value = settings.lot_size || 0.01;
        document.getElementById('max-grids').value = settings.max_grids || 7;
        document.getElementById('gap-pips').value = settings.gap_pips || 15;
        document.getElementById('break-even').value = settings.break_even_s || 0.10;
        
        console.log('Settings loaded successfully');
    } catch (error) {
        console.error('Error loading settings:', error);
        showNotification('Error loading settings', 'danger');
    }
}

async function refreshData() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        console.log('Data refreshed:', data);
        
        // Update UI with data
        if (data.market) updateMarketData(data.market);
        if (data.account) updateAccountInfo(data.account);
        if (data.positions) updatePositionsTable(data.positions);
        
        // Update status based on connection
        if (data.connected) {
            connectionStatus.textContent = 'Connected';
            connectionStatus.className = 'badge bg-success me-2';
            disconnectBtn.disabled = false;
        } else {
            connectionStatus.textContent = 'Disconnected';
            connectionStatus.className = 'badge bg-secondary me-2';
            disconnectBtn.disabled = true;
        }
        
        // Update bot status
        if (data.bot_active) {
            botStatus.textContent = 'Bot Running';
            botStatus.className = 'badge bg-success';
            startBotBtn.disabled = true;
            stopBotBtn.disabled = false;
        } else {
            botStatus.textContent = 'Bot Stopped';
            botStatus.className = 'badge bg-danger';
            startBotBtn.disabled = false;
            stopBotBtn.disabled = true;
        }
        
    } catch (error) {
        console.error('Error refreshing data:', error);
    }
}

function updateMarketData(market) {
    if (!market) return;
    
    document.getElementById('market-symbol').textContent = market.symbol || '---';
    
    const price = market.close || market.bid || 0;
    document.getElementById('market-price').textContent = price.toFixed(5);
    document.getElementById('fast-ema-val').textContent = market.fast_ema ? market.fast_ema.toFixed(5) : '---';
    document.getElementById('slow-ema-val').textContent = market.slow_ema ? market.slow_ema.toFixed(5) : '---';
    
    const trendElement = document.getElementById('trend-indicator');
    if (market.trend === 'BULL') {
        trendElement.innerHTML = '<span class="badge bg-success" style="font-size: 1.2rem;">📈 BULLISH</span>';
    } else if (market.trend === 'BEAR') {
        trendElement.innerHTML = '<span class="badge bg-danger" style="font-size: 1.2rem;">📉 BEARISH</span>';
    } else {
        trendElement.innerHTML = '<span class="badge bg-secondary" style="font-size: 1.2rem;">➡️ NEUTRAL</span>';
    }
}

function updateAccountInfo(account) {
    if (!account) return;
    
    document.getElementById('balance').textContent = account.balance ? account.balance.toFixed(2) : '---';
    document.getElementById('equity').textContent = account.equity ? account.equity.toFixed(2) : '---';
    document.getElementById('free-margin').textContent = account.free_margin ? account.free_margin.toFixed(2) : '---';
    
    const profit = account.profit || 0;
    const plElement = document.getElementById('total-pl');
    plElement.textContent = profit.toFixed(2);
    
    if (profit > 0) {
        plElement.style.color = '#28a745';
        plElement.className = 'text-success';
    } else if (profit < 0) {
        plElement.style.color = '#dc3545';
        plElement.className = 'text-danger';
    } else {
        plElement.style.color = '#6c757d';
        plElement.className = '';
    }
}

function updatePositionsTable(positions) {
    const tbody = document.getElementById('positions-table');
    
    if (!positions || positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No open positions</td></tr>';
        return;
    }
    
    tbody.innerHTML = positions.map(pos => `
        <tr>
            <td>${pos.ticket}</td>
            <td><span class="badge ${pos.type === 'BUY' ? 'bg-success' : 'bg-danger'}">${pos.type}</span></td>
            <td>${pos.volume}</td>
            <td>${pos.price_open.toFixed(5)}</td>
            <td>${(pos.price_current || pos.price_open).toFixed(5)}</td>
            <td class="${pos.profit > 0 ? 'text-success' : (pos.profit < 0 ? 'text-danger' : '')}">
                ${pos.profit ? pos.profit.toFixed(2) : '0.00'}
            </td>
            <td>
                <button class="btn btn-sm btn-danger" onclick="closePosition(${pos.ticket})">
                    Close
                </button>
            </td>
        </tr>
    `).join('');
}

async function tickSimulation() {
    try {
        const response = await fetch('/api/tick');
        const data = await response.json();
        
        if (data.status === 'success') {
            refreshData(); // Refresh after tick
        }
    } catch (error) {
        console.error('Tick error:', error);
    }
}

function startDataRefresh() {
    if (refreshInterval) clearInterval(refreshInterval);
    refreshInterval = setInterval(refreshData, 2000);
}

function stopDataRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

function startTickSimulation() {
    if (tickInterval) clearInterval(tickInterval);
    tickInterval = setInterval(tickSimulation, 5000);
}

function stopTickSimulation() {
    if (tickInterval) {
        clearInterval(tickInterval);
        tickInterval = null;
    }
}

function showNotification(message, type) {
    // Create a temporary notification div
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Make closePosition available globally
window.closePosition = closePosition;