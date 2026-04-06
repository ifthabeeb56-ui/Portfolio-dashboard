import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os
import zipfile
import io

# --- 1. ഫയൽ സെറ്റിംഗ്സ് ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"
HISTORY_FILE = "portfolio_history.csv"

# --- ഫംഗ്ഷനുകൾ (മാറ്റമില്ലാതെ) ---
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
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage", "Dividend", "Tax"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame()

def get_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

# --- ആപ്പ് സെറ്റപ്പ് ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.8", page_icon="📈")
df = load_data()
watch_data_list = get_watchlist()
nifty500_list = get_nifty500_tickers()

# --- 💾 സൈഡ്‌ബാർ: Combined Backup (ZIP) ---
with st.sidebar:
    st.header("📦 Smart Backup Hub")
    st.write("Portfolio + Watchlist")
    
    if os.path.exists(PORTFOLIO_FILE) or os.path.exists(WATCHLIST_FILE):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as x_zip:
            if os.path.exists(PORTFOLIO_FILE): x_zip.write(PORTFOLIO_FILE)
            if os.path.exists(WATCHLIST_FILE): x_zip.write(WATCHLIST_FILE)
        
        st.download_button(
            label="📥 Download All-in-One ZIP",
            data=buf.getvalue(),
            file_name=f"habeeb_backup_{datetime.now().strftime('%Y%m%d')}.zip",
            mime="application/zip",
            use_container_width=True
        )
    
    st.divider()
    st.subheader("📤 Restore Data")
    uploaded_zip = st.file_uploader("Upload Backup ZIP", type=["zip"])
    if uploaded_zip:
        if st.button("🚀 Start Full Restore", use_container_width=True):
            with zipfile.ZipFile(uploaded_zip, 'r') as z:
                z.extractall()
            st.success("വിജയകരമായി റീസ്റ്റോർ ചെയ്തു!"); st.rerun()

st.title("📊 Habeeb's Power Hub v6.8")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 5: WATCHLIST (ഇവിടെയായിരുന്നു പിശക്, ഇപ്പോൾ തിരുത്തിയിട്ടുണ്ട്) ---
with tab5:
    st.subheader("👀 Professional Watchlist")
    c_w1, c_w2 = st.columns([3, 1])
    with c_w1:
        w_in = st.text_input("Enter Ticker", key="watch_in").upper().strip()
    with c_w2:
        st.write("##")
        if st.button("➕ Add", use_container_width=True) and w_in:
            ticker = w_in + ".NS" if not w_in.endswith(".NS") else w_in # തിരുത്തിയ ഭാഗം
            date_now = datetime.now().strftime("%d-%m-%Y")
            with open(WATCHLIST_FILE, "a") as f: 
                f.write(f"{ticker},{date_now}\n")
            st.rerun()

    if watch_data_list:
        lines = [l.split(',') for l in watch_data_list]
        valid_tickers = [l[0] for l in lines if len(l[0]) > 3]
        
        try:
            with st.spinner("Updating Watchlist Prices..."):
                w_live = yf.download(valid_tickers, period="2d", progress=False)['Close']
                
            cols = st.columns(3)
            for i, entry in enumerate(lines):
                ticker = entry[0]
                added_on = entry[1] if len(entry) > 1 else "N/A"
                with cols[i % 3]:
                    try:
                        if len(valid_tickers) == 1:
                            cp, pp = float(w_live.iloc[-1]), float(w_live.iloc[-2])
                        else:
                            cp, pp = float(w_live[ticker].iloc[-1]), float(w_live[ticker].iloc[-2])
                        
                        change = ((cp - pp) / pp) * 100
                        with st.container(border=True):
                            st.markdown(f"### {ticker.replace('.NS', '')}")
                            st.caption(f"📅 Added: {added_on}")
                            st.metric("Price", f"₹{cp:,.2f}", f"{change:+.2f}%")
                    except:
                        st.error(f"Error: {ticker}")
        except:
            st.warning("Live data update failed.")
            
        if st.button("🗑️ Clear Watchlist"):
            if os.path.exists(WATCHLIST_FILE):
                os.remove(WATCHLIST_FILE)
                st.rerun()
    
