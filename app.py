import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os
import time  # പുതുതായി ചേർത്തത്
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
            # ഡ്യൂപ്ലിക്കേറ്റ് ഒഴിവാക്കാൻ സെറ്റ് ഉപയോഗിക്കുന്നു
            return sorted(list(set([line.strip() for line in f.readlines() if line.strip()])))
    return []

def update_live_prices(df):
    tickers = df[df['Status'] == "Holding"]['Name'].unique().tolist()
    if not tickers: return df
    try:
        # Tickers ലിസ്റ്റ് ശരിയാണെന്ന് ഉറപ്പുവരുത്തുക
        live_data = yf.download(tickers, period="5d", progress=False)['Close']
        if live_data.empty: return df
        
        for index, row in df.iterrows():
            if row['Status'] == "Holding":
                t_name = row['Name']
                try:
                    # സിംഗിൾ ടിക്കർ ആണെങ്കിൽ ഡാറ്റാഫ്രെയിം സ്ട്രക്ചർ മാറും, അത് ഹാൻഡിൽ ചെയ്യുന്നു
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

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 1: HEATMAP ---
with tab1:
    hold_stocks_df = df[df['Status'] == "Holding"].copy()
    if not hold_stocks_df.empty:
        fig = px.treemap(hold_stocks_df, path=['Name'], values='Investment', color='P_Percentage', 
                         color_continuous_scale='RdYlGn', range_color=[-5, 5])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ഹീറ്റ്‌മാപ്പ് കാണുന്നതിനായി സ്റ്റോക്കുകൾ ആഡ് ചെയ്യുക.")

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

            def style_pnl(val):
                return 'color: green' if val > 0 else 'color: red' if val < 0 else ''

            if view_mode == "Summary View":
                # അക്കൗണ്ട് കൂടി ഗ്രൂപ്പിംഗിൽ ഉൾപ്പെടുത്തി
                summ_df = hold_df.groupby(['Name', 'Account']).agg({'Investment':'sum', 'CM Value':'sum', 'P&L':'sum', 'Today_PnL':'sum'}).reset_index()
                summ_df['Weight %'] = ((summ_df['Investment'] / t_inv) * 100).round(1) if t_inv > 0 else 0
                for c in ['Investment', 'CM Value', 'P&L', 'Today_PnL']: summ_df[c] = summ_df[c].astype(int)
                st.dataframe(summ_df.style.map(style_pnl, subset=['P&L', 'Today_PnL']), use_container_width=True, hide_index=True)
            else:
                det_df = hold_df.copy()
                for c in ["CMP", "Buy Price", "Investment", "CM Value", "P&L", "Today_PnL"]: det_df[c] = det_df[c].astype(int)
                st.dataframe(det_df.style.map(style_pnl, subset=['P&L', 'Today_PnL']), use_container_width=True, hide_index=True)

            st.divider()
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button("📥 Download Portfolio CSV", df.to_csv(index=False).encode('utf-8'), "portfolio_backup.csv", "text/csv")
            with col_d2:
                up_p = st.file_uploader("📤 Upload Portfolio CSV", type=["csv"])
                if up_p and st.button("Confirm Restore"):
                    pd.read_csv(up_p).to_csv(PORTFOLIO_FILE, index=False); st.rerun()

    with st.expander("➕ Add/Remove/Update Stock"):
        c_a, c_b = st.columns(2)
        with c_a:
            st.write("### Add Stock")
            b_date = st.date_input("Date", datetime.now())
            n_in = st.selectbox("Symbol", nifty500_list)
            b_p = st.number_input("Buy Price", min_value=0.1)
            q_y = st.number_input("Qty", min_value=1)
            tax_in = st.number_input("Tax", 0.0)
            acc_in = st.selectbox("Account", ["Habeeb", "RISU"])
            if st.button("💾 Save Stock"):
                sym = n_in + ".NS" if ".NS" not in n_in else n_in
                new = {"Category": "Equity", "Buy Date": str(b_date), "Name": sym, "CMP": b_p, "Buy Price": b_p, "QTY Available": q_y, "Account": acc_in, "Investment": round(q_y*b_p, 2), "CM Value": round(q_y*b_p, 2), "P&L": 0, "P_Percentage": 0, "Status": "Holding", "Tax": tax_in, "Dividend": 0, "Today_PnL": 0}
                df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False); st.success("Saved!"); st.rerun()
        with c_b:
            st.write("### Manage Stock")
            h_list = list(df[df['Status']=='Holding']['Name'].unique())
            st_m = st.selectbox("Select Stock", ["None"] + h_list)
            if st_m != "None":
                if st.button("🗑️ Mark as Sold"):
                    # ഒരേ പേരിൽ ഒന്നിലധികം എൻട്രി ഉണ്ടെങ്കിൽ അത് കൺട്രോൾ ചെയ്യാൻ ഇൻഡക്സ് ഉപയോഗിക്കുന്നതാണ് നല്ലത്
                    df.loc[df['Name'] == st_m, 'Status'] = 'Sold'
                    df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()
                div_val = st.number_input("Add Dividend", min_value=0.0)
                if st.button("➕ Update Dividend"):
                    df.loc[df['Name'] == st_m, 'Dividend'] += div_val
                    df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()

