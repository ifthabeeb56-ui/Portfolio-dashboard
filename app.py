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
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage", "Dividend", "Tax"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Remark", "Status"])

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
        live_data = yf.download(tickers, period="5d", progress=False)
        if live_data.empty: return df
        
        for index, row in df.iterrows():
            if row['Status'] == "Holding":
                t_name = row['Name']
                try:
                    if len(tickers) == 1:
                        new_p = float(live_data['Close'].iloc[-1])
                    else:
                        new_p = float(live_data['Close'][t_name].iloc[-1])
                        
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
watch_stocks = get_watchlist()
nifty500_list = get_nifty500_tickers()

st.title("📊 Habeeb's Power Hub v6.8")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 1: HEATMAP ---
with tab1:
    st.subheader("Market Visualization Settings")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        size_option = st.radio("Box Size based on:", ["Investment", "Daily % Change"], horizontal=True)
    with col_s2:
        show_watch = st.toggle("Include Watchlist in Heatmap", value=False)
    
    hold_stocks_df = df[df['Status'] == "Holding"].copy()
    hold_stocks = hold_stocks_df['Name'].unique().tolist()
    final_tickers = list(set(hold_stocks + watch_stocks)) if show_watch else hold_stocks

    if final_tickers:
        with st.spinner("Fetching Heatmap Data..."):
            try:
                m_data = yf.download(final_tickers, period="5d", progress=False)['Close']
                if not m_data.empty and len(m_data) > 1:
                    m_changes = ((m_data.iloc[-1] - m_data.iloc[-2]) / m_data.iloc[-2]) * 100
                    m_df = pd.DataFrame({"Symbol": m_changes.index, "Change %": m_changes.values, "Price": m_data.iloc[-1].values})
                    m_df = m_df.merge(hold_stocks_df[['Name', 'Investment']], left_on='Symbol', right_on='Name', how='left')
                    m_df['Investment'] = m_df['Investment'].fillna(1000) 
                    m_df['Size_Value'] = m_df['Change %'].abs() + 0.1 if size_option == "Daily % Change" else m_df['Investment']
                    fig = px.treemap(m_df, path=['Symbol'], values='Size_Value', color='Change %', color_continuous_scale='RdYlGn', range_color=[-3, 3], hover_data={'Price': ': .2f', 'Change %': ': .2f%', 'Investment': ': .2f'})
                    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=550)
                    fig.update_traces(textinfo="label+text", texttemplate="<b>%{label}</b><br>%{color:.2f}%", textfont=dict(size=20))
                    fig.update_layout(uniformtext=dict(minsize=10, mode='hide'))
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e: st.error(f"Heatmap കാണിക്കാൻ കഴിഞ്ഞില്ല: {e}")
    else: st.info("Heatmap കാണുന്നതിനായി സ്റ്റോക്കുകൾ ആഡ് ചെയ്യുക.")

# --- TAB 2: PORTFOLIO ---
with tab2:
    if not df.empty:
        df = update_live_prices(df)
        hold_df = df[df['Status'] == "Holding"].copy()
        if not hold_df.empty:
            t_inv, t_val, t_pnl = hold_df['Investment'].sum(), hold_df['CM Value'].sum(), hold_df['P&L'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Investment", f"₹{t_inv:,.2f}")
            c2.metric("Current Value", f"₹{t_val:,.2f}")
            c3.metric("Total P&L", f"₹{t_pnl:,.2f}", f"{((t_pnl/t_inv)*100):.2f}%" if t_inv > 0 else "0%")
            st.dataframe(hold_df.style.map(lambda v: 'color:green' if (isinstance(v, (int, float)) and v > 0) else 'color:red' if (isinstance(v, (int, float)) and v < 0) else '', subset=['P&L', 'P_Percentage']), use_container_width=True, hide_index=True)

            # Portfolio Download/Upload
            st.divider()
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                csv_p = df.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Download Portfolio CSV", data=csv_p, file_name=f'portfolio_backup_{datetime.now().strftime("%Y%m%d")}.csv', mime='text/csv')
            with col_d2:
                up_p = st.file_uploader("📤 Upload Portfolio CSV", type=["csv"], key="port_up")
                if up_p is not None:
                    if st.button("Confirm Portfolio Restore"):
                        pd.read_csv(up_p).to_csv(PORTFOLIO_FILE, index=False)
                        st.success("Portfolio Updated!"); st.rerun()

    with st.expander("➕ Add/Remove/Update Stock"):
        c_a, c_b = st.columns(2)
        with c_a:
            st.write("### Add New Stock")
            b_date = st.date_input("Purchase Date", datetime.now())
            cat = st.selectbox("Category", ["Equity", "ETF", "SGB", "Mutual Fund"])
            acc = st.selectbox("Account", ["Habeeb", "RISU"])
            n_in = st.selectbox("Select Symbol from Nifty 500", ["Custom"] + nifty500_list)
            if n_in == "Custom": n_in = st.text_input("Enter Symbol").upper().strip()
            
            auto_p = 0.0
            if n_in != "Custom" and n_in != "" and st.button(f"Get Price for {n_in}"):
                try: auto_p = yf.Ticker(n_in + ".NS").fast_info['last_price']
                except: st.error("വില കിട്ടിയില്ല")

            b_p = st.number_input("Buy Price", value=float(auto_p), step=0.01)
            q_y = st.number_input("Qty", min_value=1, value=1)
            tax_in = st.number_input("Tax", 0.0, step=0.01)
            remark = st.text_input("Remark")
            
            if st.button("💾 Save Stock") and n_in != "":
                sym = n_in + ".NS" if ".NS" not in n_in else n_in
                new = {"Category": cat, "Buy Date": str(b_date), "Name": sym, "CMP": b_p, "Buy Price": b_p, "QTY Available": q_y, "Account": acc, "Investment": round(q_y*b_p, 2), "CM Value": round(q_y*b_p, 2), "P&L": 0, "P_Percentage": 0, "Status": "Holding", "Remark": remark, "Dividend": 0, "Tax": tax_in}
                df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False); st.success("Saved!"); st.rerun()
        
        with c_b:
            st.write("### Manage Existing")
            h_list = list(df[df['Status']=='Holding']['Name'].unique())
            st_m = st.selectbox("Select Stock", ["None"] + h_list)
            if st_m != "None":
                div = st.number_input("Add Dividend", 0.0)
                if st.button("➕ Update Div"):
                    df.loc[df['Name'] == st_m, 'Dividend'] += div
                    df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()
                if st.button("🗑️ Sell / Remove"):
                    df.loc[df['Name'] == st_m, 'Status'] = 'Sold'
                    df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()

