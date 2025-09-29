from flask import Flask, render_template, request, jsonify
import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import numpy as np


load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', 'your_api_key_here')
BASE_URL = 'https://www.alphavantage.co/query'

def get_stock_data(symbol, function='TIME_SERIES_DAILY'):
    """
    Fetch stock data from Alpha Vantage API
    """
    params = {
        'function': function,
        'symbol': symbol,
        'apikey': API_KEY,
        'outputsize': 'compact'
    }
    
    try:
        response = requests.get(BASE_URL, params=params)
        data = response.json()
        
        if 'Error Message' in data:
            return None, "Invalid stock symbol"
        
        if 'Note' in data:
            return None, "API call frequency limit reached. Please try again later."
        
        return data, None
    except Exception as e:
        return None, f"Error fetching data: {str(e)}"

def calculate_sma(prices, window):
    """Calculate Simple Moving Average"""
    if len(prices) < window:
        return [None] * len(prices)
    
    sma = []
    for i in range(len(prices)):
        if i < window - 1:
            sma.append(None)
        else:
            sma.append(sum(prices[i-window+1:i+1]) / window)
    return sma

def calculate_ema(prices, window):
    """Calculate Exponential Moving Average"""
    if len(prices) < window:
        return [None] * len(prices)
    
    ema = [None] * (window - 1)
    multiplier = 2 / (window + 1)
    ema.append(sum(prices[:window]) / window)  # First EMA is SMA
    
    for i in range(window, len(prices)):
        ema.append((prices[i] * multiplier) + (ema[-1] * (1 - multiplier)))
    
    return ema

def calculate_rsi(prices, window=14):
    """Calculate Relative Strength Index"""
    if len(prices) < window + 1:
        return [None] * len(prices)
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [delta if delta > 0 else 0 for delta in deltas]
    losses = [-delta if delta < 0 else 0 for delta in deltas]
    
    avg_gain = sum(gains[:window]) / window
    avg_loss = sum(losses[:window]) / window
    
    rsi = [None] * window
    
    for i in range(window, len(gains)):
        avg_gain = ((avg_gain * (window - 1)) + gains[i]) / window
        avg_loss = ((avg_loss * (window - 1)) + losses[i]) / window
        
        if avg_loss == 0:
            rsi.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100 - (100 / (1 + rs)))
    
    return [None] + rsi  # Add None for first price (no delta)

