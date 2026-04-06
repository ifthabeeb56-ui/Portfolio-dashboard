import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import plotly.express as px
import os
import zipfile
import io

# --- 1. ഫയൽ സെറ്റിംഗ്സ് ---
PORTFOLIO_FILE = "habeeb_portfolio_v6.csv"
WATCHLIST_FILE = "watchlist_data.txt"
HISTORY_FILE = "portfolio_history.csv"

# --- 2. ഫംഗ്ഷനുകൾ ---
@st.cache_data(ttl=86400)
def get_nifty500_tickers():
    try:
        url = "https://raw.githubusercontent.com/indandata/stock-market-data/master/ind_nifty500list.csv"
        n500_df = pd.read_csv(url)
        return sorted(n500_df['Symbol'].tolist())
    except:
        return ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN"]

def load_data():
    cols = ["Category", "Buy Date", "Sell Date", "Name", "CMP", "Buy Price", "QTY Available", "Account", "Investment", "CM Value", "P&L", "P_Percentage", "Tax", "Dividend", "Remark", "Status"]
    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
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
            return [line.strip() for line in f.readlines() if line.strip()]
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
                    # Single vs Multiple Ticker handling
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

# --- 3. ആപ്പ് സെറ്റപ്പ് ---
st.set_page_config(layout="wide", page_title="Habeeb's Power Hub v6.8", page_icon="📈")

# ഡാറ്റാ ലോഡിംഗ്
df = load_data()
watch_data_list = get_watchlist()
nifty500_list = get_nifty500_tickers()

# --- 💾 സൈഡ്‌ബാർ: Smart Backup Hub (ZIP) ---
with st.sidebar:
    st.header("📦 Smart Backup Hub")
    st.write("Portfolio + Watchlist")
    
    # ഡൗൺലോഡ് സെക്ഷൻ
    if os.path.exists(PORTFOLIO_FILE) or os.path.exists(WATCHLIST_FILE):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as x_zip:
            if os.path.exists(PORTFOLIO_FILE): x_zip.write(PORTFOLIO_FILE)
            if os.path.exists(WATCHLIST_FILE): x_zip.write(WATCHLIST_FILE)
            if os.path.exists(HISTORY_FILE): x_zip.write(HISTORY_FILE)
        
        st.download_button(
            label="📥 Download All-in-One ZIP",
            data=buf.getvalue(),
            file_name=f"habeeb_full_backup_{datetime.now().strftime('%Y%m%d')}.zip",
            mime="application/zip",
            use_container_width=True
        )
    
    st.divider()
    
    # അപ്‌ലോഡ് (Restore) സെക്ഷൻ
    st.subheader("📤 Restore Data")
    uploaded_zip = st.file_uploader("Upload Backup ZIP file", type=["zip"])
    if uploaded_zip:
        if st.button("🚀 Start Full Restore", use_container_width=True):
            try:
                with zipfile.ZipFile(uploaded_zip, 'r') as z:
                    z.extractall()
                st.success("വിജയകരമായി അപ്‌ഡേറ്റ് ചെയ്തു!"); st.rerun()
            except Exception as e:
                st.error(f"Error restoring: {e}")

# --- മെയിൻ ടാബുകൾ ---
st.title("📊 Habeeb's Power Hub v6.8")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔍 Heatmap", "💼 Portfolio", "📊 Analytics", "📰 News", "👀 Watchlist"])

# --- TAB 1: HEATMAP ---
with tab1:
    st.subheader("Portfolio Market View")
    hold_df_heatmap = df[df['Status'] == "Holding"].copy()
    if not hold_df_heatmap.empty:
        fig = px.treemap(hold_df_heatmap, path=['Name'], values='Investment', 
                         color='P_Percentage', color_continuous_scale='RdYlGn',
                         range_color=[-5, 5])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ഹീറ്റ്‌മാപ്പ് കാണാൻ സ്റ്റോക്കുകൾ ആഡ് ചെയ്യുക.")

