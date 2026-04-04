import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import yfinance as yf
from datetime import datetime

# --- 1. DATABASE SETUP ---
def get_connection():
    return sqlite3.connect("habeeb_inv.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            index_name TEXT,
            qty REAL,
            avg_price REAL,
            date_added TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- 2. DYNAMIC STOCK LIST FETCHING ---
@st.cache_data
def get_index_stocks(index_name):
    try:
        if index_name == "Nifty 50":
            url = "https://en.wikipedia.org/wiki/NIFTY_50"
            df = pd.read_html(url)[2] # വിക്കിപീഡിയയിലെ മൂന്നാമത്തെ ടേബിൾ
            return sorted(df['Symbol'].tolist())
        
        elif index_name == "Nifty 500":
            # Nifty 500 ലിസ്റ്റ് വിക്കിപീഡിയയിൽ നിന്നോ എൻഎസ്ഇയിൽ നിന്നോ എടുക്കാം
            url = "https://en.wikipedia.org/wiki/List_of_Nifty_500_companies"
            df = pd.read_html(url)[0]
            return sorted(df['Symbol'].tolist())
            
        elif index_name == "Nifty Bank":
            return sorted(["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "INDUSINDBK", "AUBL", "IDFCFIRSTB", "FEDERALBNK", "BANDHANBNK", "BANKBARODA", "PNB"])
            
        elif index_name == "Nifty IT":
            return sorted(["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "LTIM", "PERSISTENT", "COFORGE", "MPHASIS", "LTTS"])
    except Exception:
        # ഇന്റർനെറ്റ് പ്രശ്നമുണ്ടെങ്കിൽ കാണിക്കാൻ ഒരു ബാക്കപ്പ് ലിസ്റ്റ്
        return ["RELIANCE", "TCS", "HDFCBANK", "INFY"]

# --- 3. LIVE PRICE FETCHING ---
@st.cache_data(ttl=300)
def fetch_live_price(symbol):
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        price = ticker.fast_info['lastPrice']
        return round(price, 2)
    except:
        return None

# --- 4. UI CONFIG ---
st.set_page_config(page_title="Habeeb INV Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    div[data-testid="stMetric"] {
        background-color: #161B22; border-radius: 12px; padding: 20px; border: 1px solid #30363D;
    }
    .stSidebar { background-color: #0D1117; border-right: 1px solid #30363D; }
    .stButton>button { background-color: #238636; color: white; border-radius: 8px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. DATA LOADING ---
conn = get_connection()
df_portfolio = pd.read_sql_query("SELECT * FROM portfolio", conn)
conn.close()

# --- 6. SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color: #58A6FF; text-align: center;'>HABEEB INV</h2>", unsafe_allow_html=True)
    st.markdown("---")
    menu = st.radio("Menu", ["📊 Overview", "⚙️ Manage Assets"])

# --- 7. DASHBOARD PAGE ---
if menu == "📊 Overview":
    st.title("🚀 Portfolio Analytics")
    
    if not df_portfolio.empty:
        with st.spinner('Updating Market Prices...'):
            df_portfolio['Live Price'] = df_portfolio['symbol'].apply(fetch_live_price)
            df_portfolio['Live Price'] = df_portfolio['Live Price'].fillna(df_portfolio['avg_price'])
            
        df_portfolio['Invested'] = df_portfolio['qty'] * df_portfolio['avg_price']
        df_portfolio['Value'] = df_portfolio['qty'] * df_portfolio['Live Price']
        df_portfolio['PnL'] = df_portfolio['Value'] - df_portfolio['Invested']

        # Metrics
        m1, m2, m3, m4 = st.columns(4)
        total_inv = df_portfolio['Invested'].sum()
        total_val = df_portfolio['Value'].sum()
        total_pnl = df_portfolio['PnL'].sum()
        p_pct = (total_pnl / total_inv * 100) if total_inv > 0 else 0
        
        m1.metric("Total Invested", f"₹{total_inv:,.0f}")
        m2.metric("Market Value", f"₹{total_val:,.0f}")
        m3.metric("Net Profit/Loss", f"₹{total_pnl:,.0f}", f"{pnl_pct:.2f}%")
        m4.metric("Assets", len(df_portfolio))

        st.markdown("---")

        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Performance")
            fig_bar = px.bar(df_portfolio, x='symbol', y='PnL', color='PnL', 
                             color_continuous_scale='RdYlGn', color_continuous_midpoint=0, template="plotly_dark")
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col2:
            st.subheader("Allocation")
            fig_pie = px.pie(df_portfolio, names='index_name', values='Value', hole=0.5, template="plotly_dark")
            st.plotly_chart(fig_pie, use_container_width=True)

        st.subheader("📋 Your Holdings")
        st.dataframe(df_portfolio[['symbol', 'index_name', 'qty', 'avg_price', 'Live Price', 'PnL']], use_container_width=True)
    else:
        st.info("നിങ്ങളുടെ പോർട്ട്‌ഫോളിയോ കാലിയാണ്.")

# --- 8. MANAGE ASSETS ---
elif menu == "⚙️ Manage Assets":
    st.title("Asset Management")
    tab1, tab2 = st.tabs(["➕ Add Position", "🗑️ Close Position"])
    
    with tab1:
        with st.form("add_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            # ആദ്യം ഇൻഡക്സ് തിരഞ്ഞെടുക്കുക
            sel_idx = c1.selectbox("Select Index", ["Nifty 50", "Nifty Bank", "Nifty IT", "Nifty 500"])
            
            # തിരഞ്ഞെടുക്കുന്ന ഇൻഡക്സിന് അനുസരിച്ച് സ്റ്റോക്ക് ലിസ്റ്റ് വരുന്നു
            stock_list = get_index_stocks(sel_idx)
            sel_sym = c2.selectbox("Select Stock Symbol", stock_list)
            
            qty = c1.number_input("Quantity", min_value=0.1)
            avg_p = c2.number_input("Average Buy Price", min_value=1.0)
            
            if st.form_submit_button("Save to Portfolio"):
                conn = get_connection()
                conn.execute("INSERT INTO portfolio (symbol, index_name, qty, avg_price, date_added) VALUES (?,?,?,?,?)",
                             (sel_sym, sel_idx, qty, avg_p, datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                conn.close()
                st.success(f"{sel_sym} added to {sel_idx}!")
                st.rerun()

    with tab2:
        if not df_portfolio.empty:
            to_del = st.selectbox("Select Stock to Remove", df_portfolio['symbol'].unique())
            if st.button("Delete Asset"):
                conn = get_connection()
                conn.execute("DELETE FROM portfolio WHERE symbol = ?", (to_del,))
                conn.commit()
                conn.close()
                st.rerun()
