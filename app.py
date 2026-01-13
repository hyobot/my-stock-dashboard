import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Hybrid Barbell Dashboard", layout="wide")
st.title("🛡️ 하이브리드 바벨 전략 대시보드")

# 1. 자산 및 설정
assets = {
    'Defense (좌측)': ['COST', 'WM', 'XLV'],
    'Core (우측-핵심)': ['MSFT', 'GOOGL'],
    'Satellite (우측-위성)': ['VRT', 'ETN']
}
risk_tickers = {'VIX': '^VIX', '10Y Yield': '^TNX'}

# 2. 데이터 가져오기
@st.cache_data(ttl=60)
def fetch_data():
    tickers = [t for cat in assets.values() for t in cat] + list(risk_tickers.values())
    data = yf.download(tickers, period="5d", progress=False)['Close']
    changes = data.pct_change().iloc[-1] * 100
    return data.iloc[-1], changes

try:
    prices, changes = fetch_data()
except:
    st.error("데이터 로딩 실패. 잠시 후 다시 시도해주세요.")
    st.stop()

# 3. 화면 구성
st.header("1. Risk Monitor")
col1, col2 = st.columns(2)
vix_val = prices['^VIX']
status = "🔴 위험 (Cash Up!)" if vix_val > 20 else "🟢 안전 (Invest)"
col1.metric("VIX (공포지수)", f"{vix_val:.2f}", f"{changes['^VIX']:.2f}%", delta_color="inverse")
col2.info(f"시장 상태: **{status}**")

st.divider()

st.header("2. Portfolio Status")
rows = []
for cat, tickers in assets.items():
    for t in tickers:
        rows.append({'Category': cat, 'Ticker': t, 'Change(%)': changes[t]})
df = pd.DataFrame(rows)

fig = px.bar(df, x='Ticker', y='Change(%)', color='Category', title="실시간 자산 변동률",
             color_discrete_map={'Defense (좌측)': '#2ecc71', 'Core (우측-핵심)': '#3498db', 'Satellite (우측-위성)': '#e74c3c'})
st.plotly_chart(fig, use_container_width=True)
