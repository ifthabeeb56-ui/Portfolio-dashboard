import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import yfinance as yf
from datetime import datetime

# --- DATABASE SETUP ---
def get_connection():
    return sqlite3.connect("habeeb_inv.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    # index_type എന്ന കോളം ഉണ്ടെന്ന് ഉറപ്പുവരുത്തുന്നു
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            index_type TEXT,
            quantity REAL,
            buy_price REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- INDEX STOCK LISTS ---
STOCKS_DICT = {
    "Nifty 50": ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK"],
    "Nifty Bank": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "INDUSINDBK", "PNB", "FEDERALBNK"],
    "Nifty IT": ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "LTIM", "PERSISTENT", "COFORGE"],
    "Nifty 500": ["RELIANCE", "TCS", "ZOMATO", "PAYTM", "ADANIENT", "TATAMOTORS", "MRF", "NYKAA", "SUZLON", "IRFC"]
}

# --- LIVE PRICE FETCHING (With Cache) ---
@st.cache_data(ttl=600) # 10 മിനിറ്റ് ഡാറ്റ സേവ് ചെയ്തു വെക്കും (വേഗത കൂട്ടാൻ)
def get_live_price(symbol):
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        price = ticker.fast_info['lastPrice']
        return round(price, 2)
    except:
        return None

# --- PAGE CONFIG ---
st.set_page_config(page_title="Habeeb's Pro Dashboard", layout="wide")

# Dark CSS
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    div[data-testid="stMetric"] {
        background-color: #161B22; border-radius: 12px; padding: 15px; border: 1px solid #30363D;
    }
    .stButton>button { background-color: #238636; color: white; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA LOADING ---
conn = get_connection()
df_portfolio = pd.read_sql_query("SELECT * FROM portfolio", conn)
conn.close()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color: #58A6FF; text-align: center;'>HABEEB INV</h1>", unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio("Menu", ["📊 Dashboard", "⚙️ Manage Stocks"])

if page == "📊 Dashboard":
    st.title("🚀 Multi-Index Portfolio")
    
    if not df_portfolio.empty:
        with st.spinner('Updating market prices...'):
            df_portfolio['current_price'] = df_portfolio['name'].apply(get_live_price)
            df_portfolio['current_price'] = df_portfolio['current_price'].fillna(df_portfolio['buy_price'])

        df_portfolio['Invested'] = df_portfolio['quantity'] * df_portfolio['buy_price']
        df_portfolio['Value'] = df_portfolio['quantity'] * df_portfolio['current_price']
        df_portfolio['PnL'] = df_portfolio['Value'] - df_portfolio['Invested']
        
        # Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Invested", f"₹{df_portfolio['Invested'].sum():,.0f}")
        m2.metric("Current Value", f"₹{df_portfolio['Value'].sum():,.0f}")
        profit = df_portfolio['PnL'].sum()
        inv_sum = df_portfolio['Invested'].sum()
        p_pct = (profit/inv_sum*100) if inv_sum > 0 else 0
        m3.metric("Total P&L", f"₹{profit:,.0f}", f"{p_pct:.2f}%")
        m4.metric("Stocks Count", len(df_portfolio))

        st.markdown("---")
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("📈 Performance by Index")
            idx_pnl = df_portfolio.groupby('index_type')['PnL'].sum().reset_index()
            fig = px.bar(idx_pnl, x='index_type', y='PnL', color='index_type', template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        
        with c2:
            st.subheader("Index Allocation")
            fig_pie = px.pie(df_portfolio, names='index_type', values='Value', hole=0.5, template="plotly_dark")
            st.plotly_chart(fig_pie, use_container_width=True)

        st.subheader("📋 Detailed Holdings")
        st.dataframe(df_portfolio[['name', 'index_type', 'quantity', 'buy_price', 'current_price', 'PnL']], use_container_width=True)
    else:
        st.info("No stocks added yet.")

elif page == "⚙️ Manage Stocks":
    st.title("Portfolio Settings")
    t1, t2 = st.tabs(["➕ Add Stock", "🗑️ Remove Stock"])
    
    with t1:
        with st.form("add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            idx = col1.selectbox("Select Index", list(STOCKS_DICT.keys()))
            name = col2.selectbox("Select Stock", STOCKS_DICT[idx])
            qty = col1.number_input("Quantity", min_value=0.1)
            buy_p = col2.number_input("Avg. Buy Price", min_value=0.1)
            
            if st.form_submit_button("Add Stock"):
                conn = get_connection()
                conn.execute("INSERT INTO portfolio (name, index_type, quantity, buy_price) VALUES (?,?,?,?)",
                             (name, idx, qty, buy_p))
                conn.commit()
                conn.close()
                st.success(f"{name} added!")
                st.rerun()

    with t2:
        if not df_portfolio.empty:
            to_del = st.selectbox("Select stock to remove", df_portfolio['name'].tolist())
            if st.button("Delete Asset"):
                conn = get_connection()
                conn.execute("DELETE FROM portfolio WHERE name = ?", (to_del,))
                conn.commit()
                conn.close()
                st.rerun()
