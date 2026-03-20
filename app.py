from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import logging
import os
from mt5_client_real import MT5Client
from trading_bot import ProTrendGridBot
import threading
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-2024')
CORS(app)

# Initialize MT5 client and bot
mt5_client = MT5Client()
trading_bot = None
bot_active = False
bot_thread = None

bot_settings = {
    'scan_tf': 'H1',
    'fast_ema': 13,
    'slow_ema': 48,
    'lot_size': 0.01,
    'max_grids': 7,
    'gap_pips': 15.0,
    'break_even_s': 0.10,
    'magic': 888999,
    'symbol': 'XAUUSD'
}

def bot_worker():
    """Background thread for running the bot"""
    global trading_bot, bot_active
    
    while bot_active:
        try:
            if trading_bot and mt5_client.connected:
                trading_bot.process_tick()
            time.sleep(1)  # Process every second
        except Exception as e:
            logger.error(f"Bot worker error: {e}")
            time.sleep(5)

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/connect', methods=['POST'])
def connect():
    """Connect to MT5"""
    global mt5_client, trading_bot
    
    try:
        data = request.json
        symbol = data.get('symbol', 'XAUUSD')
        terminal_path = data.get('terminal_path', None)
        
        # Disconnect if already connected
        if mt5_client.connected:
            mt5_client.disconnect()
        
        # Connect to MT5
        if mt5_client.connect(symbol, terminal_path):
            bot_settings['symbol'] = symbol
            
            # Initialize trading bot
            trading_bot = ProTrendGridBot(mt5_client, bot_settings)
            
            logger.info(f"Connected to {symbol} successfully")
            
            # Get account info
            account = mt5_client.get_account_info()
            
            return jsonify({
                'status': 'success', 
                'message': f'Connected to {symbol}',
                'account': account
            })
        else:
            return jsonify({'status': 'error', 'message': 'Connection failed'}), 500
            
    except Exception as e:
        logger.error(f"Connection error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from MT5"""
    global mt5_client, bot_active, trading_bot, bot_thread
    
    try:
        # Stop bot if running
        if bot_active:
            stop_bot_internal()
        
        # Disconnect MT5
        mt5_client.disconnect()
        trading_bot = None
        
        return jsonify({'status': 'success', 'message': 'Disconnected'})
    except Exception as e:
        logger.error(f"Disconnect error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current system status"""
    try:
        positions = mt5_client.get_positions() if mt5_client.connected else []
        account = mt5_client.get_account_info() if mt5_client.connected else {}
        market = mt5_client.get_market_data(
            bot_settings['scan_tf'],
            bot_settings['fast_ema'],
            bot_settings['slow_ema']
        ) if mt5_client.connected else {}
        
        total_profit = sum(p.get('profit', 0) for p in positions)
        
        return jsonify({
            'connected': mt5_client.connected,
            'bot_active': bot_active,
            'positions': positions,
            'account': account,
            'market': market,
            'settings': bot_settings,
            'positions_count': len(positions),
            'total_profit': total_profit
        })
    except Exception as e:
        logger.error(f"Status error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
def settings():
    """Get or update bot settings"""
    global bot_settings, trading_bot
    
    if request.method == 'GET':
        return jsonify(bot_settings)
    
    elif request.method == 'POST':
        try:
            data = request.json
            for key in bot_settings:
                if key in data:
                    bot_settings[key] = data[key]
            
            # Update trading bot settings if it exists
            if trading_bot:
                trading_bot.settings = bot_settings
            
            # Update MT5 client settings
            mt5_client.update_settings(magic=bot_settings['magic'])
            
            logger.info(f"Settings updated: {bot_settings}")
            return jsonify({'status': 'success', 'settings': bot_settings})
        except Exception as e:
            logger.error(f"Settings error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

def start_bot_internal():
    """Internal function to start bot"""
    global bot_active, bot_thread, trading_bot
    
    if not mt5_client.connected:
        return False
    
    if bot_active:
        return True
    
    if trading_bot:
        bot_active = True
        trading_bot.start()
        
        # Start bot thread
        bot_thread = threading.Thread(target=bot_worker, daemon=True)
        bot_thread.start()
        
        logger.info("Bot started")
        return True
    
    return False

def stop_bot_internal():
    """Internal function to stop bot"""
    global bot_active, trading_bot
    
    bot_active = False
    if trading_bot:
        trading_bot.stop()
    
    logger.info("Bot stopped")
    return True

@app.route('/api/start', methods=['POST'])
def start_bot():
    """Start the trading bot"""
    if start_bot_internal():
        return jsonify({'status': 'success', 'message': 'Bot started'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to start bot'}), 500

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Stop the trading bot"""
    stop_bot_internal()
    return jsonify({'status': 'success', 'message': 'Bot stopped'})

@app.route('/api/execute_trade', methods=['POST'])
def execute_trade():
    """Execute a manual trade"""
    try:
        if not mt5_client.connected:
            return jsonify({'status': 'error', 'message': 'Not connected to MT5'}), 400
        
        data = request.json
        order_type = data.get('type', 'BUY')
        lot_size = float(data.get('lot_size', bot_settings['lot_size']))
        sl_pips = float(data.get('sl_pips', 0))
        tp_pips = float(data.get('tp_pips', 0))
        
        if mt5_client.execute_trade(order_type, lot_size, "Manual Trade", sl_pips, tp_pips):
            logger.info(f"Manual trade executed: {order_type} {lot_size}")
            return jsonify({'status': 'success', 'message': f'{order_type} order placed'})
        else:
            return jsonify({'status': 'error', 'message': 'Trade failed'}), 500
    except Exception as e:
        logger.error(f"Execute trade error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/close_position/<int:ticket>', methods=['DELETE'])
def close_position(ticket):
    """Close a specific position"""
    try:
        if mt5_client.close_position(ticket):
            logger.info(f"Position {ticket} closed")
            return jsonify({'status': 'success', 'message': f'Position {ticket} closed'})
        else:
            return jsonify({'status': 'error', 'message': 'Close failed'}), 500
    except Exception as e:
        logger.error(f"Close position error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/close_all', methods=['POST'])
def close_all():
    """Close all positions"""
    try:
        if mt5_client.close_all_positions():
            logger.info("All positions closed")
            return jsonify({'status': 'success', 'message': 'All positions closed'})
        else:
            return jsonify({'status': 'error', 'message': 'Close all failed'}), 500
    except Exception as e:
        logger.error(f"Close all error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/market_data', methods=['GET'])
def market_data():
    """Get current market data"""
    try:
        data = mt5_client.get_market_data(
            bot_settings['scan_tf'],
            bot_settings['fast_ema'],
            bot_settings['slow_ema']
        )
        return jsonify(data)
    except Exception as e:
        logger.error(f"Market data error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/tick', methods=['GET'])
def tick():
    """Manual tick trigger"""
    if bot_active and mt5_client.connected and trading_bot:
        trading_bot.process_tick()
        return jsonify({'status': 'success', 'message': 'Tick processed'})
    return jsonify({'status': 'inactive'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)