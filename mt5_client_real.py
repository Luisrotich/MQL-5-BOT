import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import logging
import time
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class MT5Client:
    def __init__(self, magic_number=888999):
        self.magic = magic_number
        self.connected = False
        self.symbol = None
        self.terminal_path = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
        
    def connect(self, symbol="XAUUSD", terminal_path=None):
        """Connect to MetaTrader 5 terminal"""
        try:
            # Initialize MT5 connection
            if terminal_path:
                # If you have a specific terminal path
                if not mt5.initialize(terminal_path):
                    logger.error(f"MT5 initialization failed with path: {terminal_path}")
                    return False
            else:
                # Default initialization
                if not mt5.initialize():
                    logger.error("MT5 initialization failed")
                    return False
            
            # Check if connected
            if not mt5.terminal_info():
                logger.error("MT5 terminal info not available")
                return False
            
            # Get account info to verify connection
            account_info = mt5.account_info()
            if account_info is None:
                logger.error("No account info - please login to MT5 terminal")
                return False
            
            self.symbol = symbol
            self.connected = True
            
            logger.info(f"Connected to MT5 - Account: {account_info.login}")
            logger.info(f"Balance: {account_info.balance}, Equity: {account_info.equity}")
            
            # Verify symbol exists
            if not mt5.symbol_info(symbol):
                logger.error(f"Symbol {symbol} not found")
                return False
            
            # Enable symbol in Market Watch if needed
            mt5.symbol_select(symbol, True)
            
            return True
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("Disconnected from MT5")
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        if not self.connected:
            logger.warning("Not connected to MT5")
            return []
        
        try:
            positions = mt5.positions_get()
            if positions is None:
                return []
            
            result = []
            for pos in positions:
                # Filter by magic number if set
                if self.magic == 0 or pos.magic == self.magic:
                    result.append({
                        'ticket': pos.ticket,
                        'type': 'BUY' if pos.type == 0 else 'SELL',
                        'volume': pos.volume,
                        'price_open': pos.price_open,
                        'price_current': pos.price_current,
                        'profit': pos.profit,
                        'symbol': pos.symbol,
                        'comment': pos.comment,
                        'magic': pos.magic,
                        'time': pos.time
                    })
            return result
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_account_info(self) -> Dict:
        """Get account information"""
        if not self.connected:
            return {}
        
        try:
            account = mt5.account_info()
            if account:
                return {
                    'login': account.login,
                    'balance': account.balance,
                    'equity': account.equity,
                    'margin': account.margin,
                    'free_margin': account.margin_free,
                    'profit': account.profit,
                    'leverage': account.leverage,
                    'currency': account.currency
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}
    
    def get_market_data(self, tf="H1", fast_ema=13, slow_ema=48) -> Dict:
        """Get market data and trend analysis"""
        if not self.connected:
            return {}
        
        try:
            # Map timeframe strings to MT5 constants
            timeframe_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1,
                "W1": mt5.TIMEFRAME_W1,
                "MN1": mt5.TIMEFRAME_MN1
            }
            
            timeframe = timeframe_map.get(tf, mt5.TIMEFRAME_H1)
            
            # Get current tick
            tick = mt5.symbol_info_tick(self.symbol)
            if not tick:
                return {}
            
            # Get historical data for EMA calculation
            rates = mt5.copy_rates_from_pos(
                self.symbol,
                timeframe,
                0,
                slow_ema + 50
            )
            
            if rates is None or len(rates) < slow_ema:
                return {
                    'symbol': self.symbol,
                    'bid': tick.bid,
                    'ask': tick.ask,
                    'close': tick.bid,
                    'fast_ema': 0,
                    'slow_ema': 0,
                    'trend': 'NEUTRAL',
                    'trend_strength': 0
                }
            
            df = pd.DataFrame(rates)
            
            # Calculate EMAs
            df['fast_ema'] = df['close'].ewm(span=fast_ema, adjust=False).mean()
            df['slow_ema'] = df['close'].ewm(span=slow_ema, adjust=False).mean()
            
            current = df.iloc[-1]
            previous = df.iloc[-2]
            
            # Determine trend
            current_fast = current['fast_ema']
            current_slow = current['slow_ema']
            prev_fast = previous['fast_ema']
            prev_slow = previous['slow_ema']
            
            if current_fast > current_slow:
                trend = 'BULL'
                strength = abs(current_fast - current_slow)
            elif current_fast < current_slow:
                trend = 'BEAR'
                strength = abs(current_fast - current_slow)
            else:
                trend = 'NEUTRAL'
                strength = 0
            
            return {
                'symbol': self.symbol,
                'timestamp': datetime.now().isoformat(),
                'bid': tick.bid,
                'ask': tick.ask,
                'close': tick.bid,
                'fast_ema': current_fast,
                'slow_ema': current_slow,
                'trend': trend,
                'trend_strength': strength,
                'previous_trend': 'BULL' if prev_fast > prev_slow else 'BEAR'
            }
            
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return {}
    
    def execute_trade(self, order_type: str, lot_size: float, comment: str = "", 
                      sl_pips: float = 0, tp_pips: float = 0) -> bool:
        """Execute a trade with optional SL/TP"""
        if not self.connected:
            logger.error("Not connected to MT5")
            return False
        
        try:
            symbol_info = mt5.symbol_info(self.symbol)
            if symbol_info is None:
                logger.error(f"Symbol {self.symbol} not found")
                return False
            
            # Check if trading is allowed
            if not symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                logger.error(f"Trading is not allowed for {self.symbol}")
                return False
            
            point = symbol_info.point
            tick = mt5.symbol_info_tick(self.symbol)
            
            # Calculate SL and TP if specified
            sl = 0
            tp = 0
            
            if sl_pips > 0:
                if order_type == "BUY":
                    sl = tick.ask - (sl_pips * point * 10)
                else:
                    sl = tick.bid + (sl_pips * point * 10)
            
            if tp_pips > 0:
                if order_type == "BUY":
                    tp = tick.ask + (tp_pips * point * 10)
                else:
                    tp = tick.bid - (tp_pips * point * 10)
            
            # Prepare order request
            if order_type == "BUY":
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.symbol,
                    "volume": lot_size,
                    "type": mt5.ORDER_TYPE_BUY,
                    "price": tick.ask,
                    "deviation": 20,
                    "magic": self.magic,
                    "comment": comment,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                
                if sl > 0:
                    request["sl"] = sl
                if tp > 0:
                    request["tp"] = tp
                    
            elif order_type == "SELL":
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.symbol,
                    "volume": lot_size,
                    "type": mt5.ORDER_TYPE_SELL,
                    "price": tick.bid,
                    "deviation": 20,
                    "magic": self.magic,
                    "comment": comment,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                
                if sl > 0:
                    request["sl"] = sl
                if tp > 0:
                    request["tp"] = tp
            else:
                return False
            
            # Send order
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Trade failed: {result.comment}, retcode: {result.retcode}")
                return False
            
            logger.info(f"Trade executed: {order_type} {lot_size} at {request['price']}")
            logger.info(f"Order result: {result}")
            return True
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return False
    
    def close_position(self, ticket: int) -> bool:
        """Close a specific position"""
        if not self.connected:
            return False
        
        try:
            position = mt5.positions_get(ticket=ticket)
            if not position or len(position) == 0:
                logger.error(f"Position {ticket} not found")
                return False
            
            pos = position[0]
            tick = mt5.symbol_info_tick(pos.symbol)
            
            if pos.type == 0:  # BUY
                price = tick.bid
                order_type = mt5.ORDER_TYPE_SELL
            else:  # SELL
                price = tick.ask
                order_type = mt5.ORDER_TYPE_BUY
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": self.magic,
                "comment": "Close position",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Close failed: {result.comment}")
                return False
            
            logger.info(f"Position {ticket} closed")
            return True
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False
    
    def close_all_positions(self) -> bool:
        """Close all positions"""
        positions = self.get_positions()
        success = True
        
        for pos in positions:
            if not self.close_position(pos['ticket']):
                success = False
                logger.error(f"Failed to close position {pos['ticket']}")
        
        return success
    
    def get_settings(self) -> Dict:
        """Get current bot settings"""
        return {
            'magic': self.magic,
            'symbol': self.symbol,
            'connected': self.connected
        }
    
    def update_settings(self, **kwargs) -> bool:
        """Update bot settings"""
        if 'magic' in kwargs:
            self.magic = kwargs['magic']
        if 'symbol' in kwargs:
            self.symbol = kwargs['symbol']
        return True