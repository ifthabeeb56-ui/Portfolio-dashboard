import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os
from GoogleNews import GoogleNews
from deep_translator import GoogleTranslator

# --- 1. ഫയൽ സെറ്റിംഗ്സ് (ബാക്കപ്പ് ഡാറ്റ ലോഡ് ചെയ്യാൻ ഇത് സഹായിക്കും) ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"
HISTORY_FILE = "portfolio_history.csv"

def load_data():
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        # പഴയ ഡാറ്റയും പുതിയ ഫീച്ചറുകളും തമ്മിലുള്ള പൊരുത്തക്കേട് ഒഴിവാക്കുന്നു
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage", "Dividend", "Tax", "Sell_Price"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0.0
        
        # അത്യാവശ്യം വേണ്ട കോളങ്ങൾ ഇല്ലെങ്കിൽ അവ ചേർക്കുന്നു
        if 'Status' not in df.columns: df['Status'] = 'Holding'
        if 'Account' not in df.columns: df['Account'] = 'Habeeb'
        if 'Name' not in df.columns: return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "Status"])
        return df
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Remark", "Status", "Sell_Price"])

def get_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            return sorted(list(set([line.strip() for line in f.readlines() if line.strip()])))
    return []

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
        background-color: #ffffff; border: 1px solid #dee2e6;
        padding: 10px 25px; border-radius: 5px; color: #263c5c; font-weight: bold;
    }
    div.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #263c5c !important; color: white !important; border: none;
    }
    [data-testid="stMetric"] {
        background-color: white; padding: 15px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #263c5c;
    }
    h1, h2, h3 { color: #263c5c !important; }
</style>
""", unsafe_allow_html=True)

df = load_data()
watch_stocks = get_watchlist()
nifty500_list = get_nifty500_tickers()

st.title("📊 Habeeb's Power Hub v6.9")
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
        try:
            m_data = yf.download(final_tickers, period="5d", progress=False)['Close']
            if not m_data.empty and len(m_data) > 1:
                m_changes = ((m_data.iloc[-1] - m_data.iloc[-2]) / m_data.iloc[-2]) * 100
                m_df = pd.DataFrame({"Symbol": m_changes.index, "Change %": m_changes.values})
                m_df = m_df.merge(hold_stocks_df[['Name', 'Investment']], left_on='Symbol', right_on='Name', how='left')
                m_df['Investment'] = m_df['Investment'].fillna(1000) 
                m_df['Size_Value'] = m_df['Change %'].abs() + 0.1 if size_option == "Daily % Change" else m_df['Investment']

                fig = px.treemap(m_df, path=['Symbol'], values='Size_Value', color='Change %', 
                                 color_continuous_scale='RdYlGn', range_color=[-3, 3],
                                 title="Market Overview")
                fig.update_traces(texttemplate="<b>%{label}</b><br>%{color:.2f}%")
                st.plotly_chart(fig, use_container_width=True)
        except: st.info("ലൈവ് ഡാറ്റ ലഭിക്കാൻ പേജ് റീഫ്രഷ് ചെയ്യുക.")

# --- TAB 2: PORTFOLIO ---
with tab2:
    hold_df = df[df['Status'] == "Holding"].copy()
    if not hold_df.empty:
        tickers = hold_df['Name'].tolist()
        live_data = yf.download(tickers, period="2d", progress=False)['Close']
        today_pnl_total = 0
        for index, row in hold_df.iterrows():
            try:
                if len(tickers) == 1:
                    curr, prev = live_data.iloc[-1], live_data.iloc[-2]
                else:
                    curr, prev = live_data[row['Name']].iloc[-1], live_data[row['Name']].iloc[-2]
                
                today_pnl_total += (curr - prev) * row['QTY Available']
                hold_df.at[index, 'CMP'] = curr
                hold_df.at[index, 'CM Value'] = curr * row['QTY Available']
                hold_df.at[index, 'P&L'] = (curr * row['QTY Available']) - row['Investment']
            except: pass

        t_inv, t_val = int(hold_df['Investment'].sum()), int(hold_df['CM Value'].sum())
        t_pnl = t_val - t_inv
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Investment", f"₹{t_inv:,}")
        c2.metric("Current Value", f"₹{t_val:,}")
        c3.metric("Total P&L", f"₹{int(t_pnl):,}", f"{((t_pnl/t_inv)*100 if t_inv > 0 else 0):.2f}%")
        c4.metric("Today's P&L", f"₹{int(today_pnl_total):,}", f"{((today_pnl_total/t_inv)*100 if t_inv > 0 else 0):.2f}%")

        disp_df = hold_df[['Category', 'Buy Date', 'Name', 'CMP', 'Buy Price', 'QTY Available', 'Account', 'Investment', 'CM Value', 'P&L']].copy()
        for col in ['CMP', 'Buy Price', 'Investment', 'CM Value', 'P&L']:
            disp_df[col] = disp_df[col].apply(lambda x: int(round(x)))
        st.dataframe(disp_df, use_container_width=True, hide_index=True)

    edit_mode = st.toggle("🛠️ Manage Portfolio (Add/Sell)")
    if edit_mode:
        col_add, col_sell = st.columns(2)
        with col_add:
            st.subheader("➕ Add Stock")
            with st.form("add_form", clear_on_submit=True):
                f_cat = st.selectbox("Category", ["Stock", "ETF", "Mutual Fund"])
                f_date = st.date_input("Date", datetime.now())
                f_name = st.selectbox("Symbol", ["Custom"] + nifty500_list)
                if f_name == "Custom": f_name = st.text_input("Enter Symbol").upper().strip()
                f_price = st.number_input("Price", min_value=0.0)
                f_qty = st.number_input("Qty", min_value=1)
                f_acc = st.selectbox("Account", ["Habeeb", "RISU"])
                if st.form_submit_button("Add"):
                    sym = f_name if ".NS" in f_name else f_name + ".NS"
                    new_row = {"Category": f_cat, "Buy Date": str(f_date), "Name": sym, "Buy Price": f_price, "QTY Available": f_qty, "Account": f_acc, "Investment": f_price * f_qty, "Status": "Holding"}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()

        with col_sell:
            st.subheader("💰 Sell Stock")
            s_stock = st.selectbox("Select", ["None"] + (hold_df['Name'].tolist() if not hold_df.empty else []))
            if s_stock != "None":
                s_price = st.number_input("Sell Price", value=0.0)
                if st.button("Confirm Sale"):
                    df.loc[df['Name'] == s_stock, 'Status'] = 'Sold'
                    df.loc[df['Name'] == s_stock, 'Sell_Price'] = s_price
                    df.to_csv(PORTFOLIO_FILE, index=False); st.success("Sold!"); st.rerun()

# --- TAB 3: ANALYTICS ---
with tab3:
    if not hold_df.empty:
        col_a1, col_a2 = st.columns(2)
        with col_a1: st.plotly_chart(px.pie(hold_df, values='Investment', names='Category', title='Category Distribution', hole=0.4), use_container_width=True)
        with col_a2: st.plotly_chart(px.pie(hold_df, values='Investment', names='Account', title='Account Distribution', hole=0.4), use_container_width=True)
    if os.path.exists(HISTORY_FILE):
        h_df = pd.read_csv(HISTORY_FILE)
        st.plotly_chart(px.line(h_df, x='Date', y='Total_Value', title="Portfolio Trend"), use_container_width=True)

# --- TAB 4: NEWS ---
with tab4:
    st.subheader("📰 Market News")
    n_stock = st.selectbox("News for:", ["None"] + list(df['Name'].unique()))
    if n_stock != "None":
        lang = st.radio("Language:", ["English", "മലയാളം"], horizontal=True)
        if st.button("Get News"):
            gn = GoogleNews(lang='en', period='7d')
            gn.search(n_stock.replace(".NS", ""))
            for r in gn.result()[:5]:
                title = r['title']
                if lang == "മലയാളം": title = GoogleTranslator(source='auto', target='ml').translate(title)
                st.write(f"📢 **{title}**")
                st.caption(f"Source: {r['date']} | [Read More]({r['link']})")
                st.divider()

# --- TAB 5: WATCHLIST ---
with tab5:
    st.subheader("👀 Watchlist")
    w_in = st.text_input("Add Ticker").upper().strip()
    if st.button("Add to Watchlist"):
        with open(WATCHLIST_FILE, "a") as f: f.write((w_in if ".NS" in w_in else w_in + ".NS") + "\n")
        st.rerun()
    if watch_stocks:
        if st.button("Refresh Watchlist"):
            w_data = yf.download(watch_stocks, period="2d", progress=False)['Close']
            cols = st.columns(4)
            for i, s in enumerate(watch_stocks):
                try:
                    cp, pp = float(w_data[s].iloc[-1]), float(w_data[s].iloc[-2])
                    cols[i%4].metric(s, f"₹{cp:.2f}", f"{((cp-pp)/pp)*100:.2f}%")
                except: continue
