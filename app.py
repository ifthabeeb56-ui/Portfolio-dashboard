import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import yfinance as yf
from datetime import datetime

# --- 1. പുതിയ ഡാറ്റാബേസ് സെറ്റപ്പ് ---
def get_connection():
    return sqlite3.connect("habeeb_inv.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    # പഴയ ടേബിൾ ഉണ്ടെങ്കിൽ അത് കളഞ്ഞ് പുതിയത് ഉണ്ടാക്കുന്നു
    conn.execute("DROP TABLE IF EXISTS portfolio")
    conn.execute("""
        CREATE TABLE portfolio (
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

# ആപ്പ് ആദ്യമായി റൺ ചെയ്യുമ്പോൾ ഡാറ്റാബേസ് ക്ലീൻ ആക്കുന്നു
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state['db_initialized'] = True

# --- 2. സ്റ്റോക്ക് ലിസ്റ്റ് ലോഡിംഗ് (Nifty 50 & 500) ---
@st.cache_data
def get_stock_list(index_type):
    try:
        if index_type == "Nifty 50":
            url = "https://en.wikipedia.org/wiki/NIFTY_50"
            df = pd.read_html(url)[2]
            return sorted(df['Symbol'].tolist())
        elif index_type == "Nifty 500":
            url = "https://en.wikipedia.org/wiki/List_of_Nifty_500_companies"
            df = pd.read_html(url)[0]
            return sorted(df['Symbol'].tolist())
        else:
            return ["RELIANCE", "TCS", "HDFCBANK", "INFY"]
    except:
        # ഇന്റർനെറ്റ് ഇല്ലെങ്കിൽ മാത്രം കാണിക്കാൻ
        return ["RELIANCE", "TCS", "INFY"]

# --- 3. ലൈവ് പ്രൈസ് ഫെച്ചിംഗ് ---
@st.cache_data(ttl=300)
def fetch_live_price(symbol):
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        return round(ticker.fast_info['lastPrice'], 2)
    except:
        return None

# --- 4. UI കൺഫിഗറേഷൻ ---
st.set_page_config(page_title="Habeeb INV Pro", layout="wide")

# Sidebar Menu
with st.sidebar:
    st.title("HABEEB INV")
    menu = st.radio("Menu", ["📊 Overview", "⚙️ Manage Assets"])

# ഡാറ്റാബേസിൽ നിന്ന് ഡാറ്റ എടുക്കുന്നു
conn = get_connection()
df_portfolio = pd.read_sql_query("SELECT * FROM portfolio", conn)
conn.close()

# --- 5. ഡാഷ്‌ബോർഡ് ഓവർവ്യൂ ---
if menu == "📊 Overview":
    st.title("🚀 Portfolio Dashboard")
    
    if not df_portfolio.empty:
        with st.spinner('Updating Market Prices...'):
            df_portfolio['Live Price'] = df_portfolio['symbol'].apply(fetch_live_price)
            df_portfolio['Live Price'] = df_portfolio['Live Price'].fillna(df_portfolio['avg_price'])
            
        df_portfolio['Invested'] = df_portfolio['qty'] * df_portfolio['avg_price']
        df_portfolio['Current Value'] = df_portfolio['qty'] * df_portfolio['Live Price']
        df_portfolio['PnL'] = df_portfolio['Current Value'] - df_portfolio['Invested']

        # KPI Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Invested", f"₹{df_portfolio['Invested'].sum():,.0f}")
        m2.metric("Market Value", f"₹{df_portfolio['Current Value'].sum():,.0f}")
        total_pnl = df_portfolio['PnL'].sum()
        m3.metric("Total Gain/Loss", f"₹{total_pnl:,.0f}")

        st.markdown("---")
        
        # Charts
        c1, c2 = st.columns(2)
        with c1:
            fig_bar = px.bar(df_portfolio, x='symbol', y='PnL', color='PnL', title="Stock Performance", template="plotly_dark")
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            fig_pie = px.pie(df_portfolio, names='index_name', values='Current Value', title="Portfolio Split", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

        st.subheader("Holdings Details")
        st.dataframe(df_portfolio[['symbol', 'index_name', 'qty', 'avg_price', 'Live Price', 'PnL']], use_container_width=True)
    else:
        st.info("പുതിയ ഡാറ്റാബേസ് തയ്യാറാണ്. 'Manage Assets' ഉപയോഗിച്ച് സ്റ്റോക്കുകൾ ആഡ് ചെയ്യുക.")

# --- 6. അസറ്റ് മാനേജ്‌മെന്റ് (Add/Delete) ---
elif menu == "⚙️ Manage Assets":
    st.title("Asset Management")
    tab1, tab2 = st.tabs(["Add Stock", "Remove Stock"])
    
    with tab1:
        with st.form("add_stock_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            idx_choice = col1.selectbox("Select Index", ["Nifty 50", "Nifty 500"])
            stock_list = get_stock_list(idx_choice)
            symbol_choice = col2.selectbox("Select Stock", stock_list)
            
            qty = col1.number_input("Quantity", min_value=0.1)
            buy_p = col2.number_input("Average Price", min_value=1.0)
            
            if st.form_submit_button("Add Asset"):
                conn = get_connection()
                conn.execute("INSERT INTO portfolio (symbol, index_name, qty, avg_price, date_added) VALUES (?,?,?,?,?)",
                             (symbol_choice, idx_choice, qty, buy_p, datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                conn.close()
                st.success(f"{symbol_choice} added successfully!")
                st.rerun()

    with tab2:
        if not df_portfolio.empty:
            del_stock = st.selectbox("Select Stock to Remove", df_portfolio['symbol'].unique())
            if st.button("Delete Permanently"):
                conn = get_connection()
                conn.execute("DELETE FROM portfolio WHERE symbol = ?", (del_stock,))
                conn.commit()
                conn.close()
                st.rerun()
