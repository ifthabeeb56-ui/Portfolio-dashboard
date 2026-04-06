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
    req_cols = ["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", 
                "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", 
                "Remark", "Status", "Today_PnL", "Sell_Price", "Sell_Date"]
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        for col in req_cols:
            if col not in df.columns:
                df[col] = "" if col in ["Sell_Date", "Remark", "Category", "Account", "Status", "Name"] else 0.0
            if col not in ["Sell_Date", "Status", "Name", "Account", "Category", "Remark", "Buy Date"]:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=req_cols)

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

# --- Sidebar Management ---
st.sidebar.header("⚙️ Settings")
if st.sidebar.button("🔄 Force Refresh Data"):
    st.rerun()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "📜 Sold History", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 1: HEATMAP (ValueError Fix) ---
with tab1:
    hold_stocks_df = df[df['Status'] == "Holding"].copy()
    if not hold_stocks_df.empty:
        st.subheader("Market Visualization Settings")
        box_size_opt = st.radio("Box Size based on:", ["Investment", "Daily % Change"], horizontal=True)
        st.toggle("Include Watchlist in Heatmap")
        
        val_col = 'Investment' if box_size_opt == "Investment" else 'Today_PnL'
        hold_stocks_df['Plot_Val'] = hold_stocks_df[val_col].abs()
        
        if hold_stocks_df['Plot_Val'].sum() > 0:
            fig = px.treemap(hold_stocks_df, path=['Name'], values='Plot_Val', 
                             color='P_Percentage', color_continuous_scale='RdYlGn', 
                             range_color=[-5, 5])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("ഹീറ്റ്‌മാപ്പ് കാണിക്കാൻ മതിയായ ഡാറ്റയില്ല.")
    else:
        st.info("സ്റ്റോക്കുകൾ ആഡ് ചെയ്യുക.")

# --- TAB 2: PORTFOLIO & ADD STOCK ---
with tab2:
    if not df.empty:
        df = update_live_prices(df)
        hold_df = df[df['Status'] == "Holding"].copy()
        if not hold_df.empty:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Investment", f"₹{int(hold_df['Investment'].sum()):,}")
            m2.metric("Current Value", f"₹{int(hold_df['CM Value'].sum()):,}")
            m3.metric("Total P&L", f"₹{int(hold_df['P&L'].sum()):,}")
            m4.metric("Today's P&L", f"₹{int(hold_df['Today_PnL'].sum()):,}")
            st.dataframe(hold_df, use_container_width=True, hide_index=True)

    # Add/Update Section (നിങ്ങളുടെ സ്ക്രീൻഷോട്ടിലെ ലേഔട്ട് അനുസരിച്ച്)
    with st.expander("➕ Add/Remove/Update Stock"):
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Add New Stock")
            p_date = st.date_input("Purchase Date", datetime.now())
            category = st.selectbox("Category", ["Equity", "Mutual Fund", "ETF", "Gold"])
            account = st.selectbox("Account", ["Habeeb", "RISU", "Family"])
            n_selection = st.selectbox("Select Symbol from Nifty 500", ["Custom"] + nifty500_list)
            symbol_input = st.text_input("Enter Symbol").upper() if n_selection == "Custom" else n_selection
            final_sym = symbol_input + ".NS" if symbol_input and ".NS" not in symbol_input else symbol_input
        with col_b:
            st.write("<br><br>", unsafe_allow_html=True) # Spacer
            buy_price = st.number_input("Buy Price", min_value=0.0, step=0.05)
            qty = st.number_input("Qty", min_value=1, step=1)
            tax = st.number_input("Tax", value=0.0)
            remark = st.text_input("Remark")

        if st.button("💾 Save Stock", use_container_width=True):
            if final_sym:
                new_entry = {
                    "Category": category, "Buy Date": str(p_date), "Name": final_sym, 
                    "CMP": buy_price, "Buy Price": buy_price, "QTY Available": qty, 
                    "Account": account, "Investment": round(qty * buy_price, 2), 
                    "CM Value": round(qty * buy_price, 2), "P&L": 0, "P_Percentage": 0, 
                    "Status": "Holding", "Tax": tax, "Dividend": 0, "Today_PnL": 0, 
                    "Remark": remark, "Sell_Price": 0, "Sell_Date": ""
                }
                df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False)
                st.success("Saved!"); st.rerun()

        st.divider()
        st.subheader("Manage Existing")
        st_m = st.selectbox("Select Stock to Update/Sell", ["None"] + list(df[df['Status']=='Holding']['Name'].unique()))
        if st_m != "None":
            m_col1, m_col2 = st.columns(2)
            sell_p = m_col1.number_input("Selling Price")
            if m_col1.button("Mark as Sold", use_container_width=True):
                idx = df[df['Name'] == st_m].index
                df.loc[idx, 'Status'], df.loc[idx, 'Sell_Price'], df.loc[idx, 'Sell_Date'] = 'Sold', sell_p, datetime.now().strftime('%Y-%m-%d')
                df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()
            div_add = m_col2.number_input("Dividend Received")
            if m_col2.button("Update Dividend", use_container_width=True):
                df.loc[df['Name'] == st_m, 'Dividend'] += div_add
                df.to_csv(PORTFOLIO_FILE, index=False); st.success("Updated!"); st.rerun()

# --- TAB 3: SOLD HISTORY ---
with tab3:
    sold_df = df[df['Status'] == "Sold"].copy()
    if not sold_df.empty:
        st.dataframe(sold_df, use_container_width=True)
    else: st.info("വിൽപന നടന്ന സ്റ്റോക്കുകൾ ഇവിടെ കാണാം.")

# --- TAB 4: ANALYTICS ---
with tab4:
    if not hold_stocks_df.empty:
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.pie(hold_stocks_df, values='Investment', names='Account', title='Account Distribution'), use_container_width=True)
        c2.plotly_chart(px.bar(hold_stocks_df, x='Name', y='P&L', color='P&L', title='Stock-wise P&L'), use_container_width=True)

# --- TAB 5: NEWS (Malayalam Translation) ---
with tab5:
    n_stk = st.selectbox("Get News for:", ["None"] + list(df['Name'].unique()))
    if n_stk != "None" and st.button("Fetch News"):
        with st.spinner("തിരയുന്നു..."):
            try:
                gn = GoogleNews(lang='en', period='7d')
                gn.search(n_stk.replace(".NS", ""))
                res = gn.result()
                if res:
                    translator = GoogleTranslator(source='auto', target='ml')
                    for r in res[:5]:
                        st.write(f"📢 **{r['title']}**")
                        with st.expander("മലയാളത്തിൽ വായിക്കാം"):
                            st.write(translator.translate(r['title']))
                        st.caption(f"{r['date']} | [Link]({r['link']})")
                        st.divider()
            except: st.error("വാർത്തകൾ ലഭ്യമായില്ല.")

# --- TAB 6: WATCHLIST ---
with tab6:
    st.subheader("👀 My Watchlist")
    new_w = st.text_input("Add Symbol to Watchlist").upper().strip()
    if st.button("Add") and new_w:
        with open(WATCHLIST_FILE, "a") as f: f.write((new_w + ".NS" if ".NS" not in new_w else new_w) + "\n")
        st.rerun()
    for s in get_watchlist():
        wc1, wc2 = st.columns([5, 1])
        wc1.write(f"📈 **{s}**")
        if wc2.button("🗑️", key=f"del_{s}"):
            upd = [i for i in get_watchlist() if i != s]
            with open(WATCHLIST_FILE, "w") as f:
                for i in upd: f.write(i + "\n")
            st.rerun()
                             
