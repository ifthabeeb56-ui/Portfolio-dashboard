import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os
import time
from GoogleNews import GoogleNews
from deep_translator import GoogleTranslator

# --- 1. ഫയൽ സെറ്റിംഗ്സ് ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"

@st.cache_data(ttl=86400)
def get_nifty500_tickers():
    try:
        url = "https://raw.githubusercontent.com/anirban-d/nifty-indices-constituents/main/ind_nifty500list.csv"
        n500_df = pd.read_csv(url)
        return sorted(n500_df['Symbol'].tolist())
    except:
        return ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN"]

def load_data():
    req_cols = ["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", 
                "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", 
                "Remark", "Status", "Today_PnL", "Sell_Price", "Sell_Date"]
    
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        # ഇല്ലാത്ത കോളംസ് ഉണ്ടെങ്കിൽ ആഡ് ചെയ്യുന്നു
        for col in req_cols:
            if col not in df.columns:
                df[col] = "" if col in ["Sell_Date", "Remark", "Category", "Account", "Status", "Name"] else 0.0
            
            # കണക്കുകൂട്ടലുകൾക്ക് ആവശ്യമായ കോളംസ് നമ്പറുകളാണെന്ന് ഉറപ്പുവരുത്തുന്നു
            if col not in ["Sell_Date", "Status", "Name", "Account", "Category", "Remark", "Buy Date"]:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=req_cols)

def get_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            return sorted(list(set([line.strip() for line in f.readlines() if line.strip()])))
    return []

def update_live_prices(df):
    tickers = df[df['Status'] == "Holding"]['Name'].unique().tolist()
    if not tickers: return df
    try:
        live_data = yf.download(tickers, period="5d", progress=False)['Close']
        if live_data.empty: return df
        
        for index, row in df.iterrows():
            if row['Status'] == "Holding":
                t_name = row['Name']
                try:
                    stock_series = live_data[t_name].dropna() if len(tickers) > 1 else live_data.dropna()
                    if len(stock_series) >= 2:
                        new_p = float(stock_series.iloc[-1])
                        prev_p = float(stock_series.iloc[-2])
                        df.at[index, 'CMP'] = round(new_p, 2)
                        current_val = round(row['QTY Available'] * new_p, 2)
                        df.at[index, 'CM Value'] = current_val
                        df.at[index, 'Today_PnL'] = round((new_p - prev_p) * row['QTY Available'], 2)
                        
                        # Net P&L calculation
                        net_pnl = (current
        