# --- TAB 3: ANALYTICS ---
with tab3:
    if not hold_stocks_df.empty:
        col_an1, col_an2 = st.columns(2)
        with col_an1:
            st.plotly_chart(px.pie(hold_stocks_df, values='Investment', names='Account', title='Account Distribution', hole=0.4), use_container_width=True)
        with col_an2:
            st.plotly_chart(px.bar(hold_stocks_df, x='Name', y='P&L', color='P&L', title='Stock-wise P&L'), use_container_width=True)

# --- TAB 4: NEWS ---
with tab4:
    n_stock = st.selectbox("Select Stock for News:", ["None"] + list(df['Name'].unique()))
    if n_stock != "None" and st.button("Get News"):
        with st.spinner("വാർത്തകൾ തിരയുന്നു..."):
            try:
                gn = GoogleNews(lang='en', period='7d')
                gn.search(n_stock.replace(".NS", ""))
                time.sleep(1) # ചെറിയ ഡിലേ നൽകുന്നു
                results = gn.result()
                if results:
                    translator = GoogleTranslator(source='en', target='ml')
                    for r in results[:5]:
                        st.write(f"📢 **{r['title']}**")
                        with st.expander("മലയാളത്തിൽ വായിക്കാം"):
                            try:
                                st.write(translator.translate(r['title']))
                            except: st.write("പരിഭാഷ ലഭ്യമായില്ല.")
                        st.caption(f"{r['date']} | [Read More]({r['link']})")
                        st.divider()
                else: st.info("വാർത്തകൾ ഒന്നും ലഭ്യമല്ല.")
            except Exception as e: st.error(f"Error: {e}")

# --- TAB 5: WATCHLIST ---
with tab5:
    st.subheader("👀 My Watchlist")
    win = st.text_input("Add Symbol (eg: SBIN)").upper().strip()
    if st.button("Add to Watchlist") and win:
        ticker = win + ".NS" if ".NS" not in win else win
        with open(WATCHLIST_FILE, "a") as f: f.write(ticker + "\n")
        st.success(f"{ticker} ചേർത്തു!")
        st.rerun()
    
    st.divider()
    if watch_stocks:
        for s in watch_stocks:
            wc1, wc2 = st.columns([4, 1])
            wc1.write(f"📈 **{s}**")
            if wc2.button("Remove", key=f"del_{s}"):
                updated = [item for item in watch_stocks if item != s]
                with open(WATCHLIST_FILE, "w") as f:
                    for item in updated: f.write(item + "\n")
                st.rerun()
