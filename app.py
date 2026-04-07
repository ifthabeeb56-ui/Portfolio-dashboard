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

# --- SIDEBAR: BACKUP & UPLOAD ---
st.sidebar.header("⚙️ Data Management")

# 1. Portfolio Backup
st.sidebar.subheader("Portfolio Data")
if not df.empty:
    csv_p = df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button("📥 Portfolio Backup", data=csv_p, file_name="portfolio_backup.csv", mime='text/csv')

up_p = st.sidebar.file_uploader("Restore Portfolio (CSV)", type="csv")
if up_p and st.sidebar.button("Confirm Portfolio Restore"):
    pd.read_csv(up_p).to_csv(PORTFOLIO_FILE, index=False)
    st.rerun()

st.sidebar.divider()

# 2. Watchlist Backup
st.sidebar.subheader("Watchlist Data")
if watch_stocks:
    wl_content = "\n".join(watch_stocks)
    st.sidebar.download_button("📥 Watchlist Backup", data=wl_content, file_name="watchlist_backup.txt")

up_w = st.sidebar.file_uploader("Restore Watchlist (TXT)", type="txt")
if up_w and st.sidebar.button("Confirm Watchlist Restore"):
    with open(WATCHLIST_FILE, "wb") as f:
        f.write(up_w.getvalue())
    st.rerun()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "📜 Sold History", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 1: HEATMAP ---
with tab1:
    hold_stocks_df = df[df['Status'] == "Holding"].copy()
    if not hold_stocks_df.empty:
        fig = px.treemap(hold_stocks_df, path=['Name'], values='Investment', color='P_Percentage', 
                         color_continuous_scale='RdYlGn', range_color=[-5, 5])
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("ഹീറ്റ്‌മാപ്പ് കാണുന്നതിനായി സ്റ്റോക്കുകൾ ആഡ് ചെയ്യുക.")

# --- TAB 2: PORTFOLIO ---
with tab2:
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
            m4.metric("Today's P&L", f"₹{int(t_today_pnl):,}")

            view_mode = st.radio("Display Mode:", ["Detailed View", "Summary View"], horizontal=True)
            style_func = lambda x: 'color: green' if isinstance(x, (int, float)) and x > 0 else 'color: red' if isinstance(x, (int, float)) and x < 0 else ''

            if view_mode == "Summary View":
                summ_df = hold_df.groupby(['Name', 'Account']).agg({'Investment':'sum', 'CM Value':'sum', 'P&L':'sum', 'Today_PnL':'sum'}).reset_index()
                summ_df['Weight %'] = ((summ_df['Investment'] / t_inv) * 100).round(1) if t_inv > 0 else 0
                for c in ['Investment', 'CM Value', 'P&L', 'Today_PnL']: summ_df[c] = summ_df[c].astype(int)
                st.dataframe(summ_df.style.map(style_func, subset=['P&L', 'Today_PnL']), use_container_width=True, hide_index=True)
            else:
                det_df = hold_df.copy()
                for c in ["CMP", "Buy Price", "Investment", "CM Value", "P&L", "Today_PnL"]: det_df[c] = det_df[c].astype(int)
                st.dataframe(det_df.style.map(style_func, subset=['P&L', 'Today_PnL']), use_container_width=True, hide_index=True)

    with st.expander("➕ Add/Remove/Update Stock"):
        c_a, c_b = st.columns(2)
        with c_a:
            st.subheader("Add Stock")
            b_date = st.date_input("Date", datetime.now())
            n_in = st.selectbox("Symbol", nifty500_list)
            sym = n_in + ".NS" if ".NS" not in n_in else n_in
            
            # --- Auto Price Fetching ---
            auto_p = 0.0
            try:
                auto_p = yf.Ticker(sym).history(period="1d")['Close'].iloc[-1]
            except: auto_p = 0.0

            b_p = st.number_input("Buy Price", value=float(round(auto_p, 2)), min_value=0.0)
            q_y = st.number_input("Qty", min_value=1)
            tax_in, acc_in = st.number_input("Tax", 0.0), st.selectbox("Account", ["Habeeb", "RISU"])
            
            if st.button("💾 Save Stock"):
                if b_p <= 0:
                    st.error("Price cannot be zero! സ്റ്റോക്ക് സേവ് ചെയ്തിട്ടില്ല.")
                else:
                    new = {"Category": "Equity", "Buy Date": str(b_date), "Name": sym, "CMP": b_p, "Buy Price": b_p, "QTY Available": q_y, "Account": acc_in, "Investment": round(q_y*b_p, 2), "CM Value": round(q_y*b_p, 2), "P&L": 0, "P_Percentage": 0, "Status": "Holding", "Tax": tax_in, "Dividend": 0, "Today_PnL": 0, "Sell_Price": 0, "Sell_Date": ""}
                    df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                    df.to_csv(PORTFOLIO_FILE, index=False)
                    st.success(f"{sym} Saved!")
                    time.sleep(1)
                    st.rerun()
        with c_b:
            st.subheader("Manage Stock")
            h_list = list(df[df['Status']=='Holding']['Name'].unique())
            st_m = st.selectbox("Select Stock", ["None"] + h_list)
            if st_m != "None":
                s_p = st.number_input("Selling Price", 0.0)
                if st.button("🗑️ Mark as Sold"):
                    idx = df[df['Name'] == st_m].index
                    df.loc[idx, 'Status'], df.loc[idx, 'Sell_Price'], df.loc[idx, 'Sell_Date'] = 'Sold', s_p, datetime.now().strftime('%Y-%m-%d')
                    f_val = df.loc[idx, 'QTY Available'] * s_p
                    df.loc[idx, 'P&L'] = round((f_val + df.loc[idx, 'Dividend']) - (df.loc[idx, 'Investment'] + df.loc[idx, 'Tax']), 2)
                    df.loc[idx, 'P_Percentage'] = round((df.loc[idx, 'P&L'] / df.loc[idx, 'Investment']) * 100, 2)
                    df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()
                div_v = st.number_input("Add Dividend", 0.0)
                if st.button("➕ Update Dividend"):
                    df.loc[df['Name'] == st_m, 'Dividend'] += div_v
                    df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()

