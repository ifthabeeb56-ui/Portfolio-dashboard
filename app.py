import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# 1. പേജ് ലേഔട്ട്
st.set_page_config(layout="wide", page_title="Habeeb's Power Dashboard")

# 2. വാച്ച്‌ലിസ്റ്റ്
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

# 3. സൈഡ്ബാർ
st.sidebar.title("📁 Portfolio Manager")

with st.sidebar.expander("➕ Add New Stock", expanded=True):
    new_stock_input = st.text_input("Enter Symbol (eg: SBIN)").upper().strip()
    if st.button("Add to Dashboard"):
        if new_stock_input:
            # .NS ഇല്ലെങ്കിൽ ചേർക്കുന്നു
            if not new_stock_input.endswith('.NS') and "." not in new_stock_input:
                new_stock_input += '.NS'
            
            if new_stock_input not in st.session_state.watchlist:
                st.session_state.watchlist.append(new_stock_input)
                st.success(f"{new_stock_input} ചേർത്തു!")
                st.rerun() # ഇവിടെ മാറ്റം വരുത്തി

# 4. ഡാറ്റ എടുക്കുന്ന ഫങ്ക്ഷൻ (കൂടുതൽ സുരക്ഷിതം)
@st.cache_data
def get_data(symbol):
    df = yf.download(symbol, period="1y", interval="1d")
    if df.empty:
        return None
    
    # Column level ശരിയാക്കുന്നു
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Technicals
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 0.00001) # Zero division ഒഴിവാക്കാൻ
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

# 5. ഡിസ്പ്ലേ ഭാഗം
selected_stock = st.sidebar.selectbox("Select Stock", st.session_state.watchlist)

try:
    df = get_data(selected_stock)
    if df is not None:
        # വിലകൾ കൃത്യമായി എടുക്കുന്നു (Squeeze ഉപയോഗിച്ച് Single Value ആക്കുന്നു)
        curr_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-2])
        
        price_diff = round(curr_price - prev_price, 2)
        pct_change = round((price_diff / prev_price) * 100, 2)
        rsi_val = round(float(df['RSI'].iloc[-1]), 2)

        st.title(f"📈 {selected_stock} Dashboard")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current Price", f"₹{curr_price:.2f}", f"{pct_change}%")
        
        rsi_status = "Neutral"
        if rsi_val > 70: rsi_status = "Overbought"
        elif rsi_val < 30: rsi_status = "Oversold"
        m2.metric("RSI (14)", rsi_val, rsi_status)

        # EMA Trend
        last_ema20 = df['EMA20'].iloc[-1]
        last_ema50 = df['EMA50'].iloc[-1]
        ema_signal = "Bullish" if last_ema20 > last_ema50 else "Bearish"
        m3.metric("20/50 EMA Trend", ema_signal)
        m4.metric("Market", "NSE India", "Live")

        # ചാർട്ട്
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'))
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], line=dict(color='blue', width=1), name='EMA 20'))
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='orange', width=1), name='EMA 50'))
        fig.update_layout(height=500, template="plotly_white", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("ഡാറ്റ ലഭ്യമല്ല. സിംബൽ പരിശോധിക്കുക.")
except Exception as e:
    st.error(f"പ്രശ്നം സംഭവിച്ചു: {e}")
