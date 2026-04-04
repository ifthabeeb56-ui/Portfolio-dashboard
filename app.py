import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import os

# 1. പേജ് ലേഔട്ട് സെറ്റിംഗ്സ്
st.set_page_config(layout="wide", page_title="Habeeb's Power Dashboard")

# --- ഡാറ്റാബേസ് സെറ്റപ്പ് (CSV ഫയൽ) ---
DB_FILE = "portfolio_db.csv"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE)
        except:
            return pd.DataFrame(columns=['Account', 'Symbol', 'Sector', 'Index', 'Qty', 'Buy_Price', 'Tax', 'Total_Inv'])
    return pd.DataFrame(columns=['Account', 'Symbol', 'Sector', 'Index', 'Qty', 'Buy_Price', 'Tax', 'Total_Inv'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# ഡാറ്റ ഇനിഷ്യലൈസ് ചെയ്യുന്നു
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_data()

# 2. സൈഡ്ബാർ - ഇൻപുട്ട് വിഭാഗം
st.sidebar.title("📁 Portfolio Manager")

with st.sidebar.expander("➕ Add New Transaction", expanded=True):
    acc_name = st.selectbox("Select Account", ["Account 1", "Account 2", "Family", "Custom Name"])
    if acc_name == "Custom Name":
        acc_name = st.text_input("Enter Account Name", "My Account")
        
    symbol = st.text_input("Stock Symbol (eg: ABB, SBIN)").upper().strip()
    sector = st.selectbox("Sector", ["IT", "Banking", "Auto", "Pharma", "Energy", "FMCG", "Metal", "Others"])
    market_index = st.selectbox("Index", ["Nifty 50", "Nifty Next 50", "Nifty Midcap", "Nifty Smallcap", "Nifty 500"])
    
    qty = st.number_input("Quantity", min_value=1, step=1)
    price = st.number_input("Buy Price", min_value=0.0, format="%.2f")
    tax = st.number_input("Tax / Charges", min_value=0.0, format="%.2f")
    
    if st.button("Add & Save Permanently"):
        if symbol:
            full_symbol = symbol if symbol.endswith('.NS') else f"{symbol}.NS"
            total_cost = (qty * price) + tax
            
            new_entry = pd.DataFrame([{
                'Account': acc_name, 'Symbol': full_symbol, 'Sector': sector,
                'Index': market_index, 'Qty': qty, 'Buy_Price': price,
                'Tax': tax, 'Total_Inv': total_cost
            }])
            
            # ഡാറ്റ അപ്ഡേറ്റ് ചെയ്യുന്നു
            st.session_state.my_portfolio = pd.concat([st.session_state.my_portfolio, new_entry], ignore_index=True)
            save_data(st.session_state.my_portfolio)
            st.success(f"{full_symbol} Saved Successfully!")
            st.rerun()

# 3. ഫിൽട്ടറിംഗ് സെക്ഷൻ
st.sidebar.divider()
all_accounts = st.session_state.my_portfolio['Account'].unique().tolist()
view_acc = st.sidebar.multiselect("Filter by Account", options=all_accounts, default=all_accounts)

# ഫിൽട്ടർ ചെയ്ത ലിസ്റ്റ്
filtered_df = st.session_state.my_portfolio[st.session_state.my_portfolio['Account'].isin(view_acc)]
stock_list = filtered_df['Symbol'].unique().tolist()

# സ്റ്റോക്ക് സെലക്ഷൻ (ലിസ്റ്റ് ഉണ്ടെങ്കിൽ മാത്രം)
if stock_list:
    selected_stock = st.sidebar.selectbox("Select Stock to Analyze", stock_list)
else:
    selected_stock = "RELIANCE.NS" # Default

# 4. ലൈവ് ഡാറ്റ ഫെച്ചിംഗ്
@st.cache_data(ttl=300)
def fetch_live_data(symbol):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

live_data = fetch_live_data(selected_stock)

# 5. ഡിസ്പ്ലേ ബോർഡും മെട്രിക്സും
if live_data is not None:
    l_price = float(live_data['Close'].iloc[-1])
    stock_detail = filtered_df[filtered_df['Symbol'] == selected_stock]
    
    st.title(f"📊 {selected_stock} Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Live Price", f"₹{l_price:.2f}")
    
    if not stock_detail.empty:
        t_qty = stock_detail['Qty'].sum()
        t_inv = stock_detail['Total_Inv'].sum()
        avg_price = t_inv / t_qty
        curr_val = t_qty * l_price
        pnl = curr_val - t_inv
        pnl_pct = (pnl / t_inv) * 100
        
        col2.metric("Avg Buy Cost", f"₹{avg_price:.2f}")
        col3.metric("Profit / Loss", f"₹{pnl:.2f}", f"{pnl_pct:.2f}%")
        col4.metric("Holding Qty", f"{int(t_qty)}")

    # ചാർട്ട്
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=live_data.index, open=live_data['Open'], high=live_data['High'], 
                                 low=live_data['Low'], close=live_data['Close'], name='Market Price'))
    fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# 6. ഡാറ്റ റിപ്പോർട്ടും ഡിലീറ്റ് ഓപ്ഷനും
st.subheader("📋 Permanent Portfolio Records")
if not st.session_state.my_portfolio.empty:
    st.dataframe(st.session_state.my_portfolio, use_container_width=True)
    
    with st.expander("🗑️ Delete a Transaction"):
        del_id = st.number_input("Enter Index Number to Delete", min_value=0, max_value=len(st.session_state.my_portfolio)-1, step=1)
        if st.button("Delete Permanently"):
            st.session_state.my_portfolio = st.session_state.my_portfolio.drop(del_id).reset_index(drop=True)
            save_data(st.session_state.my_portfolio)
            st.warning(f"Record {del_id} Deleted.")
            st.rerun()
else:
    st.info("Portfolio കാലിയാണ്. പുതിയ സ്റ്റോക്കുകൾ ആഡ് ചെയ്യുക.")
