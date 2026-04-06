import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os

# --- 1. ഫയൽ സെറ്റിംഗ്സ് ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"

def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        # പഴയ ഡാറ്റയുമായി സിങ്ക് ചെയ്യാൻ 0 കൊണ്ട് ഫിൽ ചെയ്യുന്നു
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0.0
        if 'Status' not in df.columns: df['Status'] = 'Holding'
        if 'Name' not in df.columns: return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "Status"])
        return df
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "Status"])

def get_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            return sorted(list(set([line.strip() for line in f.readlines() if line.strip()])))
    return []

# --- 2. ആപ്പ് സെറ്റപ്പ് & FULL BLACK THEME ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9", page_icon="📈")

st.markdown("""
<style>
    .stApp { background-color: #000000; color: #ffffff; }
    div.stTabs [data-baseweb="tab-list"] { background-color: #000000; }
    div.stTabs [data-baseweb="tab"] {
        background-color: #1a1a1a; border: 1px solid #333;
        padding: 10px 25px; border-radius: 5px; color: #ffffff;
    }
    div.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #ff4b4b !important; color: white !important;
    }
    [data-testid="stMetric"] {
        background-color: #1a1a1a; padding: 15px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); border-left: 5px solid #ff4b4b;
    }
    label, p, h1, h2, h3 { color: #ffffff !important; }
    .stDataFrame { background-color: #1a1a1a; }
</style>
""", unsafe_allow_html=True)

df = load_data()
watch_stocks = get_watchlist()

st.title("📊 Habeeb's Power Hub v6.9 (Black Edition)")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "📊 Analytics", "👀 Watchlist", "💾 Backup"])

# --- TAB 1: HEATMAP (NaN പ്രശ്നം ഒഴിവാക്കാൻ) ---
with tab1:
    st.subheader("Market Overview")
    hold_df = df[df['Status'] == "Holding"]
    tickers = hold_df['Name'].tolist()
    if tickers:
        try:
            # സിംബലുകൾ വാലിഡ് ആണെന്ന് ഉറപ്പാക്കുന്നു
            tickers = [s if ".NS" in s or ".BO" in s else s + ".NS" for s in tickers]
            data = yf.download(tickers, period="2d", progress=False)['Close']
            if not data.empty and len(data) > 1:
                changes = ((data.iloc[-1] - data.iloc[-2]) / data.iloc[-2]) * 100
                m_df = pd.DataFrame({"Symbol": changes.index, "Change %": changes.values})
                fig = px.treemap(m_df, path=['Symbol'], values='Change %', color='Change %', 
                                 color_continuous_scale='RdYlGn', range_color=[-3, 3])
                st.plotly_chart(fig, use_container_width=True)
        except: st.error("ലൈവ് ഡാറ്റ കിട്ടാൻ ഇന്റർനെറ്റ് ഉണ്ടെന്ന് ഉറപ്പാക്കുക.")

# --- TAB 2: PORTFOLIO ---
with tab2:
    st.subheader("Current Holdings")
    st.dataframe(df[df['Status'] == 'Holding'], use_container_width=True, hide_index=True)

# --- TAB 4: WATCHLIST ---
with tab5:
    st.subheader("Manage Watchlist")
    w_input = st.text_input("Enter Ticker Name").upper().strip()
    if st.button("Add Ticker"):
        with open(WATCHLIST_FILE, "a") as f: f.write(w_input + "\n")
        st.success(f"{w_input} added!")
        st.rerun()
    st.write("Current List:", watch_stocks)

# --- TAB 5: BACKUP & RESTORE (ഡൗൺലോഡ് & അപ്‌ലോഡ്) ---
with tab5:
    st.subheader("💾 Backup Center")
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("### ⬇️ Download")
        # Portfolio CSV
        st.download_button("Download Portfolio", data=df.to_csv(index=False), file_name="habeeb_portfolio.csv", mime="text/csv")
        # Watchlist TXT
        if watch_stocks:
            st.download_button("Download Watchlist", data="\n".join(watch_stocks), file_name="watchlist.txt", mime="text/plain")

    with c2:
        st.write("### ⬆️ Restore")
        up_csv = st.file_uploader("Upload Portfolio CSV", type="csv")
        if up_csv and st.button("Confirm Portfolio Restore"):
            pd.read_csv(up_csv).to_csv(PORTFOLIO_FILE, index=False)
            st.success("Portfolio Updated!")
            st.rerun()
        
        up_txt = st.file_uploader("Upload Watchlist TXT", type="txt")
        if up_txt and st.button("Confirm Watchlist Restore"):
            with open(WATCHLIST_FILE, "wb") as f: f.write(up_txt.read())
            st.success("Watchlist Updated!")
            st.rerun()
