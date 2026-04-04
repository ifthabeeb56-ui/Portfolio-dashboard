import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# --- കോൺഫിഗറേഷൻ ---
# BotFather തന്ന ടോക്കൺ ഇവിടെ നൽകുക
API_TOKEN = 'YOUR_BOT_TOKEN_HERE' 
CHAT_ID = '6044203893'

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{API_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
    try:
        requests.get(url)
    except:
        pass

# പേജ് സെറ്റിംഗ്സ്
st.set_page_config(page_title="Habeeb's Power Dashboard", layout="wide")

# ബ്ലൂ തീം സ്റ്റൈലിംഗ് (നിങ്ങൾ നൽകിയ ഫോട്ടോയിലെ പോലെ)
st.markdown("""
    <style>
    .main { background-color: #F4F7F9; }
    .stMetric { background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0px 4px 10px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] { background-color: #1A3A5F; color: white; }
    .stButton>button { background-color: #1E3A8A; color: white; border-radius: 8px; width: 100%; font-weight: bold; }
    .css-10trblm { color: white; } /* Sidebar text color */
    </style>
    """, unsafe_allow_html=True)

# സൈഡ് ബാർ നാവിഗേഷൻ
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: white;'>HABEEB INV</h2>", unsafe_allow_html=True)
    st.markdown("---")
    st.write("🏠 Home")
    st.write("📊 Analytics")
    st.write("⚙️ Settings")
    st.markdown("---")
    st.info("Upload your Excel file to update charts.")

st.title("📊 Portfolio Power Dashboard")

# ഫയൽ അപ്‌ലോഡ് (Excel മാത്രം)
uploaded_file = st.file_uploader("നിങ്ങളുടെ എക്സൽ (Excel) ഫയൽ ഇവിടെ അപ്‌ലോഡ് ചെയ്യുക", type=['xlsx'])

if uploaded_file:
    # ഡാറ്റ റീഡ് ചെയ്യുന്നു
    df = pd.read_excel(uploaded_file)
    
    # വരികൾ ക്ലീൻ ചെയ്യുന്നു
    df = df.dropna(subset=['Name', 'Invest'])

    # മുകളിലെ കാർഡുകൾ (KPIs)
    total_invest = df['Invest'].sum()
    current_val = df['CM Value'].sum()
    total_pnl = df['P&L'].sum()
    pnl_pct = (total_pnl / total_invest) * 100 if total_invest != 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Invested", f"₹{total_invest:,.0f}")
    with col2:
        st.metric("Current Value", f"₹{current_val:,.0f}")
    with col3:
        st.metric("Net P&L", f"₹{total_pnl:,.0f}", f"{pnl_pct:.2f}%")
    with col4:
        st.metric("Stocks Count", len(df))

    st.markdown("---")

    # ചാർട്ടുകൾ (ഫോട്ടോയിലെ മോഡൽ)
    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader("📈 Individual Stock Performance")
        fig = px.bar(df, x='Name', y='P&L', color='P&L', 
                     color_continuous_scale=['#FF4B4B', '#00CC96'],
                     template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Sector Wise Split")
        fig2 = px.pie(df, names='Category', values='Invest', hole=0.5)
        st.plotly_chart(fig2, use_container_width=True)

    # ഡാറ്റ ടേബിൾ
    st.subheader("📋 Detailed Portfolio")
    st.dataframe(df.style.format(subset=['Invest', 'CM Value', 'P&L'], formatter="₹{:.2f}"), use_container_width=True)

    # ടെലിഗ്രാം അലേർട്ട് ബട്ടൺ
    st.markdown("---")
    if st.button("🚀 Send Live Report to Telegram"):
        status = "🟢 PROFIT" if total_pnl >= 0 else "🔴 LOSS"
        msg = (
            f"🔔 *HABEEB PORTFOLIO UPDATE*\n\n"
            f"Status: {status}\n"
            f"💰 *Invested:* ₹{total_invest:,.0f}\n"
            f"📈 *Current:* ₹{current_val:,.0f}\n"
            f"💵 *Net P&L:* ₹{total_pnl:,.0f} ({pnl_pct:.2f}%)\n\n"
            f"Dashboard Updated! ✅"
        )
        send_telegram(msg)
        st.success("Telegram-ലേക്ക് റിപ്പോർട്ട് അയച്ചു!")

else:
    st.info("നിങ്ങളുടെ 2026 New Excel ഫയൽ അപ്‌ലോഡ് ചെയ്താൽ ഉടൻ ഡാറ്റ കാണാൻ സാധിക്കും.")
