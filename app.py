import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import os

# 1. പേജ് സെറ്റിംഗ്സ്
st.set_page_config(layout="wide", page_title="Habeeb's Auto-Portfolio")

DB_FILE = "portfolio_db.csv"

def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=['Account', 'Symbol', 'Sector', 'Index', 'Qty', 'Buy_Price', 'Tax', 'Total_Inv'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# Session State ഇനിഷ്യലൈസ് ചെയ്യുന്നു
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_data()
if 'auto_sector' not in st.session_state:
    st.session_state.auto_sector = "Others"
if 'auto_price' not in st.session_state:
    st.session_state.auto_price = 0.0

# 2. സൈഡ്ബാർ - ഓട്ടോമാറ്റിക് എൻട്രി
st.sidebar.title("📁 Portfolio Manager")

with st.sidebar.expander("➕ Add New Transaction", expanded=True):
    acc_name = st.selectbox("Select Account", ["Account 1", "Account 2", "Family"])
    
    # സിംബൽ ടൈപ്പ് ചെയ്യുമ്പോൾ ഡാറ്റ എടുക്കാനുള്ള ഫങ്ക്ഷൻ
    symbol_input = st.text_input("Stock Symbol (eg: ABB, SBIN)").upper().strip()
    
    if symbol_input:
        full_sym = symbol_input if symbol_input.endswith('.NS') else f"{symbol_input}.NS"
        try:
            ticker = yf.Ticker(full_sym)
            # ലൈവ് പ്രൈസും സെക്ടറും ഫെച്ച് ചെയ്യുന്നു
            st.session_state.auto_price = float(ticker.fast_info['lastPrice'])
            st.session_state.auto_sector = ticker.info.get('sector', 'Others')
        except:
            st.session_state.auto_price = 0.0
            st.session_state.auto_sector = "Not Found"

    # ഓട്ടോ ഫെച്ച് ചെയ്ത വിവരങ്ങൾ ഇവിടെ കാണിക്കുന്നു (ഇത് നിങ്ങൾക്ക് എഡിറ്റ് ചെയ്യാം)
    sector = st.text_input("Sector", value=st.session_state.auto_sector)
    market_index = st.selectbox("Index", ["Nifty 50", "Nifty Next 50", "Nifty Midcap", "Nifty 500"])
    
    qty = st.number_input("Quantity", min_value=1, step=1)
    
    # പ്രൈസ് ഓട്ടോമാറ്റിക് ആയി വരും
    price = st.number_input("Buy Price", value=st.session_state.auto_price, format="%.2f")
    tax = st.number_input("Tax / Charges", min_value=0.0, format="%.2f")
    
    if st.button("Add & Save Permanently"):
        if symbol_input:
            full_symbol = symbol_input if symbol_input.endswith('.NS') else f"{symbol_input}.NS"
            total_cost = (qty * price) + tax
            
            new_entry = pd.DataFrame([{
                'Account': acc_name, 'Symbol': full_symbol, 'Sector': sector,
                'Index': market_index, 'Qty': qty, 'Buy_Price': price,
                'Tax': tax, 'Total_Inv': total_cost
            }])
            
            st.session_state.my_portfolio = pd.concat([st.session_state.my_portfolio, new_entry], ignore_index=True)
            save_data(st.session_state.my_portfolio)
            st.success("Saved Successfully!")
            st.rerun()

# 3. ഡിസ്പ്ലേ & ചാർട്ട്
st.sidebar.divider()
all_acc = st.session_state.my_portfolio['Account'].unique().tolist()
view_acc = st.sidebar.multiselect("Filter Account", options=all_acc, default=all_acc)

filtered_df = st.session_state.my_portfolio[st.session_state.my_portfolio['Account'].isin(view_acc)]

if not filtered_df.empty:
    selected_stock = st.sidebar.selectbox("Analyze Stock", filtered_df['Symbol'].unique())
    data = yf.download(selected_stock, period="1mo", interval="1d", progress=False)
    
    if not data.empty:
        st.title(f"📊 {selected_stock} Dashboard")
        st.metric("LTP", f"₹{data['Close'].iloc[-1]:.2f}")
        fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
        fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

# 4. റെക്കോർഡ്സ് ടേബിൾ
st.subheader("📋 Portfolio Records")
st.dataframe(st.session_state.my_portfolio, use_container_width=True)
