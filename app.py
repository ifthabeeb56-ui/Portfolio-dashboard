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
HISTORY_FILE = "portfolio_history.csv"

@st.cache_data(ttl=86400)
def get_nifty500_tickers():
    try:
        url = "https://raw.githubusercontent.com/anirban-d/nifty-indices-constituents/main/ind_nifty500list.csv"
        n500_df = pd.read_csv(url)
        return sorted(n500_df['Symbol'].tolist())
    except:
        return ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN"]

@st.cache_data(ttl=604800) # കമ്പനി പേര് ഒരാഴ്ചത്തേക്ക് ക്യാഷ് ചെയ്യുന്നു
def get_company_name(symbol):
    try:
        return yf.Ticker(symbol).info.get('longName', symbol)
    except:
        return symbol

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
        save_portfolio_history(df[df['Status'] == "Holding"]['CM Value'].sum())
    except: st.sidebar.error("ലൈവ് പ്രൈസ് അപ്‌ഡേറ്റ് പരാജയപ്പെട്ടു.")
    return df

# --- App Setup ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v7.1", page_icon="📈")
df = load_data()
watch_stocks = get_watchlist()
nifty500_list = get_nifty500_tickers()

# --- SIDEBAR: DATA MANAGEMENT ---
st.sidebar.header("⚙️ Data Management")
st.sidebar.subheader("📂 Portfolio & History")
if not df.empty:
    st.sidebar.download_button("📥 Backup Portfolio", data=df.to_csv(index=False).encode('utf-8'), file_name="portfolio_backup.csv", mime='text/csv')

up_p = st.sidebar.file_uploader("Restore Portfolio (CSV)", type="csv")
if up_p and st.sidebar.button("✅ Confirm Portfolio Restore"):
    pd.read_csv(up_p).to_csv(PORTFOLIO_FILE, index=False)
    st.sidebar.success("ഡാറ്റ അപ്‌ലോഡ് ചെയ്തു!")
    st.rerun()

st.sidebar.divider()
st.sidebar.subheader("🔭 Watchlist")
if watch_stocks:
    st.sidebar.download_button("📥 Backup Watchlist", data="\n".join(watch_stocks), file_name="watchlist_backup.txt")

up_w = st.sidebar.file_uploader("Restore Watchlist (TXT)", type="txt")
if up_w and st.sidebar.button("✅ Confirm Watchlist Restore"):
    with open(WATCHLIST_FILE, "wb") as f: f.write(up_w.getvalue())
    st.sidebar.success("വാച്ച്‌ലിസ്റ്റ് അപ്‌ലോഡ് ചെയ്തു!")
    st.rerun()

st.title("📊 Habeeb's Power Hub v7.1")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "📜 Sold History", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 1: HEATMAP ---
with tab1:
    st.subheader("Market Visualization")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        size_opt = st.radio("Box Size based on:", ["Investment", "Daily % Change"], horizontal=True)
    with col_s2:
        show_watch = st.toggle("Include Watchlist", value=False)
    
    hold_stocks_df = df[df['Status'] == "Holding"].copy()
    final_tickers = list(set(hold_stocks_df['Name'].tolist() + watch_stocks)) if show_watch else hold_stocks_df['Name'].tolist()

    if final_tickers:
        with st.spinner("Fetching Data..."):
            try:
                m_data = yf.download(final_tickers, period="5d", progress=False)['Close']
                if not m_data.empty and len(m_data) > 1:
                    m_changes = ((m_data.iloc[-1] - m_data.iloc[-2]) / m_data.iloc[-2]) * 100
                    m_df = pd.DataFrame({"Symbol": m_changes.index, "Change %": m_changes.values, "Price": m_data.iloc[-1].values})
                    m_df = m_df.merge(hold_stocks_df[['Name', 'Investment']], left_on='Symbol', right_on='Name', how='left')
                    m_df['Investment'] = m_df['Investment'].fillna(1000)
                    m_df['Size_Value'] = m_df['Change %'].abs() + 0.1 if size_opt == "Daily % Change" else m_df['Investment']
                    
                    fig = px.treemap(m_df, path=['Symbol'], values='Size_Value', color='Change %', color_continuous_scale='RdYlGn', range_color=[-3, 3])
                    fig.update_traces(textinfo="label+text", texttemplate="<b>%{label}</b><br>%{color:.2f}%")
                    st.plotly_chart(fig, use_container_width=True)
            except: st.error("ഹീറ്റ്‌മാപ്പ് ഡാറ്റ ലഭ്യമല്ല.")
    else: st.info("സ്റ്റോക്കുകൾ ആഡ് ചെയ്യുക.")