# --- TAB 2: PORTFOLIO ---
with tab2:
    if not df.empty:
        with st.spinner("Updating Prices..."):
            df = update_live_prices(df)
        
        hold_df = df[df['Status'] == "Holding"].copy()
        if not hold_df.empty:
            t_inv, t_val, t_pnl = hold_df['Investment'].sum(), hold_df['CM Value'].sum(), hold_df['P&L'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Investment", f"₹{t_inv:,.2f}")
            c2.metric("Current Value", f"₹{t_val:,.2f}")
            c3.metric("Total P&L", f"₹{t_pnl:,.2f}", f"{((t_pnl/t_inv)*100):.2f}%" if t_inv > 0 else "0%")
            
            st.divider()
            st.dataframe(hold_df[['Name', 'Buy Price', 'CMP', 'QTY Available', 'Investment', 'CM Value', 'P&L', 'P_Percentage', 'Account']], 
                         use_container_width=True, hide_index=True)
        else:
            st.info("ഹോൾഡിംഗ്സ് ഒന്നുമില്ല.")
    
    with st.expander("➕ Add New Stock"):
        c_a, c_b = st.columns(2)
        with c_a:
            b_date = st.date_input("Purchase Date", datetime.now())
            cat = st.selectbox("Category", ["Equity", "ETF", "Mutual Fund"])
            acc = st.selectbox("Account", ["Habeeb", "RISU"])
        with c_b:
            n_in = st.selectbox("Select Ticker", ["Custom"] + nifty500_list)
            if n_in == "Custom": n_in = st.text_input("Enter Symbol").upper()
            b_p = st.number_input("Buy Price", min_value=0.0, step=0.01)
            q_y = st.number_input("Quantity", min_value=1, step=1)
            
        if st.button("💾 Save to Portfolio", use_container_width=True):
            if n_in and b_p > 0:
                sym = n_in + ".NS" if not n_in.endswith(".NS") else n_in
                new_row = {
                    "Category": cat, "Buy Date": str(b_date), "Name": sym, "CMP": b_p, 
                    "Buy Price": b_p, "QTY Available": q_y, "Account": acc, 
                    "Investment": round(q_y*b_p, 2), "CM Value": round(q_y*b_p, 2), 
                    "P&L": 0, "P_Percentage": 0, "Status": "Holding", "Dividend": 0, "Tax": 0, "Sell Date": ""
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(PORTFOLIO_FILE, index=False)
                st.success(f"{sym} Added!")
                st.rerun()

# --- TAB 5: WATCHLIST ---
with tab5:
    st.subheader("👀 Professional Watchlist")
    
    c_w1, c_w2 = st.columns([3, 1])
    with c_w1:
        w_in = st.text_input("Ticker Name (eg: RELIANCE)", key="watch_ticker").upper().strip()
    with c_w2:
        st.write("##")
        if st.button("➕ Add to Watchlist", use_container_width=True) and w_in:
            ticker_formatted = w_in + ".NS" if not w_in.endswith(".NS") else w_in
            add_date = datetime.now().strftime("%d-%m-%Y")
            with open(WATCHLIST_FILE, "a") as f:
                f.write(f"{ticker_formatted},{add_date}\n")
            st.rerun()

    # ഫയലിൽ നിന്ന് ഡാറ്റ വായിക്കുന്നു
    current_watch = get_watchlist()
    if current_watch:
        lines = [line.split(',') for line in current_watch]
        valid_tickers = [l[0] for l in lines if len(l[0]) > 3]
        
        try:
            with st.spinner("Fetching Live Prices..."):
                w_live_data = yf.download(valid_tickers, period="2d", progress=False)['Close']
            
            st.divider()
            cols = st.columns(3)
            for i, entry in enumerate(lines):
                t_name = entry[0]
                t_date = entry[1] if len(entry) > 1 else "N/A"
                
                with cols[i % 3]:
                    try:
                        # Price calculation
                        if len(valid_tickers) == 1:
                            curr_p = float(w_live_data.iloc[-1])
                            prev_p = float(w_live_data.iloc[-2])
                        else:
                            curr_p = float(w_live_data[t_name].iloc[-1])
                            prev_p = float(w_live_data[t_name].iloc[-2])
                        
                        price_change = ((curr_p - prev_p) / prev_p) * 100
                        
                        with st.container(border=True):
                            st.markdown(f"### {t_name.replace('.NS', '')}")
                            st.caption(f"📅 Added: {t_date}")
                            st.metric("Price", f"₹{curr_p:,.2f}", f"{price_change:+.2f}%")
                    except:
                        st.error(f"Error loading {t_name}")
        except:
            st.warning("ലൈവ് ഡാറ്റ ലഭ്യമാക്കാൻ കഴിയുന്നില്ല.")

        st.divider()
        if st.button("🗑️ Clear All Watchlist", type="secondary"):
            if os.path.exists(WATCHLIST_FILE):
                os.remove(WATCHLIST_FILE)
                st.rerun()
    else:
        st.info("നിങ്ങളുടെ വാച്ച്‌ലിസ്റ്റ് ഒഴിഞ്ഞു കിടക്കുകയാണ്.")

# Tab 3 & 4 (Analytics & News) can be integrated as per your existing code.
