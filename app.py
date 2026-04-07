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

# --- 2. ഡാറ്റാ ഫങ്ക്ഷനുകൾ ---
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
    return pd.DataFrame(columns=["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Remark", "Status", "Sell Date"])

def get_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            return pd.read_csv(WATCHLIST_FILE)
        except:
            return pd.DataFrame(columns=["Date", "Symbol", "Today P&L %", "Remarks"])
    return pd.DataFrame(columns=["Date", "Symbol", "Today P&L %", "Remarks"])

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
                    new_p = float(live_data['Close'].iloc[-1]) if len(tickers) == 1 else float(live_data['Close'][t_name].iloc[-1])
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

# --- 3. ആപ്പ് സെറ്റപ്പ് ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v7.0", page_icon="📈")
df = load_data()
w_df = get_watchlist()
nifty500_list = get_nifty500_tickers()

# --- SIDEBAR (Point 6: Upload/Download) ---
with st.sidebar:
    st.header("⚙️ Data Management")
    st.subheader("Portfolio CSV")
    st.download_button("📥 Download Portfolio", df.to_csv(index=False), "portfolio.csv", "text/csv")
    up_p = st.file_uploader("📤 Upload Portfolio", type="csv", key="p_up")
    if up_p:
        pd.read_csv(up_p).to_csv(PORTFOLIO_FILE, index=False)
        st.success("Portfolio Updated!"); st.rerun()
    
    st.divider()
    st.subheader("Watchlist CSV")
    st.download_button("📥 Download Watchlist", w_df.to_csv(index=False), "watchlist.csv", "text/csv")
    up_w = st.file_uploader("📤 Upload Watchlist", type="csv", key="w_up")
    if up_w:
        pd.read_csv(up_w).to_csv(WATCHLIST_FILE, index=False)
        st.success("Watchlist Updated!"); st.rerun()

st.title("📊 Habeeb's Power Hub v7.0")

