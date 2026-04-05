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
        live_data = yf.download(tickers, period="1d", progress=False)
        if live_data.empty: return df
        for index, row in df.iterrows():
            if row['Status'] == "Holding":
                t_name = row['Name']
                try:
                    new_p = float(live_data['Close'].iloc[-1]) if isinstance(live_data['Close'], pd.Series) else float(live_data['Close'][t_name].iloc[-1])
                    if new_p > 0:
                        df.at[index, 'CMP'] = round(new_p, 2)
                        current_val = round(row['QTY Available'] * new_p, 2)
                        df.at[index, 'CM Value'] = current_val
                        net_pnl = (current_val + row['Dividend']) - row['Investment']
                        df.at[index, 'P&L'] = round(net_pnl, 2)
                        if row['Investment'] > 0:
                            df.at[index, 'P_Percentage'] = round((net_pnl / row['Investment']) * 100, 2)
                except: continue
        df.to_csv(PORTFOLIO_FILE, index=False)
        save_portfolio_history(df[df['Status'] == "Holding"]['CM Value'].sum())
    except: st.sidebar.error("Live Price Sync Failed!")
    return df

# --- ആപ്പ് സെറ്റപ്പ് ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.8", page_icon="📈")
df = load_data()
watch_stocks = get_watchlist()

st.title("📊 Habeeb's Power Hub v6.8")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 1: HEATMAP ---
with tab1:
    st.subheader("Market Visualization")
    show_watch = st.toggle("Include Watchlist in Heatmap", value=False)
    hold_stocks = df[df['Status'] == "Holding"]['Name'].unique().tolist()
    final_tickers = list(set(hold_stocks + watch_stocks)) if show_watch else hold_stocks
    if final_tickers:
        if st.button("🚀 Generate/Refresh Heatmap"):
            with st.spinner("Fetching Data..."):
                m_data = yf.download(final_tickers, period="5d", progress=False)['Close']
                if not m_data.empty:
                    m_changes = ((m_data.iloc[-1] - m_data.iloc[-2]) / m_data.iloc[-2]) * 100
                    m_df = pd.DataFrame({"Symbol": m_changes.index, "Change %": m_changes.values, "Price": m_data.iloc[-1].values})
                    fig = px.treemap(m_df, path=['Symbol'], values='Price', color='Change %', color_continuous_scale='RdYlGn', range_color=[-3, 3])
                    st.plotly_chart(fig, use_container_width=True)
    else: st.info("Add stocks first.")

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
            
            # TradingView ലിങ്ക് ചേർക്കുന്നു
            hold_df['Link'] = hold_df['Name'].apply(lambda x: f"https://www.tradingview.com/symbols/NSE-{x.replace('.NS','')}/")
            st.dataframe(hold_df.style.applymap(lambda v: 'color:green' if v > 0 else 'color:red', subset=['P&L', 'P_Percentage']), use_container_width=True, hide_index=True)

    with st.expander("➕ Add/Remove Stock"):
        c_a, c_b = st.columns(2)
        with c_a:
            n_in = st.text_input("Symbol (eg: SBIN)").upper().strip()
            b_p, q_y = st.number_input("Price", 0.0), st.number_input("Qty", 1)
            if st.button("💾 Save Stock"):
                sym = n_in + ".NS" if ".NS" not in n_in else n_in
                new = {"Category": "Stock", "Buy Date": str(datetime.now().date()), "Name": sym, "CMP": b_p, "Buy Price": b_p, "QTY Available": q_y, "Account": "Habeeb", "Investment": round(q_y*b_p, 2), "CM Value": round(q_y*b_p, 2), "P&L": 0, "P_Percentage": 0, "Status": "Holding"}
                df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()
        with c_b:
            st_rem = st.selectbox("Remove Stock", ["None"] + list(df[df['Status']=='Holding']['Name'].unique()))
            if st.button("🗑️ Confirm Delete") and st_rem != "None":
                df.at[df['Name'] == st_rem, 'Status'] = 'Sold'
                df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()

# --- TAB 3: ANALYTICS ---
with tab3:
    st.subheader("📈 Growth & Distribution")
    if os.path.exists(HISTORY_FILE):
        h_df = pd.read_csv(HISTORY_FILE)
        if len(h_df) > 1:
            st.plotly_chart(px.line(h_df, x='Date', y='Total_Value', title="Portfolio Trend"), use_container_width=True)
    if not df[df['Status'] == "Holding"].empty:
        st.plotly_chart(px.bar(df[df['Status'] == "Holding"], x='Name', y=['Investment', 'CM Value'], barmode='group'), use_container_width=True)

# --- TAB 4: NEWS (WITH MALAYALAM TRANSLATOR) ---
with tab4:
    st.subheader("📰 സ്റ്റോക്ക് വാർത്തകൾ (മലയാളം)")
    if not df.empty:
        n_stock = st.selectbox("വാർത്തകൾ അറിയേണ്ട സ്റ്റോക്ക്:", df['Name'].unique())
        lang_opt = st.radio("ഭാഷ തിരഞ്ഞെടുക്കുക:", ["English", "മലയാളം"], horizontal=True)
        if st.button("Get News"):
            with st.spinner("വാർത്തകൾ ശേഖരിക്കുന്നു..."):
                gn = GoogleNews(lang='en', period='7d')
                gn.search(n_stock.replace(".NS", ""))
                for r in gn.result()[:5]:
                    title = r['title']
                    if lang_opt == "മലയാളം":
                        try: title = GoogleTranslator(source='auto', target='ml').translate(title)
                        except: pass
                    st.write(f"📢 **{title}**")
                    st.write(f"[Read Full Story]({r['link']})")
                    st.divider()

# --- TAB 5: WATCHLIST ---
with tab5:
    st.subheader("👀 Watchlist")
    w_in = st.text_input("Add to Watchlist (eg: RELIANCE)").upper().strip()
    if w_in:
        s = w_in + ".NS" if ".NS" not in w_in else w_in
        if s not in watch_stocks:
            with open(WATCHLIST_FILE, "a") as f: f.write(s + "\n")
            st.rerun()
    if watch_stocks:
        if st.button("🔄 Refresh Prices"):
            w_data = yf.download(watch_stocks, period="2d", progress=False)['Close']
            cols = st.columns(4)
            for i, s in enumerate(watch_stocks):
                cp, pp = w_data[s].iloc[-1], w_data[s].iloc[-2]
                cols[i%4].metric(s, f"₹{cp:.2f}", f"{((cp-pp)/pp)*100:.2f}%")