# --- TAB 3: SOLD HISTORY ---
with tab3:
    st.subheader("📜 Sold Stocks")
    sold_df = df[df['Status'] == 'Sold'].copy()
    if not sold_df.empty:
        disp_sold = sold_df[['Sell_Date', 'Name', 'QTY Available', 'Buy Price', 'Sell_Price', 'Investment', 'P&L', 'P_Percentage']].copy()
        disp_sold.columns = ['Sold Date', 'Stock Name', 'Qty', 'Buy Price', 'Sell Price', 'Inv. Value', 'Profit/Loss', 'Gain %']
        for col in ['Qty', 'Buy Price', 'Sell Price', 'Inv. Value', 'Profit/Loss']: disp_sold[col] = disp_sold[col].astype(int)
        st.dataframe(disp_sold.style.map(lambda x: 'color: green' if isinstance(x, (int, float)) and x > 0 else 'color: red' if isinstance(x, (int, float)) and x < 0 else '', subset=['Profit/Loss', 'Gain %']), use_container_width=True, hide_index=True)
    else: st.info("വിറ്റ സ്റ്റോക്കുകളുടെ വിവരങ്ങൾ ലഭ്യമല്ല.")

# --- TAB 4: ANALYTICS ---
with tab4:
    if not hold_stocks_df.empty:
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.pie(hold_stocks_df, values='Investment', names='Account', title='Account Distribution', hole=0.4), use_container_width=True)
        c2.plotly_chart(px.bar(hold_stocks_df, x='Name', y='P&L', color='P&L', title='Stock-wise P&L'), use_container_width=True)

# --- TAB 5: NEWS ---
with tab5:
    n_stk = st.selectbox("Select Stock for News:", ["None"] + list(df['Name'].unique()))
    if n_stk != "None" and st.button("Get News"):
        with st.spinner("തിരയുന്നു..."):
            try:
                gn = GoogleNews(lang='en', period='7d')
                gn.search(n_stk.replace(".NS", ""))
                time.sleep(1)
                res = gn.result()
                if res:
                    trans = GoogleTranslator(source='en', target='ml')
                    for r in res[:5]:
                        st.write(f"📢 **{r['title']}**")
                        with st.expander("മലയാളത്തിൽ"):
                            try: st.write(trans.translate(r['title']))
                            except: st.write("పరిഭാഷ പ伝えるു.")
                        st.caption(f"{r['date']} | [Read More]({r['link']})")
                        st.divider()
                else: st.info("വാർത്തകളില്ല.")
            except Exception as e: st.error(f"Error: {e}")

# --- TAB 6: WATCHLIST ---
with tab6:
    st.subheader("👀 My Watchlist")
    win = st.text_input("Add Symbol").upper().strip()
    if st.button("Add") and win:
        tck = win + ".NS" if ".NS" not in win else win
        with open(WATCHLIST_FILE, "a") as f: f.write(tck + "\n")
        st.rerun()
    if watch_stocks:
        for s in watch_stocks:
            wc1, wc2 = st.columns([4, 1])
            wc1.write(f"📈 **{s}**")
            if wc2.button("Remove", key=f"del_{s}"):
                upd = [i for i in watch_stocks if i != s]
                with open(WATCHLIST_FILE, "w") as f:
                    for i in upd: f.write(i + "\n")
                st.rerun()
