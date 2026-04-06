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
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        req_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage", "Dividend", "Tax", "Today_PnL", "Sell_Price", "Sell_Date"]
        for col in req_cols:
            if col not in df.columns:
                df[col] = "" if col == "Sell_Date" else 0.0
            if col not in ["Sell_Date", "Status", "Name", "Account", "Category", "Remark"]:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Remark", "Status", "Today_PnL", "Sell_Price", "Sell_Date"])

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

# --- SIDEBAR: BACKUP & UPLOAD (PORTFOLIO & WATCHLIST) ---
st.sidebar.header("⚙️ Data Management")

# 1. Portfolio Data Section
st.sidebar.subheader("📁 Portfolio & Sold Data")
if not df.empty:
    csv_p = df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button("📥 Backup Portfolio (CSV)", data=csv_p, file_name=f"portfolio_backup_{datetime.now().strftime('%Y%m%d')}.csv", mime='text/csv')

up_p = st.sidebar.file_uploader("Restore Portfolio (CSV)", type="csv")
if up_p is not None:
    if st.sidebar.button("✅ Confirm Portfolio Restore"):
        pd.read_csv(up_p).to_csv(PORTFOLIO_FILE, index=False)
        st.sidebar.success("Portfolio Restored!")
        st.rerun()

st.sidebar.divider()

# 2. Watchlist Data Section
st.sidebar.subheader("🔭 Watchlist Data")
if watch_stocks:
    wl_text = "\n".join(watch_stocks)
    st.sidebar.download_button("📥 Backup Watchlist (TXT)", data=wl_text, file_name="watchlist_backup.txt")

up_w = st.sidebar.file_uploader("Restore Watchlist (TXT)", type="txt")
if up_w is
