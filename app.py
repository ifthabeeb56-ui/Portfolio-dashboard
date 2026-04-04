import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime

# --- DATABASE SETUP ---
def get_connection():
    return sqlite3.connect("habeeb_inv.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            quantity INTEGER,
            buy_price REAL,
            current_price REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- PAGE CONFIG ---
st.set_page_config(page_title="Habeeb's Power Dashboard", layout="wide")

# UI മെച്ചപ്പെടുത്താനുള്ള CSS (ഫോട്ടോയിലെ അതേ ലുക്കിന് വേണ്ടി)
st.markdown("""
    <style>
    .stApp { background-color: #F4F7F9; }
    div[data-testid="stMetric"] {
        background-color: white;
        border-radius: 15px;
        padding: 20px;
        border-left: 5px solid #1E3A8A;
        box-shadow: 0px 5px 15px rgba(0,0,0,0.05);
    }
    [data-testid="stSidebar"] { background-color: #1A3A5F; }
    .stButton>button { 
        background-color: #1E3A8A; 
        color: white; 
        border-radius: 10px; 
        height: 3em;
        font-weight: bold;
    }
    .stDataFrame { background-color: white; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA FETCHING ---
def load_data():
    conn = get_connection()
    data = pd.read_sql_query("SELECT * FROM portfolio", conn)
    conn.close()
    return data

df = load_data()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h1 style='color: white; text-align: center;'>HABEEB INV</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #BDC3C7; text-align: center;'>Investor Dashboard</p>", unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio("Menu", ["🏠 Dashboard", "⚙️ Manage Portfolio"])
    st.markdown("---")
    if not df.empty:
        st.success(f"Tracking {len(df)} Assets")

# --- MAIN PAGES ---
if page == "🏠 Dashboard":
    st.markdown(f"### Welcome Back, User")
    st.caption(f"Last updated: {datetime.now().strftime('%d %B %Y')}")
    
    if not df.empty:
        # Calculations
        df['Invested'] = df['quantity'] * df['buy_price']
        df['Current_Val'] = df['quantity'] * df['current_price']
        df['PnL'] = df['Current_Val'] - df['Invested']
        
        t_inv = df['Invested'].sum()
        t_cur = df['Current_Val'].sum()
        t_pnl = df['PnL'].sum()
        pnl_p = (t_pnl / t_inv * 100) if t_inv > 0 else 0

        # KPI Metrics - ആദ്യ ഫോട്ടോയിലെ പോലെ 4 കാർഡുകൾ
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Invested", f"₹{t_inv:,.0f}")
        m2.metric("Current Value", f"₹{t_cur:,.0f}")
        m3.metric("Net Profit", f"₹{t_pnl:,.0f}", f"{pnl_p:.2f}%")
        m4.metric("Assets", f"{len(df)}")

        st.markdown("---")

        # Visuals - ചാർട്ടുകൾ
        col_main, col_side = st.columns([2, 1])
        
        with col_main:
            st.subheader("📈 Performance Trend")
            # മനോഹരമായ ഒരു Area Chart (ഫോട്ടോയിലുള്ളത് പോലെ)
            fig_area = px.area(df, x='name', y='Current_Val', 
                              color_discrete_sequence=['#1E3A8A'],
                              template="simple_white", title="Value Distribution")
            st.plotly_chart(fig_area, use_container_width=True)

        with col_side:
            st.subheader("Sector Split")
            fig_pie = px.pie(df, names='category', values='Invested', 
                            hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)

        # Detailed Table
        st.subheader("📋 Portfolio Holdings")
        st.dataframe(df[['name', 'category', 'quantity', 'buy_price', 'current_price', 'PnL']], use_container_width=True)
    else:
        st.info("നിങ്ങളുടെ പോർട്ട്‌ഫോളിയോയിൽ സ്റ്റോക്കുകൾ ഒന്നുമില്ല. 'Manage Portfolio' ക്ലിക്ക് ചെയ്ത് തുടങ്ങുക.")

elif page == "⚙️ Manage Portfolio":
    st.title("Settings & Management")
    
    t1, t2 = st.tabs(["➕ Add New Stock", "🗑️ Remove Stock"])
    
    with t1:
        with st.form("add_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Stock/ETF Symbol (e.g. RELIANCE)").upper()
            cat = c2.selectbox("Asset Class", ["Equity", "ETF", "SGB", "Gold", "Debt"])
            qty = c1.number_input("Total Quantity", min_value=1)
            price = c2.number_input("Average Buy Price", min_value=0.0)
            
            if st.form_submit_button("Add to Portfolio"):
                if name:
                    conn = get_connection()
                    conn.execute("INSERT INTO portfolio (name, category, quantity, buy_price, current_price) VALUES (?,?,?,?,?)",
                                 (name, cat, qty, price, price))
                    conn.commit()
                    conn.close()
                    st.success(f"{name} added successfully!")
                    st.rerun()

    with t2:
        if not df.empty:
            to_del = st.selectbox("Select Asset to Remove", df['name'].tolist())
            if st.button("Delete Asset", type="primary"):
                conn = get_connection()
                conn.execute("DELETE FROM portfolio WHERE name = ?", (to_del,))
                conn.commit()
                conn.close()
                st.warning(f"{to_del} removed from portfolio.")
                st.rerun()
