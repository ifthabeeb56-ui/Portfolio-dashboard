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
WATCHLIST_FILE = "watchlist_data_v2.csv"
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
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage", "Dividend", "Tax"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Remark", "Status"])

def get_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        return pd.read_csv(WATCHLIST_FILE)
    return pd.DataFrame(columns=["Symbol", "Added Date", "Added Price"])

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
                    if len(tickers) == 1:
                        new_p = float(live_data.iloc[-1])
                    else:
                        new_p = float(live_data[t_name].iloc[-1])
                        
                    if new_p > 0:
                        df.at[index, 'CMP'] = round(new_p, 2)
                        current_val = round(row['QTY Available'] * new_p, 2)
                        df.at[index, 'CM Value'] = current_val
                        net_pnl = (current_val + row['Dividend']) - (row['Investment'] + row['Tax'])
                        df.at[index, 'P&L'] = round(net_pnl, 2)
                        if row['Investment'] > 0:
                            df.at[index, 'P_Percentage'] = round((net_pnl / row['Investment']) * 100, 2)
                except: continue
        df.to_csv(PORTFOLIO_FILE, index=False)
        save_portfolio_history(df[df['Status'] == "Holding"]['CM Value'].sum())
    except: st.sidebar.error("ലൈവ് പ്രൈസ് അപ്‌ഡേറ്റ് ചെയ്യാൻ കഴിഞ്ഞില്ല.")
    return df

# --- ആപ്പ് സെറ്റപ്പ് ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.8", page_icon="📈")
df = load_data()
w_df = get_watchlist()
nifty500_list = get_nifty500_tickers()

st.title("📊 Habeeb's Power Hub v6.8")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 1: HEATMAP ---
with tab1:
    st.subheader("Market Visualization")
    hold_stocks_df = df[df['Status'] == "Holding"].copy()
    hold_stocks = hold_stocks_df['Name'].unique().tolist()

    if hold_stocks:
        with st.spinner("Fetching Heatmap Data..."):
            try:
                m_data = yf.download(hold_stocks, period="5d", progress=False)['Close']
                if not m_data.empty and len(m_data) > 1:
                    m_changes = ((m_data.iloc[-1] - m_data.iloc[-2]) / m_data.iloc[-2]) * 100
                    m_df = pd.DataFrame({"Symbol": m_changes.index, "Change %": m_changes.values, "Price": m_data.iloc[-1].values})
                    m_df = m_df.merge(hold_stocks_df[['Name', 'Investment']], left_on='Symbol', right_on='Name', how='left')
                    
                    fig = px.treemap(m_df, path=['Symbol'], values='Investment', color='Change %',
                                     color_continuous_scale='RdYlGn', range_color=[-3, 3])
                    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=550)
                    st.plotly_chart(fig, use_container_width=True)
            except: st.error("Heatmap Load ചെയ്യാൻ കഴിഞ്ഞില്ല.")
    else:
        st.info("പോർട്ട്‌ഫോളിയോയിൽ സ്റ്റോക്കുകൾ ഇല്ല.")

