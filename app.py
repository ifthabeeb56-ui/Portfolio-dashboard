import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os
import time

# --- ഫയൽ സെറ്റിംഗ്സ് ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"

def load_data():
    req_cols = ["Category", "Buy Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", 
                "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", 
                "Remark", "Status", "Today_PnL", "Sell_Price", "Sell_Date"]
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        for col in req_cols:
            if col not in df.columns:
                df[col] = "" if col in ["Sell_Date", "Remark", "Category", "Account", "Status", "Name"] else 0.0
        return df
    return pd.DataFrame(columns=req_cols)

@st.cache_data(ttl=86400)
def get_nifty500_tickers():
    try:
        url = "https://raw.githubusercontent.com/anirban-d/nifty-indices-constituents/main/ind_nifty500list.csv"
        return sorted(pd.read_csv(url)['Symbol'].tolist())
    except:
        return ["RELIANCE", "TCS", "HDFCBANK"]

# --- App Setup ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.9")
df = load_data()
nifty500_list = get_nifty500_tickers()

st.title("📊 Habeeb's Power Hub v6.9")
tab1, tab2 = st.tabs(["🔍 Heatmap", "💼 Portfolio"])

# --- TAB 1: HEATMAP (ValueError Fix) ---
with tab1:
    hold_df = df[df['Status'] == "Holding"].copy()
    if not hold_df.empty:
        st.subheader("Market Visualization Settings")
        box_size = st.radio("Box Size based on:", ["Investment", "Daily % Change"], horizontal=True)
        
        # 'Today_PnL' നെഗറ്റീവ് ആണെങ്കിൽ ഹീറ്റ്‌മാപ്പിൽ എറർ വരും. അത് ഒഴിവാക്കാൻ abs() ഉപയോഗിക്കുന്നു.
        val_col = 'Investment' if box_size == "Investment" else 'Today_PnL'
        hold_df['Plot_Size'] = hold_df[val_col].abs() 

        # വാല്യൂ പൂജ്യം ആണെങ്കിലും എറർ വരാം, അത് ചെക്ക് ചെയ്യുന്നു.
        if hold_df['Plot_Size'].sum() > 0:
            fig = px.treemap(hold_df, path=['Name'], values='Plot_Size', 
                             color='P_Percentage', color_continuous_scale='RdYlGn',
                             range_color=[-5, 5])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("ഹീറ്റ്‌മാപ്പ് കാണിക്കാൻ മതിയായ ഡാറ്റയില്ല.")
    else:
        st.info("സ്റ്റോക്കുകൾ ആഡ് ചെയ്യുക.")

# --- TAB 2: PORTFOLIO & ADD STOCK ---
with tab2:
    with st.expander("➕ Add New Stock"):
        col1, col2 = st.columns(2)
        with col1:
            p_date = st.date_input("Purchase Date", datetime.now())
            cat = st.selectbox("Category", ["Equity", "Mutual Fund", "ETF"])
            acc = st.selectbox("Account", ["Habeeb", "RISU", "Family"])
            sym_sel = st.selectbox("Select Symbol from Nifty 500", ["Custom"] + nifty500_list)
            sym = st.text_input("Enter Symbol").upper() if sym_sel == "Custom" else sym_sel
        with col2:
            price = st.number_input("Buy Price", min_value=0.0, step=0.05)
            qty = st.number_input("Qty", min_value=1, step=1)
            tax = st.number_input("Tax", value=0.0)
            rem = st.text_input("Remark")

        if st.button("💾 Save Stock", use_container_width=True):
            final_sym = sym + ".NS" if ".NS" not in sym else sym
            new_data = {
                "Category": cat, "Buy Date": str(p_date), "Name": final_sym, 
                "CMP": price, "Buy Price": price, "QTY Available": qty, 
                "Account": acc, "Investment": round(qty*price, 2), "CM Value": round(qty*price, 2),
                "P&L": 0, "P_Percentage": 0, "Status": "Holding", "Tax": tax, "Today_PnL": 0
            }
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
            df.to_csv(PORTFOLIO_FILE, index=False)
            st.success("Saved!")
            st.rerun()
    
