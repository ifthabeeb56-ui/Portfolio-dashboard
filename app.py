import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os
from GoogleNews import GoogleNews
from deep_translator import GoogleTranslator

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

def get_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            return sorted(list(set([line.strip() for line in f.readlines() if line.strip()])))
    return []

def save_portfolio_history(total_val):
    today = str(datetime.now().date())
    h_df = pd.DataFrame(columns=["Date", "Total_Value"])
    if os.path.exists(HISTORY_FILE):
        h_df = pd.read_csv(HISTORY_FILE)
    if today in h_df['Date'].values:
        h_df.loc[h_df['Date'] == today, 'Total_Value'] = total_val
    else:
        new_entry = pd.DataFrame([{"Date": today, "Total_Value": total_val}])
        h_df = pd.concat([h_df, new_entry], ignore_index=True)
    h_df.to_csv(HISTORY_FILE, index=False)

def update_live_prices(df):
    tickers = df[df['Status'] == "Holding"]['Name'].unique().tolist()
    if not tickers: return df
    try:
        # കൃത്യമായ ഇന്നത്തെയും ഇന്നലത്തെയും വില കിട്ടാൻ 5d ഡാറ്റ എടുക്കുന്നു
        live_data = yf.download(tickers, period="5d", progress=False)['Close']
        if live_data.empty: return df
        
        for index, row in df.iterrows():
            if row['Status'] == "Holding":
                t_name = row['Name']
                try:
                    # സിംഗിൾ ടിക്കർ ആണെങ്കിലും മൾട്ടിപ്പിൾ ആണെങ്കിലും കൃത്യമായി ഡാറ്റ എടുക്കാൻ
                    if isinstance(live_data, pd.Series):
                        stock_series = live_data.dropna()
                    else:
                        stock_series = live_data[t_name].dropna()
                    
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
                except: continue
        df.to_csv(PORTFOLIO_FILE, index=False)
        save_portfolio_history(df[df['Status'] == "Holding"]['CM Value'].sum())
    except: st.sidebar.error("ലൈവ് പ്രൈസ് അപ്‌ഡേറ്റ് പരാജയപ്പെട്ടു.")
    return df

# --- App Setup ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9", page_icon="📈")
df = load_data()
watch_stocks = get_watchlist()
nifty500_list = get_nifty500_tickers()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 1: HEATMAP ---
with tab1:
    hold_stocks_df = df[df['Status'] == "Holding"].copy()
    if not hold_stocks_df.empty:
        # ഹീറ്റ്‌മാപ്പ് ലോജിക് ഇവിടെ ചേർക്കാം (മുൻപത്തെ പോലെ)
        st.info("Heatmap features active for " + str(len(hold_stocks_df)) + " stocks.")
    else:
        st.info("Portfolio-ൽ സ്റ്റോക്കുകൾ ആഡ് ചെയ്യുമ്പോൾ ഇവിടെ ഹീറ്റ്‌മാപ്പ് തെളിയും.")

# --- TAB 2: PORTFOLIO ---
with tab2:
    if not df.empty:
        df = update_live_prices(df)
        hold_df = df[df['Status'] == "Holding"].copy()
        
        if not hold_df.empty:
            t_inv, t_val, t_pnl = hold_df['Investment'].sum(), hold_df['CM Value'].sum(), hold_df['P&L'].sum()
            t_today_pnl = hold_df['Today_PnL'].sum()
            
            # Metrics Row
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Investment", f"₹{int(t_inv):,}")
            m2.metric("Current Value", f"₹{int(t_val):,}")
            m3.metric("Total P&L", f"₹{int(t_pnl):,}", f"{((t_pnl/t_inv)*100):.2f}%" if t_inv > 0 else "0%")
            # Today's P&L-ന് കളർ കൊടുക്കാൻ
            m4.metric("Today's P&L", f"₹{int(t_today_pnl):,}", f"{((t_today_pnl/t_val)*100):.2f}%" if t_val > 0 else "0%")

            view_mode = st.radio("Display Mode:", ["Detailed View", "Summary View"], horizontal=True)

            def style_pnl(val):
                if isinstance(val, (int, float)):
                    return 'color: green' if val > 0 else 'color: red' if val < 0 else 'color: white'
                return ''

            if view_mode == "Summary View":
                summ_df = hold_df[['Name', 'Investment', 'CM Value', 'P&L', 'Today_PnL']].copy()
                summ_df['Weight %'] = ((summ_df['Investment'] / t_inv) * 100).round(1) if t_inv > 0 else 0
                
                # Decimal removal for display
                display_summ = summ_df.copy()
                for col in ['Investment', 'CM Value', 'P&L', 'Today_PnL']:
                    display_summ[col] = display_summ[col].astype(int)
                
                st.dataframe(display_summ.style.map(style_pnl, subset=['P&L', 'Today_PnL']), 
                             use_container_width=True, hide_index=True)
            else:
                det_df = hold_df.copy()
                display_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "Today_PnL"]
                for c in display_cols: det_df[c] = det_df[c].astype(int)
                
                st.dataframe(det_df.style.map(style_pnl, subset=['P&L', 'Today_PnL']), 
                             use_container_width=True, hide_index=True)

    # Add/Update Stock Expander
    with st.expander("➕ Add / Manage Stock"):
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("### Add New Stock")
            b_date = st.date_input("Purchase Date")
            n_in = st.selectbox("Symbol", nifty500_list)
            b_p = st.number_input("Buy Price", min_value=0.0)
            q_y = st.number_input("Qty", min_value=1)
            tax = st.number_input("Tax", min_value=0.0)
            acc = st.selectbox("Account", ["Habeeb", "RISU"])
            cat = st.selectbox("Category", ["Equity", "ETF", "MF"])
            
            if st.button("💾 Save to Portfolio"):
                sym = n_in + ".NS" if ".NS" not in n_in else n_in
                # Investment calculation (Price * Qty + Tax)
                inv_amt = (b_p * q_y) + tax
                new_row = {
                    "Category": cat, "Buy Date": str(b_date), "Name": sym, "CMP": b_p, 
                    "Buy Price": b_p, "QTY Available": q_y, "Account": acc, 
                    "Investment": inv_amt, "CM Value": inv_amt, "P&L": 0, 
                    "P_Percentage": 0, "Tax": tax, "Dividend": 0, "Status": "Holding", "Today_PnL": 0
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False)
                st.success(f"{sym} Added!")
                st.rerun()
        
        with col_b:
            st.write("### Manage Existing")
            sell_list = df[df['Status'] == "Holding"]['Name'].unique()
            s_stock = st.selectbox("Select Stock to Sell", ["None"] + list(sell_list))
            if s_stock != "None" and st.button("🗑️ Mark as Sold"):
                df.loc[df['Name'] == s_stock, 'Status'] = 'Sold'
                df.to_csv(PORTFOLIO_FILE, index=False)
                st.rerun()

# --- TAB 3, 4, 5 (വാർത്തകൾ, വാച്ച്‌ലിസ്റ്റ് എന്നിവ മുൻപത്തെ പോലെ തന്നെ) ---