# --- TAB 2: PORTFOLIO ---
with tab2:
    df = update_live_prices(df)
    hold_df = df[df['Status'] == "Holding"].copy()
    if not hold_df.empty:
        t_inv, t_val, t_pnl = hold_df['Investment'].sum(), hold_df['CM Value'].sum(), hold_df['P&L'].sum()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Investment", f"₹{int(t_inv):,}")
        m2.metric("Current Value", f"₹{int(t_val):,}")
        m3.metric("Total P&L", f"₹{int(t_pnl):,}", f"{((t_pnl/t_inv)*100):.2f}%" if t_inv > 0 else "0%")
        m4.metric("Today's P&L", f"₹{int(hold_df['Today_PnL'].sum()):,}")
        
        # ടേബിൾ ഭംഗിയാക്കാൻ ചില കോളങ്ങൾ ഒഴിവാക്കുന്നു
        disp_df = hold_df[['Buy Date', 'Name', 'QTY Available', 'Buy Price', 'CMP', 'Investment', 'CM Value', 'P&L', 'P_Percentage', 'Account']]
        st.dataframe(disp_df, use_container_width=True, hide_index=True)

    with st.expander("➕ Add/Remove/Update Stock"):
        c_a, c_b = st.columns(2)
        with c_a:
            st.subheader("Add Stock")
            b_date = st.date_input("Date", datetime.now())
            n_in = st.selectbox("Symbol", nifty500_list)
            sym = n_in + ".NS" if ".NS" not in n_in else n_in
            
            # --- Auto Name & Price Logic ---
            comp_name = get_company_name(sym)
            auto_p = 0.0
            try:
                auto_p = yf.Ticker(sym).history(period="1d")['Close'].iloc[-1]
            except: auto_p = 0.0
            
            st.info(f"Company: **{comp_name}**")
            b_p = st.number_input("Buy Price", value=float(round(auto_p, 2)), min_value=0.0)
            q_y = st.number_input("Qty", min_value=1)
            tax_in, acc_in = st.number_input("Tax", 0.0), st.selectbox("Account", ["Habeeb", "RISU"])
            
            if st.button("💾 Save Stock"):
                if b_p <= 0: st.error("Price 0 ആയി സേവ് ചെയ്യാൻ പറ്റില്ല!")
                else:
                    new = {"Category": "Equity", "Buy Date": str(b_date), "Name": sym, "CMP": b_p, "Buy Price": b_p, "QTY Available": q_y, "Account": acc_in, "Investment": round(q_y*b_p, 2), "CM Value": round(q_y*b_p, 2), "P&L": 0, "P_Percentage": 0, "Status": "Holding", "Tax": tax_in, "Dividend": 0, "Today_PnL": 0}
                    df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                    df.to_csv(PORTFOLIO_FILE, index=False); st.success("Saved!"); time.sleep(1); st.rerun()

        with c_b:
            st.subheader("Manage Stock")
            h_list = list(df[df['Status']=='Holding']['Name'].unique())
            st_m = st.selectbox("Select Stock", ["None"] + h_list)
            if st_m != "None":
                s_p = st.number_input("Selling Price", 0.0)
                if st.button("🗑️ Mark as Sold"):
                    idx = df[df['Name'] == st_m].index
                    df.at[idx[0], 'Status'] = 'Sold'
                    df.at[idx[0], 'Sell_Price'] = s_p
                    df.at[idx[0], 'Sell_Date'] = datetime.now().strftime('%Y-%m-%d')
                    # സെൽ ചെയ്യുമ്പോൾ ലാഭം പുനർനിർണ്ണയിക്കുന്നു
                    total_sell_val = df.at[idx[0], 'QTY Available'] * s_p
                    df.at[idx[0], 'P&L'] = round((total_sell_val + df.at[idx[0], 'Dividend']) - (df.at[idx[0], 'Investment'] + df.at[idx[0], 'Tax']), 2)
                    df.at[idx[0], 'P_Percentage'] = round((df.at[idx[0], 'P&L'] / df.at[idx[0], 'Investment']) * 100, 2)
                    df.to_csv(PORTFOLIO_FILE, index=False); st.success("Sold!"); time.sleep(1); st.rerun()
                
                div_v = st.number_input("Add Dividend", 0.0)
                if st.button("➕ Update Dividend"):
                    df.loc[df['Name'] == st_m, 'Dividend'] += div_v
                    df.to_csv(PORTFOLIO_FILE, index=False); st.success("Dividend Updated!"); time.sleep(1); st.rerun()

