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
    # സ്ക്രീൻഷോട്ടിലെ ലേഔട്ട് അനുസരിച്ചുള്ള കോളംസ്
    req_cols = ["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", 
                "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", 
                "Remark", "Status", "Today_PnL", "Sell_Price", "Sell_Date"]
    
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        for col in req_cols:
            if col not in df.columns:
                df[col] = "" if col in ["Sell_Date", "Remark", "Category", "Account", "Status", "Name"] else 0.0
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
                        
                        # Net P&L calculation - Syntax Fix
                        net_pnl = (current_val + row['Dividend']) - (row['Investment'] + row['Tax'])
                        df.at[index, 'P&L'] = round(net_pnl, 2)
                        if row['Investment'] > 0:
                            df.at[index, 'P_Percentage'] = round((net_pnl / row['Investment']) * 100, 2)
                except: continue
        df.to_csv(PORTFOLIO_FILE, index=False)
    except: st.sidebar.error("ലൈവ് പ്രൈസ് അപ്‌ഡേറ്റ് പരാജയപ്പെട്ടു.")
    return df

# --- App Setup ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9", page_icon="📈")
df = load_data()
watch_stocks = get_watchlist()
nifty500_list = get_nifty500_tickers()

# --- SIDEBAR ---
st.sidebar.header("⚙️ Data Management")
if not df.empty:
    st.sidebar.download_button("📥 Portfolio Backup", data=df.to_csv(index=False).encode('utf-8'), file_name="portfolio_backup.csv")

up_p = st.sidebar.file_uploader("Restore Portfolio (CSV)", type="csv")
if up_p and st.sidebar.button("Confirm Restore"):
    pd.read_csv(up_p).to_csv(PORTFOLIO_FILE, index=False)
    st.rerun()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "📜 Sold History", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 1: HEATMAP (ValueError Fix) ---
with tab1:
    hold_stocks_df = df[df['Status'] == "Holding"].copy()
    if not hold_stocks_df.empty:
        st.subheader("Market Visualization Settings")
        box_size_opt = st.radio("Box Size based on:", ["Investment", "Daily % Change"], horizontal=True)
        st.toggle("Include Watchlist in Heatmap") # UI Switch
        
        val_col = 'Investment' if
        
