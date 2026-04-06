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
    cols = ["Category", "Buy Date", "Sell Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Remark", "Status"]
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        # പഴയ ഫയലിൽ Sell Date ഇല്ലെങ്കിൽ അത് ചേർക്കുന്നു
        if "Sell Date" not in df.columns:
            df["Sell Date"] = ""
        
        num_cols = ["CMP", "Buy Price", "QTY Available", "Investment", "CM Value", "P&L", "P_Percentage", "Dividend", "Tax"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=cols)

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
    if not h_df.empty and today in h_df['Date'].values:
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
                    # സിംഗിൾ ടിക്കർ ആണെങ്കിൽ ഡാറ്റ എടുക്കുന്ന രീതി
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
                    if len(final_tickers) == 1:
                        m_changes = pd.Series([(m_data.iloc[-1] - m_data.iloc[-2]) / m_data.iloc[-2] * 100], index=final_tickers)
                    else:
                        m_changes = ((m_data.iloc[-1] - m_data.iloc[-2]) / m_data.iloc[-2]) * 100
                    
                    m_df = pd.DataFrame({"Symbol": m_changes.index, "Change %": m_changes.values})
                    m_df = m_df.merge(hold_stocks_df[['Name', 'Investment']], left_on='Symbol', right_on='Name', how='left')
                    m_df['Investment'] = m_df['Investment'].fillna(1000) 
                    m_df['Size_Value'] = m_df['Change %'].abs() + 0.1 if size_option == "Daily % Change" else m_df['Investment']
                    
                    fig = px.treemap(m_df, path=['Symbol'], values='Size_Value', color='Change %', color_continuous_scale='RdYlGn', range_color=[-3, 3])
                    fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=550)
                    fig.update_traces(textinfo="label+text", texttemplate="<b>%{label}</b><br>%{color:.2f}%")
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e: st.error(f"Heatmap Error: {e}")
    else: st.info("സ്റ്റോക്കുകൾ ആഡ് ചെയ്യുക.")

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
            
            # --- QTY ഡെസിമൽ ഒഴിവാക്കി ---
            disp_df = hold_df.copy()
            disp_df['QTY Available'] = disp_df['QTY Available'].astype(int)
            
            st.dataframe(disp_df.style.map(lambda v: 'color:green' if (isinstance(v, (int, float)) and v > 0) else 'color:red' if (isinstance(v, (int, float)) and v < 0) else '', subset=['P&L', 'P_Percentage']), use_container_width=True, hide_index=True)

    # വിറ്റ സ്റ്റോക്കുകളുടെ ചരിത്രം
    with st.expander("📂 View Sold Stocks (History)"):
        sold_df = df[df['Status'] == "Sold"].copy()
        if not sold_df.empty:
            sold_df['QTY Available'] = sold_df['QTY Available'].astype(int)
            st.write("### വിറ്റ സ്റ്റോക്കുകൾ")
            st.dataframe(sold_df[['Name', 'Buy Date', 'Sell Date', 'QTY Available', 'Investment', 'P&L', 'P_Percentage']], use_container_width=True, hide_index=True)
        else:
            st.info("വിൽപന വിവരങ്ങൾ ലഭ്യമല്ല.")

    with st.expander("➕ Add/Remove/Update Stock"):
        c_a, c_b = st.columns(2)
        with c_a:
            st.write("### Add New Stock")
            b_date = st.date_input("Purchase Date", datetime.now())
            cat = st.selectbox("Category", ["Equity", "ETF", "SGB", "Mutual Fund"])
            acc = st.selectbox("Account", ["Habeeb", "RISU"])
            n_in = st.selectbox("Select Symbol from Nifty 500", ["Custom"] + nifty500_list)
            if n_in == "Custom": n_in = st.text_input("Enter Symbol").upper().strip()
            
            b_p = st.number_input("Buy Price", step=0.01)
            q_y = st.number_input("Qty", min_value=1, value=1)
            tax_in = st.number_input("Tax", 0.0, step=0.01)
            remark = st.text_input("Remark")
            
            if st.button("💾 Save Stock"):
                if n_in:
                    sym = n_in + ".NS" if ".NS" not in n_in else n_in
                    new = {
                        "Category": cat, "Buy Date": str(b_date), "Name": sym, 
                        "CMP": b_p, "Buy Price": b_p, "QTY Available": q_y, 
                        "Account": acc, "Investment": round(q_y*b_p, 2), 
                        "CM Value": round(q_y*b_p, 2), "P&L": 0, "P_Percentage": 0, 
                        "Status": "Holding", "Remark": remark, "Dividend": 0, "Tax": tax_in, "Sell Date": ""
                    }
                    df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                    df.to_csv(PORTFOLIO_FILE, index=False)
                    st.success("സേവ് ചെയ്തു!"); st.rerun()
        
        with c_b:
            st.write("### Manage Existing")
            holding_list = list(df[df['Status']=='Holding']['Name'].unique())
            st_manage = st.selectbox("Select Stock", ["None"] + holding_list)
            if st_manage != "None":
                if st.button("🗑️ Confirm Sell"):
                    df.loc[df['Name'] == st_manage, 'Status'] = 'Sold'
                    df.loc[df['Name'] == st_manage, 'Sell Date'] = str(datetime.now().date())
                    df.to_csv(PORTFOLIO_FILE, index=False)
                    st.success("Sold!"); st.rerun()

# --- TAB 3, 4, 5 (ബാക്കി കോഡ് മാറ്റമില്ലാതെ തുടരുന്നു...) ---
# (Analytics, News, Watchlist സെക്ഷനുകൾ നിങ്ങളുടെ പഴയ കോഡ് തന്നെ ഇതിന്റെ താഴെ ചേർക്കാം)