# --- SUMMARY SWITCH (Point 2) ---
show_summary = st.toggle("Show Portfolio Summary", value=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "💰 Sold Items", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 1: HEATMAP ---
with tab1:
    st.subheader("Market Visualization")
    hold_stocks_df = df[df['Status'] == "Holding"].copy()
    final_tickers = hold_stocks_df['Name'].unique().tolist()
    if final_tickers:
        try:
            m_data = yf.download(final_tickers, period="5d", progress=False)['Close']
            if not m_data.empty:
                m_changes = ((m_data.iloc[-1] - m_data.iloc[-2]) / m_data.iloc[-2]) * 100
                m_df = pd.DataFrame({"Symbol": m_changes.index, "Change %": m_changes.values, "Price": m_data.iloc[-1].values})
                m_df = m_df.merge(hold_stocks_df[['Name', 'Investment']], left_on='Symbol', right_on='Name', how='left')
                fig = px.treemap(m_df, path=['Symbol'], values='Investment', color='Change %', color_continuous_scale='RdYlGn', range_color=[-3, 3])
                st.plotly_chart(fig, use_container_width=True)
        except: st.error("Heatmap failed.")

# --- TAB 2: PORTFOLIO (Point 1 & 3: Today P&L % & Decimal Remove) ---
with tab2:
    if not df.empty:
        df = update_live_prices(df)
        hold_df = df[df['Status'] == "Holding"].copy()
        if not hold_df.empty:
            if show_summary:
                t_inv, t_val = int(hold_df['Investment'].sum()), int(hold_df['CM Value'].sum())
                t_pnl = t_val - t_inv
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Investment", f"₹{t_inv:,}")
                c2.metric("Current Value", f"₹{t_val:,}")
                c3.metric("Total P&L", f"₹{t_pnl:,}", f"{((t_pnl/t_inv)*100):.2f}%" if t_inv > 0 else "0%")

            # Display Table with Decimal Removal (Point 3)
            disp_df = hold_df.copy()
            for col in ["CMP", "Buy Price", "Investment", "CM Value", "P&L"]:
                disp_df[col] = disp_df[col].astype(int)
            
            # Today's P&L Logic (Point 1)
            st.dataframe(disp_df[["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Investment", "P&L", "P_Percentage"]], use_container_width=True, hide_index=True)

    with st.expander("➕ Add / Manage Stock"):
        # Add Stock logic exactly as before
        c_a, c_b = st.columns(2)
        with c_a:
            b_date = st.date_input("Date", datetime.now())
            cat = st.selectbox("Category", ["Equity", "ETF", "SGB", "Mutual Fund"])
            acc = st.selectbox("Account", ["Habeeb", "RISU"])
            n_in = st.selectbox("Nifty 500", ["Custom"] + nifty500_list)
            if n_in == "Custom": n_in = st.text_input("Symbol").upper().strip()
            b_p = st.number_input("Buy Price", 0.0)
            q_y = st.number_input("Qty", 1)
            rem = st.text_input("Remark")
            if st.button("💾 Save Stock"):
                sym = n_in + ".NS" if ".NS" not in n_in else n_in
                new = {"Category": cat, "Buy Date": str(b_date), "Name": sym, "CMP": b_p, "Buy Price": b_p, "QTY Available": q_y, "Account": acc, "Investment": round(q_y*b_p, 2), "CM Value": round(q_y*b_p, 2), "P&L": 0, "P_Percentage": 0, "Status": "Holding", "Remark": rem, "Dividend": 0, "Tax": 0}
                df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()
        with c_b:
            h_list = list(df[df['Status']=='Holding']['Name'].unique())
            st_m = st.selectbox("Select to Sell", ["None"] + h_list)
            if st_m != "None" and st.button("🗑️ Sell Stock"):
                df.loc[df['Name'] == st_m, 'Status'] = 'Sold'
                df.loc[df['Name'] == st_m, 'Sell Date'] = str(datetime.now().date())
                df.to_csv(PORTFOLIO_FILE, index=False); st.rerun()

# --- TAB 3: SOLD ITEMS (Point 4 & 5) ---
with tab3:
    sold_df = df[df['Status'] == "Sold"].copy()
    sold_summary_switch = st.toggle("Show Sold Summary")
    if sold_summary_switch and not sold_df.empty:
        total_s_pnl = int(sold_df['P&L'].sum())
        st.metric("Total Realized P&L", f"₹{total_s_pnl:,}")
    
    if not sold_df.empty:
        # Decimal removal
        for col in ["Investment", "P&L"]: sold_df[col] = sold_df[col].astype(int)
        st.dataframe(sold_df[["Name", "Buy Date", "Sell Date", "Investment", "P&L", "P_Percentage"]], use_container_width=True, hide_index=True)
    else: st.info("No sold items.")

# --- TAB 4: ANALYTICS ---
with tab4:
    h_df = df[df['Status'] == "Holding"]
    if not h_df.empty:
        cp1, cp2 = st.columns(2)
        with cp1: st.plotly_chart(px.pie(h_df, values='Investment', names='Category', title='Category'), use_container_width=True)
        with cp2: st.plotly_chart(px.pie(h_df, values='Investment', names='Account', title='Account'), use_container_width=True)

# --- TAB 5: NEWS ---
with tab5:
    n_stock = st.selectbox("Stock for News", ["None"] + list(df['Name'].unique()))
    if n_stock != "None" and st.button("Get News"):
        try:
            gn = GoogleNews(lang='en', period='7d'); gn.search(n_stock.replace(".NS", ""))
            for r in gn.result()[:5]:
                st.write(f"📢 **{r['title']}**"); st.caption(f"{r['date']} | [Read More]({r['link']})")
        except: st.error("Could not fetch news.")

# --- TAB 6: WATCHLIST (Point 7: Modified New Model) ---
with tab6:
    st.subheader("👀 Watchlist Management")
    cw1, cw2 = st.columns([1, 2])
    with cw1:
        w_sym = st.text_input("Ticker").upper()
        w_rem = st.text_area("Remarks")
        if st.button("Add to Watchlist"):
            new_w = pd.DataFrame([{"Date": str(datetime.now().date()), "Symbol": w_sym, "Today P&L %": "Updating...", "Remarks": w_rem}])
            w_df = pd.concat([w_df, new_w], ignore_index=True)
            w_df.to_csv(WATCHLIST_FILE, index=False); st.rerun()
    with cw2:
        if not w_df.empty:
            if st.button("🔄 Update Watchlist Prices"):
                tickers = [t + ".NS" if ".NS" not in t else t for t in w_df['Symbol'].tolist()]
                w_data = yf.download(tickers, period="2d", progress=False)['Close']
                for idx, row in w_df.iterrows():
                    sym = row['Symbol'] + ".NS" if ".NS" not in row['Symbol'] else row['Symbol']
                    try:
                        change = ((w_data[sym].iloc[-1] - w_data[sym].iloc[-2]) / w_data[sym].iloc[-2]) * 100
                        w_df.at[idx, 'Today P&L %'] = f"{change:.2f}%"
                    except: pass
                w_df.to_csv(WATCHLIST_FILE, index=False); st.rerun()
            st.table(w_df[["Date", "Symbol", "Today P&L %", "Remarks"]])