# --- TAB 2: PORTFOLIO ---
with tab2:
    if not df.empty:
        df = update_live_prices(df)
        hold_df = df[df['Status'] == "Holding"].copy()
        
        # ഡിസ്‌പ്ലേയ്ക്ക് മാത്രം ഡെസിമൽ ഒഴിവാക്കുന്നു
        display_df = hold_df.copy()
        int_cols = ["Investment", "CM Value", "P&L", "QTY Available"]
        for c in int_cols:
            display_df[c] = pd.to_numeric(display_df[c], errors='coerce').fillna(0).astype(int)

        if not hold_df.empty:
            t_inv, t_val, t_pnl = hold_df['Investment'].sum(), hold_df['CM Value'].sum(), hold_df['P&L'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Investment", f"₹{int(t_inv):,}")
            c2.metric("Current Value", f"₹{int(t_val):,}")
            c3.metric("Total P&L", f"₹{int(t_pnl):,}", f"{((t_pnl/t_inv)*100):.2f}%" if t_inv > 0 else "0%")
            
            st.dataframe(display_df.style.map(lambda v: 'color:green' if (isinstance(v, (int, float)) and v > 0) else 'color:red' if (isinstance(v, (int, float)) and v < 0) else '', subset=['P&L']), use_container_width=True, hide_index=True)

    with st.expander("➕ Add / 📉 Sell / ⚙️ Manage"):
        c_a, c_b = st.columns(2)
        with c_a:
            st.write("### Add Stock")
            n_in = st.selectbox("Select Symbol", ["Custom"] + nifty500_list)
            if n_in == "Custom": n_in = st.text_input("Enter Symbol").upper().strip()
            b_p = st.number_input("Buy Price", 0.0)
            q_y = st.number_input("Qty", min_value=1)
            if st.button("💾 Save Stock"):
                if n_in:
                    sym = n_in + ".NS" if ".NS" not in n_in else n_in
                    new = {"Category": "Equity", "Buy Date": str(datetime.now().date()), "Name": sym, "CMP": b_p, "Buy Price": b_p, "QTY Available": q_y, "Account": "Habeeb", "Investment": round(q_y*b_p, 2), "CM Value": round(q_y*b_p, 2), "P&L": 0, "P_Percentage": 0, "Status": "Holding", "Dividend": 0, "Tax": 0}
                    df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                    df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()
        
        with c_b:
            st.write("### Sell / Update")
            hold_list = list(df[df['Status']=='Holding']['Name'].unique())
            st_manage = st.selectbox("Select Stock", ["None"] + hold_list)
            if st_manage != "None":
                row_idx = df[df['Name'] == st_manage].index[0]
                max_q = int(df.at[row_idx, 'QTY Available'])
                s_q = st.number_input("Sell Quantity", min_value=1, max_value=max_q, value=1)
                s_p = st.number_input("Selling Price", value=float(df.at[row_idx, 'CMP']))
                
                if st.button("📉 Confirm Sell"):
                    buy_price = df.at[row_idx, 'Buy Price']
                    realized = (s_p - buy_price) * s_q
                    df.at[row_idx, 'QTY Available'] -= s_q
                    df.at[row_idx, 'Investment'] = df.at[row_idx, 'QTY Available'] * buy_price
                    if df.at[row_idx, 'QTY Available'] <= 0:
                        df.at[row_idx, 'Status'] = 'Sold'
                    df.to_csv(PORTFOLIO_FILE, index=False)
                    st.success(f"വിറ്റു! ലാഭം/നഷ്ടം: ₹{realized:.2f}"); st.rerun()

                div_add = st.number_input("Add Dividend", 0.0)
                if st.button("➕ Update Dividend"):
                    df.at[row_idx, 'Dividend'] += div_add
                    df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()

# --- TAB 3: ANALYTICS ---
with tab3:
    st.subheader("📈 Distribution")
    hold_df = df[df['Status'] == "Holding"]
    if not hold_df.empty:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.plotly_chart(px.pie(hold_df, values='Investment', names='Category', title='Category'), use_container_width=True)
        with col_p2:
            st.plotly_chart(px.pie(hold_df, values='Investment', names='Account', title='Account'), use_container_width=True)
    if os.path.exists(HISTORY_FILE):
        h_df = pd.read_csv(HISTORY_FILE)
        st.plotly_chart(px.line(h_df, x='Date', y='Total_Value', title="Portfolio Trend"), use_container_width=True)

# --- TAB 4: NEWS ---
with tab4:
    st.subheader("📰 സ്റ്റോക്ക് വാർത്തകൾ")
    tickers_news = list(df['Name'].unique())
    n_stock = st.selectbox("സ്റ്റോക്ക് സെലക്ട് ചെയ്യുക:", ["None"] + tickers_news)
    if n_stock != "None":
        if st.button("Get News"):
            try:
                gn = GoogleNews(lang='en', period='7d')
                gn.search(n_stock.replace(".NS", ""))
                for r in gn.result()[:5]:
                    title = GoogleTranslator(source='auto', target='ml').translate(r['title'])
                    st.write(f"📢 **{title}**")
                    st.caption(f"[Read More]({r['link']})")
            except: st.error("വാർത്തകൾ ലഭ്യമല്ല.")

# --- TAB 5: WATCHLIST ---
with tab5:
    st.subheader("👀 Watchlist Management")
    c_w1, c_w2 = st.columns([2, 1])
    with c_w1:
        w_in = st.text_input("Add New Ticker").upper().strip()
        if st.button("Add to Watchlist"):
            if w_in:
                sym = w_in + ".NS" if ".NS" not in w_in else w_in
                curr_p = yf.Ticker(sym).fast_info['last_price']
                new_w = pd.DataFrame([{"Symbol": sym, "Added Date": str(datetime.now().date()), "Added Price": curr_p}])
                w_df = pd.concat([w_df, new_w], ignore_index=True)
                w_df.to_csv(WATCHLIST_FILE, index=False); st.rerun()
    with c_w2:
        if st.button("🗑️ Clear"):
            if os.path.exists(WATCHLIST_FILE): os.remove(WATCHLIST_FILE); st.rerun()
    
    st.divider()
    if not w_df.empty:
        for i, row in w_df.iterrows():
            try:
                live_p = yf.Ticker(row['Symbol']).fast_info['last_price']
                chg = ((live_p - row['Added Price']) / row['Added Price']) * 100
                col_w1, col_w2, col_w3 = st.columns([1, 1, 1])
                col_w1.write(f"**{row['Symbol']}** (Added: {row['Added Date']})")
                col_w2.write(f"Price: ₹{live_p:.2f}")
                col_w3.metric("Change %", f"{chg:.2f}%", delta=f"{chg:.2f}%")
                st.divider()
            except: continue
    
