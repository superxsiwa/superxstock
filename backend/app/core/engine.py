import pandas as pd
import pandas_ta as ta
from app.data import get_market_data_provider

def fetch_and_analyze(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    Fetch OHLCV data and calculate technical indicators.
    """
    df = get_market_data_provider().fetch_ohlcv(symbol, period=period)
    
    if df.empty:
        return None

    # Remove timezone info for easier handling in database/json
    df.index = df.index.tz_localize(None)

    # Calculate RSI (14)
    df.ta.rsi(length=14, append=True)
    
    # Calculate MACD (12, 26, 9)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    
    # Calculate EMA 50 & 90
    df.ta.ema(length=50, append=True)
    df.ta.ema(length=90, append=True)
    
    # CDC Action Zone Logic (EMA12 & EMA26 crossover)
    df.ta.ema(length=12, append=True)
    df.ta.ema(length=26, append=True)
    
    # Rename for convenience since pandas-ta names them dynamically
    df.rename(columns={
        'RSI_14': 'RSI',
        'EMA_50': 'EMA_50',
        'EMA_90': 'EMA_90',
        'EMA_12': 'EMA_12',
        'EMA_26': 'EMA_26'
    }, inplace=True, errors='ignore')

    # CDC Trend: Bullish when EMA12 > EMA26
    df['CDC_Trend'] = df.apply(lambda row: 'BULL' if row['EMA_12'] > row['EMA_26'] else 'BEAR', axis=1)
    
    # CDC Signal: 
    # BUY  = Trend shifts from BEAR to BULL (Green)
    # SELL = Trend shifts from BULL to BEAR (Red)
    df['Prev_Trend'] = df['CDC_Trend'].shift(1)
    
    def get_signal(row):
        if row['CDC_Trend'] == 'BULL' and row['Prev_Trend'] == 'BEAR':
            return 'BUY'
        elif row['CDC_Trend'] == 'BEAR' and row['Prev_Trend'] == 'BULL':
            return 'SELL'
        return 'HOLD'
        
    df['Signal'] = df.apply(get_signal, axis=1)
    df.drop(columns=['Prev_Trend'], inplace=True)
    
    # Fill any NaN values with 0 to prevent JSON serialization errors
    df.fillna(0, inplace=True)
    
    return df