def calculate_bollinger_bands(prices, window=20, num_std=2):
    """Calculate Bollinger Bands"""
    if len(prices) < window:
        return [None] * len(prices), [None] * len(prices), [None] * len(prices)
    
    sma = calculate_sma(prices, window)
    upper_band = []
    lower_band = []
    
    for i in range(len(prices)):
        if i < window - 1:
            upper_band.append(None)
            lower_band.append(None)
        else:
            std_dev = np.std(prices[i-window+1:i+1])
            upper_band.append(sma[i] + (num_std * std_dev))
            lower_band.append(sma[i] - (num_std * std_dev))
    
    return upper_band, sma, lower_band

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD (Moving Average Convergence Divergence)"""
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    
    macd_line = []
    for i in range(len(prices)):
        if ema_fast[i] is None or ema_slow[i] is None:
            macd_line.append(None)
        else:
            macd_line.append(ema_fast[i] - ema_slow[i])
    
    # Calculate signal line (EMA of MACD)
    macd_values = [x for x in macd_line if x is not None]
    if len(macd_values) >= signal:
        signal_line = [None] * (len(macd_line) - len(macd_values))
        signal_ema = calculate_ema(macd_values, signal)
        signal_line.extend(signal_ema)
    else:
        signal_line = [None] * len(macd_line)
    
    # Calculate histogram
    histogram = []
    for i in range(len(macd_line)):
        if macd_line[i] is None or signal_line[i] is None:
            histogram.append(None)
        else:
            histogram.append(macd_line[i] - signal_line[i])
    
    return macd_line, signal_line, histogram

def process_stock_data(data):
    """
    Process raw stock data for visualization with technical indicators
    """
    if 'Time Series (Daily)' in data:
        time_series = data['Time Series (Daily)']
        
        dates = []
        prices = []
        volumes = []
        highs = []
        lows = []
        opens = []
        
        # Get the last 60 days of data for better indicator calculation
        sorted_dates = sorted(time_series.keys(), reverse=True)[:60]
        sorted_dates.reverse()  # Reverse to get chronological order
        
        for date in sorted_dates:
            dates.append(date)
            prices.append(float(time_series[date]['4. close']))
            volumes.append(int(time_series[date]['5. volume']))
            highs.append(float(time_series[date]['2. high']))
            lows.append(float(time_series[date]['3. low']))
            opens.append(float(time_series[date]['1. open']))
        
        # Calculate technical indicators
        sma_20 = calculate_sma(prices, 20)
        sma_50 = calculate_sma(prices, 50)
        ema_12 = calculate_ema(prices, 12)
        ema_26 = calculate_ema(prices, 26)
        rsi = calculate_rsi(prices, 14)
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(prices, 20, 2)
        macd_line, macd_signal, macd_histogram = calculate_macd(prices, 12, 26, 9)
        
        # Return last 30 days for display
        display_length = min(30, len(dates))
        start_index = len(dates) - display_length
        
        return {
            'dates': dates[start_index:],
            'prices': prices[start_index:],
            'volumes': volumes[start_index:],
            'highs': highs[start_index:],
            'lows': lows[start_index:],
            'opens': opens[start_index:],
            'indicators': {
                'sma_20': sma_20[start_index:],
                'sma_50': sma_50[start_index:],
                'ema_12': ema_12[start_index:],
                'ema_26': ema_26[start_index:],
                'rsi': rsi[start_index:],
                'bollinger_upper': bb_upper[start_index:],
                'bollinger_middle': bb_middle[start_index:],
                'bollinger_lower': bb_lower[start_index:],
                'macd_line': macd_line[start_index:],
                'macd_signal': macd_signal[start_index:],
                'macd_histogram': macd_histogram[start_index:]
            },
            'symbol': data['Meta Data']['2. Symbol'],
            'last_refreshed': data['Meta Data']['3. Last Refreshed']
        }
    
    return None

def get_company_info(symbol):
    """
    Get company overview information
    """
    params = {
        'function': 'OVERVIEW',
        'symbol': symbol,
        'apikey': API_KEY
    }
    
    try:
        response = requests.get(BASE_URL, params=params)
        data = response.json()
        
        if 'Symbol' in data:
            return {
                'name': data.get('Name', 'N/A'),
                'sector': data.get('Sector', 'N/A'),
                'industry': data.get('Industry', 'N/A'),
                'market_cap': data.get('MarketCapitalization', 'N/A'),
                'pe_ratio': data.get('PERatio', 'N/A'),
                'dividend_yield': data.get('DividendYield', 'N/A')
            }
    except Exception as e:
        print(f"Error fetching company info: {e}")
    
    return None

@app.route('/')
def index():
    """
    Home page
    """
    return render_template('index.html')

@app.route('/api/stock/<symbol>')
def get_stock(symbol):
    """
    API endpoint to get stock data
    """
    # Get daily stock data
    stock_data, error = get_stock_data(symbol.upper())
    
    if error:
        return jsonify({'error': error}), 400
    
    processed_data = process_stock_data(stock_data)
    
    if not processed_data:
        return jsonify({'error': 'Failed to process stock data'}), 400
    
    # Get company information
    company_info = get_company_info(symbol.upper())
    
    response_data = {
        'stock_data': processed_data,
        'company_info': company_info
    }
    
    return jsonify(response_data)

@app.route('/stock/<symbol>')
def stock_detail(symbol):
    """
    Stock detail page
    """
    return render_template('stock.html', symbol=symbol.upper())

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)