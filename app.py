import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os

# --- 1. ഫയൽ സെറ്റിംഗ്സ് ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"
HISTORY_FILE = "portfolio_history.csv"

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
        req_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage", "Dividend", "Tax", "Today_PnL"]
        for col in req_cols:
            if col not in df.columns: df[col] = 0.0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Remark", "Status", "Today_PnL"])

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
                        
                        net_pnl = (current_val + row['Dividend']) - row['Investment']
                        df.at[index, 'P&L'] = round(net_pnl, 2)
                        if row['Investment'] > 0:
                            df.at[index, 'P_Percentage'] = round((net_pnl / row['Investment']) * 100, 2)
                        else:
                            df.at[index, 'P_Percentage'] = 0.0
                except: continue
        df.to_csv(PORTFOLIO_FILE, index=False)
    except: st.sidebar.error("ലൈവ് പ്രൈസ് അപ്‌ഡേറ്റ് പരാജയപ്പെട്ടു.")
    return df

# --- App Setup ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9", page_icon="📈")
df = load_data()
nifty500_list = get_nifty500_tickers()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2, tab3 = st.tabs(["💼 Portfolio", "🔍 Heatmap", "⚙️ Settings"])

# --- TAB 1: PORTFOLIO ---
with tab1:
    if not df.empty:
        df = update_live_prices(df)
        hold_df = df[df['Status'] == "Holding"].copy()
        
        if not hold_df.empty:
            t_inv, t_val, t_pnl = hold_df['Investment'].sum(), hold_df['CM Value'].sum(), hold_df['P&L'].sum()
            t_today_pnl = hold_df['Today_PnL'].sum()
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Investment", f"₹{int(t_inv):,}")
            m2.metric("Current Value", f"₹{int(t_val):,}")
            m3.metric("Total P&L", f"₹{int(t_pnl):,}", f"{((t_pnl/t_inv)*100):.2f}%" if t_inv > 0 else "0%")
            m4.metric("Today's P&L", f"₹{int(t_today_pnl):,}", f"{((t_today_pnl/t_val)*100):.2f}%" if t_val > 0 else "0%")

            def style_pnl(val):
                if isinstance(val, (int, float)):
                    return 'color: green' if val > 0 else 'color: red' if val < 0 else ''
                return ''

            display_df = hold_df.copy()
            cols_to_round = ["CMP", "Buy Price", "Investment", "CM Value", "P&L", "Today_PnL"]
            for col in cols_to_round: display_df[col] = display_df[col].astype(int)

            st.dataframe(display_df.style.map(style_pnl, subset=['P&L', 'Today_PnL']), use_container_width=True, hide_index=True)

    with st.expander("➕ Add New Stock / Manage"):
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("### Add Stock")
            b_date = st.date_input("Purchase Date", datetime.now())
            n_in = st.selectbox("Symbol", nifty500_list)
            b_p = st.number_input("Buy Price", min_value=0.1, step=0.1)
            q_y = st.number_input("Qty", min_value=1)
            tax = st.number_input("Tax", min_value=0.0)
            acc = st.selectbox("Account", ["Habeeb", "RISU"])
            
            if st.button("💾 Save Stock"):
                sym = n_in + ".NS" if ".NS" not in n_in else n_in
                inv = (b_p * q_y) + tax
                new_data = {
                    "Category": "Stock", "Buy Date": str(b_date), "Name": sym, "CMP": b_p, 
                    "Buy Price": b_p, "QTY Available": q_y, "Account": acc, 
                    "Investment": inv, "CM Value": inv, "P&L": 0, "P_Percentage": 0, 
                    "Status": "Holding", "Tax": tax, "Dividend": 0, "Today_PnL": 0
                }
                df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False)
                st.success(f"{sym} Added Successfully!")
                st.rerun()

        with col_b:
            st.write("### Sell Stock")
            h_names = df[df['Status'] == 'Holding']['Name'].unique()
            s_name = st.selectbox("Select Stock to Sell", ["None"] + list(h_names))
            if s_name != "None" and st.button("🗑️ Mark as Sold"):
                df.loc[df['Name'] == s_name, 'Status'] = 'Sold'
                df.to_csv(PORTFOLIO_FILE, index=False)
                st.rerun()

# --- TAB 2: HEATMAP ---
with tab2:
    hold_stocks = df[df['Status'] == "Holding"].copy()
    if not hold_stocks.empty:
        fig = px.treemap(hold_stocks, path=['Name'], values='Investment', color='P_Percentage', color_continuous_scale='RdYlGn', range_color=[-5, 5])
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 3: SETTINGS ---
with tab3:
    st.write("### Data Management")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📥 Download Portfolio CSV", df.to_csv(index=False).encode('utf-8'), "portfolio_backup.csv", "text/csv")
    with col2:
        up_file = st.file_uploader("📤 Upload Backup CSV", type="csv")
        if up_file and st.button("Restore Now"):
            pd.read_csv(up_file).to_csv(PORTFOLIO_FILE, index=False)
            st.rerun()