# --- TAB 3: SOLD HISTORY ---
with tab3:
    sold_df = df[df['Status'] == 'Sold'].copy()
    if not sold_df.empty:
        st.dataframe(sold_df[['Sell_Date', 'Name', 'QTY Available', 'Buy Price', 'Sell_Price', 'P&L', 'P_Percentage', 'Account']], use_container_width=True, hide_index=True)
    else: st.info("വിറ്റ വിവരങ്ങൾ ലഭ്യമല്ല.")

# --- TAB 4: ANALYTICS ---
with tab4:
    if not hold_df.empty:
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.pie(hold_df, values='Investment', names='Account', title='Account Distribution', hole=0.4), use_container_width=True)
        if os.path.exists(HISTORY_FILE):
            st.plotly_chart(px.line(pd.read_csv(HISTORY_FILE), x='Date', y='Total_Value', title="Portfolio Trend (Current Value Over Time)"), use_container_width=True)

# --- TAB 5: NEWS ---
with tab5:
    n_stk = st.selectbox("News for:", ["None"] + list(df['Name'].unique()))
    if n_stk != "None" and st.button("Get News"):
        with st.spinner("വാർത്തകൾ തിരയുന്നു..."):
            try:
                gn = GoogleNews(lang='en', period='7d'); gn.search(n_stk.replace(".NS", ""))
                trans = GoogleTranslator(source='en', target='ml')
                results = gn.result()
                if results:
                    for r in results[:5]:
                        st.write(f"📢 **{r['title']}**")
                        with st.expander("മലയാളത്തിൽ"): st.write(trans.translate(r['title']))
                        st.caption(f"{r['date']} | [Read More]({r['link']})")
                else: st.info("വാർത്തകളൊന്നും ലഭ്യമല്ല.")
            except: st.error("വാർത്തകൾ ലോഡ് ചെയ്യാൻ കഴിഞ്ഞില്ല.")

# --- TAB 6: WATCHLIST ---
with tab6:
    win = st.text_input("Add Symbol (e.g. RELIANCE)").upper().strip()
    if st.button("Add") and win:
        t_sym = win + ".NS" if ".NS" not in win else win
        with open(WATCHLIST_FILE, "a") as f: f.write(t_sym + "\n")
        st.success(f"{t_sym} വാച്ച്‌ലിസ്റ്റിൽ ചേർത്തു!")
        time.sleep(1); st.rerun()
        
    if watch_stocks:
        for s in watch_stocks:
            wc1, wc2 = st.columns([4, 1])
            wc1.write(f"📈 **{s}** - {get_company_name(s)}")
            if wc2.button("Remove", key=f"del_{s}"):
                upd = [i for i in watch_stocks if i != s]
                with open(WATCHLIST_FILE, "w") as f:
                    for i in upd: f.write(i + "\n")
                st.rerun()
                    