# --- TAB 3: ANALYTICS ---
with tab3:
    st.subheader("📈 Distribution")
    h_df = df[df['Status'] == "Holding"]
    if not h_df.empty:
        cp1, cp2 = st.columns(2)
        with cp1: st.plotly_chart(px.pie(h_df, values='Investment', names='Category', title='Category', hole=0.4), use_container_width=True)
        with cp2: st.plotly_chart(px.pie(h_df, values='Investment', names='Account', title='Account', hole=0.4), use_container_width=True)
    if os.path.exists(HISTORY_FILE):
        st.plotly_chart(px.line(pd.read_csv(HISTORY_FILE), x='Date', y='Total_Value', title="Trend", markers=True), use_container_width=True)

# --- TAB 4: NEWS ---
with tab4:
    st.subheader("📰 വാർത്തകൾ")
    if not df.empty:
        n_stock = st.selectbox("സ്റ്റോക്ക് സെലക്ട് ചെയ്യുക:", ["None"] + list(df['Name'].unique()))
        if n_stock != "None":
            lang = st.radio("ഭാഷ:", ["English", "മലയാളം"], horizontal=True)
            if st.button("Get News"):
                try:
                    gn = GoogleNews(lang='en', period='7d'); gn.search(n_stock.replace(".NS", ""))
                    for r in gn.result()[:5]:
                        t = GoogleTranslator(source='auto', target='ml').translate(r['title']) if lang == "മലയാളം" else r['title']
                        st.write(f"📢 **{t}**"); st.caption(f"{r['date']} | [Read More]({r['link']})"); st.divider()
                except: st.error("വാർത്തകൾ കിട്ടിയില്ല")

# --- TAB 5: WATCHLIST ---
with tab5:
    st.subheader("👀 Watchlist Management")
    cw1, cw2 = st.columns([2, 1])
    with cw1:
        win = st.text_input("Add Ticker (eg: RELIANCE)").upper().strip()
        if st.button("Add to Watchlist") and win:
            s = win + ".NS" if ".NS" not in win else win
            if s not in watch_stocks:
                with open(WATCHLIST_FILE, "a") as f: f.write(s + "\n")
                st.rerun()
    with cw2:
        if st.button("🗑️ Clear Watchlist") and os.path.exists(WATCHLIST_FILE):
            os.remove(WATCHLIST_FILE); st.rerun()
    
    # Watchlist Download/Upload
    st.divider()
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        if watch_stocks:
            w_text = "\n".join(watch_stocks)
            st.download_button(label="📥 Download Watchlist TXT", data=w_text, file_name="watchlist_backup.txt", mime="text/plain")
    with col_w2:
        up_w = st.file_uploader("📤 Upload Watchlist TXT", type=["txt"], key="watch_up")
        if up_w is not None:
            if st.button("Confirm Watchlist Restore"):
                with open(WATCHLIST_FILE, "wb") as f: f.write(up_w.getvalue())
                st.success("Watchlist Updated!"); st.rerun()

    st.divider()
    if watch_stocks and st.button("🔄 Refresh Watchlist Prices"):
        try:
            wd = yf.download(watch_stocks, period="2d", progress=False)['Close']
            cols = st.columns(4)
            for i, s in enumerate(watch_stocks):
                try:
                    cp, pp = (float(wd.iloc[-1]), float(wd.iloc[-2])) if len(watch_stocks) == 1 else (float(wd[s].iloc[-1]), float(wd[s].iloc[-2]))
                    cols[i%4].metric(s, f"₹{cp:.2f}", f"{((cp-pp)/pp*100):.2f}%")
                except: continue
        except: st.error("വില കിട്ടിയില്ല")
