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
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage", "Dividend", "Tax", "Sell_Price"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Remark", "Status", "Sell_Price"])

@st.cache_data(ttl=86400)
def get_nifty500_tickers():
    try:
        url = "https://raw.githubusercontent.com/anirban-d/nifty-indices-constituents/main/ind_nifty500list.csv"
        n500_df = pd.read_csv(url)
        return sorted(n500_df['Symbol'].tolist())
    except:
        return ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN"]

# --- 2. ആപ്പ് സെറ്റപ്പ് & COLORFUL UI (CSS) ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9", page_icon="📈")

st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    div.stTabs [data-baseweb="tab-list"] { gap: 10px; }
    div.stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border: 1px solid #dee2e6;
        padding: 10px 25px;
        border-radius: 5px;
        color: #263c5c;
        font-weight: bold;
    }
    div.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #263c5c !important;
        color: white !important;
        border: none;
    }
    [data-testid="stMetric"] {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 5px solid #263c5c;
    }
    [data-testid="stMetricValue"] { color: #263c5c; font-size: 24px; }
    h1, h2, h3 { color: #263c5c !important; }
</style>
""", unsafe_allow_html=True)

df = load_data()
nifty500_list = get_nifty500_tickers()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2, tab3 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "📊 Analytics"])

# --- TAB 1: HEATMAP ---
with tab1:
    st.subheader("Market Visualization")
    hold_df = df[df['Status'] == "Holding"].copy()
    if not hold_df.empty:
        try:
            m_data = yf.download(hold_df['Name'].tolist(), period="2d", progress=False)['Close']
            m_changes = ((m_data.iloc[-1] - m_data.iloc[-2]) / m_data.iloc[-2]) * 100
            m_df = pd.DataFrame({"Symbol": m_changes.index, "Change %": m_changes.values}).merge(hold_df[['Name', 'Investment']], left_on='Symbol', right_on='Name')
            fig = px.treemap(m_df, path=['Symbol'], values='Investment', color='Change %', color_continuous_scale='RdYlGn', range_color=[-3, 3])
            st.plotly_chart(fig, use_container_width=True)
        except: st.error("Heatmap loading error.")

# --- TAB 2: PORTFOLIO ---
with tab2:
    hold_df = df[df['Status'] == "Holding"].copy()
    if not hold_df.empty:
        tickers = hold_df['Name'].tolist()
        with st.spinner('Updating Live Prices...'):
            try:
                live_data = yf.download(tickers, period="2d", progress=False)['Close']
                today_pnl_total = 0
                for index, row in hold_df.iterrows():
                    try:
                        curr, prev = live_data[row['Name']].iloc[-1], live_data[row['Name']].iloc[-2]
                        today_pnl_total += (curr - prev) * row['QTY Available']
                        hold_df.at[index, 'CMP'], hold_df.at[index, 'CM Value'] = curr, curr * row['QTY Available']
                        hold_df.at[index, 'P&L'] = (curr * row['QTY Available']) - row['Investment']
                    except: pass
            except: st.warning("Live price update failed. Using last saved data.")

        t_inv, t_val = int(hold_df['Investment'].sum()), int(hold_df['CM Value'].sum())
        t_pnl = t_val - t_inv
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Investment", f"₹{t_inv:,}")
        c2.metric("Current Value", f"₹{t_val:,}")
        c3.metric("Total P&L", f"₹{int(t_pnl):,}", f"{((t_pnl/t_inv)*100):.2f}%" if t_inv > 0 else "0%")
        c4.metric("Today's P&L", f"₹{int(today_pnl_total):,}", f"{((today_pnl_total/t_inv)*100):.2f}%" if t_inv > 0 else "0%")

        # Decimal remove ചെയ്ത ടേബിൾ
        display_df = hold_df[['Category', 'Buy Date', 'Name', 'CMP', 'Buy Price', 'QTY Available', 'Account', 'Investment', 'CM Value', 'P&L']].copy()
        for col in ['CMP', 'Buy Price', 'Investment', 'CM Value', 'P&L']:
            display_df[col] = display_df[col].apply(lambda x: int(round(x)))
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    # --- ADD & SELL SECTION ---
    edit_mode = st.toggle("🛠️ Manage Portfolio (Add/Sell)")
    if edit_mode:
        col_add, col_sell = st.columns(2)
        with col_add:
            st.subheader("➕ Add New Stock")
            with st.form("add_form", clear_on_submit=True):
                f_cat = st.selectbox("Category", ["Stock", "ETF", "Mutual Fund"])
                f_date = st.date_input("Purchase Date", datetime.now())
                f_name = st.selectbox("Stock Name", nifty500_list)
                f_price = st.number_input("Buy Price", min_value=0.0, step=0.1)
                f_qty = st.number_input("Quantity", min_value=1, step=1)
                f_acc = st.selectbox("Account", ["Habeeb", "RISU"])
                if st.form_submit_button("Add to Portfolio"):
                    new_sym = f_name + ".NS"
                    new_row = {
                        "Category": f_cat, "Buy Date": str(f_date), "Name": new_sym, 
                        "Buy Price": f_price, "QTY Available": f_qty, "Account": f_acc, 
                        "Investment": round(f_price * f_qty, 2), "Status": "Holding",
                        "CMP": f_price, "CM Value": round(f_price * f_qty, 2), "P&L": 0,
                        "Dividend": 0, "Tax": 0
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_csv(PORTFOLIO_FILE, index=False)
                    st.success(f"{f_name} added successfully!")
                    st.rerun()

        with col_sell:
            st.subheader("💰 Sell Stock")
            if not hold_df.empty:
                s_stock = st.selectbox("Select to Sell", ["None"] + hold_df['Name'].tolist())
                s_price = st.number_input("Selling Price", value=0.0, step=0.1)
                if st.button("Confirm Sale") and s_stock != "None":
                    df.loc[df['Name'] == s_stock, 'Status'] = 'Sold'
                    df.loc[df['Name'] == s_stock, 'Sell_Price'] = s_price
                    df.to_csv(PORTFOLIO_FILE, index=False)
                    st.success(f"{s_stock} sold successfully!")
                    st.rerun()
            else:
                st.info("No stocks available to sell.")

    # --- SOLD HISTORY ---
    st.divider()
    st.subheader("📜 Sold Stocks History")
    sold_df = df[df['Status'] == "Sold"].copy()
    if not sold_df.empty:
        sold_df['Exit Value'] = (sold_df['Sell_Price'] * sold_df['QTY Available']).apply(int)
        sold_df['Realized P&L'] = (sold_df['Exit Value'] - sold_df['Investment']).apply(int)
        st.dataframe(sold_df[['Name', 'Buy Date', 'Investment', 'Exit Value', 'Realized P&L']], use_container_width=True, hide_index=True)
        st.info(f"Total Realized Profit/Loss: ₹{int(sold_df['Realized P&L'].sum()):,}")

# --- TAB 3: ANALYTICS ---
with tab3:
    st.subheader("📊 Distribution Analysis")
    if not hold_df.empty:
        ana_mode = st.radio("Based on:", ["Investment", "Current Market Value"], horizontal=True)
        val_col = 'Investment' if ana_mode == "Investment" else 'CM Value'
        c_p1, c_p2 = st.columns(2)
        color_map = ['#263c5c', '#ff9f43', '#00d2d3', '#54a0ff']
        with c_p1: 
            st.plotly_chart(px.pie(hold_df, values=val_col, names='Category', hole=0.5, 
                                    title=f"By Category ({ana_mode})", color_discrete_sequence=color_map), use_container_width=True)
        with c_p2: 
            st.plotly_chart(px.pie(hold_df, values=val_col, names='Account', hole=0.5, 
                                    title=f"By Account ({ana_mode})", color_discrete_sequence=color_map), use_container_width=True)
    else:
        st.info("No data available for analysis.")
