import logging
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class ProTrendGridBot:
    def __init__(self, mt5_client, settings):
        self.mt5 = mt5_client
        self.settings = settings
        self.is_running = False
        
    def start(self):
        """Start the trading bot"""
        self.is_running = True
        logger.info("ProTrend Grid Bot started")
        
    def stop(self):
        """Stop the trading bot"""
        self.is_running = False
        logger.info("ProTrend Grid Bot stopped")
        
    def process_tick(self):
        """Process a single tick - main bot logic"""
        if not self.is_running:
            return
        
        if not self.mt5.connected:
            logger.warning("Bot not connected to MT5")
            return
        
        try:
            # 1. Get current market data and trend
            market = self.mt5.get_market_data(
                self.settings['scan_tf'],
                self.settings['fast_ema'],
                self.settings['slow_ema']
            )
            
            if not market:
                return
            
            # 2. Get current positions
            positions = self.mt5.get_positions()
            is_bull = market.get('trend') == 'BULL'
            is_bear = market.get('trend') == 'BEAR'
            
            # 3. Apply No-Loss Guard
            self.apply_no_loss_guard(positions, market, is_bull, is_bear)
            
            # 4. Manage Grid
            self.manage_grid(positions, market, is_bull, is_bear)
            
        except Exception as e:
            logger.error(f"Error in process_tick: {e}")
    
    def apply_no_loss_guard(self, positions, market, is_bull, is_bear):
        """Apply the no-loss guard logic"""
        for pos in positions:
            # Check if position is losing
            if pos['profit'] < 0:
                # Close if trend has reversed
                if (pos['type'] == 'BUY' and is_bear) or (pos['type'] == 'SELL' and is_bull):
                    logger.info(f"Closing losing position {pos['ticket']} due to trend reversal")
                    self.mt5.close_position(pos['ticket'])
            
            # Lock profit: Close at tiny profit if price returns to entry
            if pos['type'] == 'BUY' and market['bid'] <= pos['price_open'] and pos['profit'] > 0:
                if pos['profit'] < self.settings['break_even_s']:
                    logger.info(f"Closing break-even position {pos['ticket']} with profit {pos['profit']}")
                    self.mt5.close_position(pos['ticket'])
            
            if pos['type'] == 'SELL' and market['ask'] >= pos['price_open'] and pos['profit'] > 0:
                if pos['profit'] < self.settings['break_even_s']:
                    logger.info(f"Closing break-even position {pos['ticket']} with profit {pos['profit']}")
                    self.mt5.close_position(pos['ticket'])
    
    def manage_grid(self, positions, market, is_bull, is_bear):
        """Manage the grid trading strategy"""
        # Separate buy and sell positions
        buy_positions = [p for p in positions if p['type'] == 'BUY']
        sell_positions = [p for p in positions if p['type'] == 'SELL']
        
        # Calculate point value based on symbol
        if 'XAU' in self.settings['symbol'] or 'GOLD' in self.settings['symbol']:
            point = 0.00001  # Gold
        else:
            point = 0.0001   # Forex
            
        gap = self.settings['gap_pips'] * 10 * point
        
        # Open Buy Grid if trend is UP
        if is_bull and len(buy_positions) < self.settings['max_grids']:
            if len(buy_positions) == 0:
                next_price = market['ask']
            else:
                # Find the lowest buy price
                lowest_buy = min(p['price_open'] for p in buy_positions)
                next_price = lowest_buy - gap
            
            # Check if we should place a buy order
            if market['ask'] <= next_price:
                logger.info(f"Placing grid buy at {market['ask']} (next: {next_price})")
                self.mt5.execute_trade(
                    'BUY', 
                    self.settings['lot_size'], 
                    f"Grid Buy - Level {len(buy_positions)+1}"
                )
        
        # Open Sell Grid if trend is DOWN
        if is_bear and len(sell_positions) < self.settings['max_grids']:
            if len(sell_positions) == 0:
                next_price = market['bid']
            else:
                # Find the highest sell price
                highest_sell = max(p['price_open'] for p in sell_positions)
                next_price = highest_sell + gap
            
            # Check if we should place a sell order
            if market['bid'] >= next_price:
                logger.info(f"Placing grid sell at {market['bid']} (next: {next_price})")
                self.mt5.execute_trade(
                    'SELL', 
                    self.settings['lot_size'], 
                    f"Grid Sell - Level {len(sell_positions)+1}"
                )