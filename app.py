import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="Hybrid Barbell Dashboard", layout="wide")
st.title("🛡️ 하이브리드 바벨 전략 대시보드 (Advanced)")

# 1. 자산 및 설정
assets = {
    'Defense (좌측-방어)': ['COST', 'WM', 'XLV'],
    'Core (우측-핵심)': ['MSFT', 'GOOGL'],
    'Satellite (우측-위성)': ['VRT', 'ETN']
}
risk_tickers = {'VIX': '^VIX', '10Y Yield': '^TNX'}

# 모든 티커 리스트 병합
all_tickers = [t for cat in assets.values() for t in cat] + list(risk_tickers.values())

# 2. 데이터 가져오기 (수정: 종가 외에 모든 데이터 가져오기)
@st.cache_data(ttl=60)
def fetch_data():
    # group_by='ticker'로 설정하여 종목별 관리가 용이하게 함
    data = yf.download(all_tickers, period="5d", group_by='ticker', progress=False)
    return data

try:
    raw_data = fetch_data()
except Exception as e:
    st.error(f"데이터 로딩 실패: {e}")
    st.stop()

# 3. 데이터 가공 (테이블 생성을 위한 전처리)
rows = []
for cat, tickers in assets.items():
    for t in tickers:
        try:
            # 해당 종목의 최근 2일치 데이터 추출
            df_t = raw_data[t]
            latest = df_t.iloc[-1]
            prev = df_t.iloc[-2]
            
            # 변동률 계산
            chg = latest['Close'] - prev['Close']
            pct_chg = (chg / prev['Close']) * 100
            
            rows.append({
                'Category': cat,
                'Ticker': t,
                'Price ($)': round(latest['Close'], 2),
                'Change ($)': round(chg, 2),
                'Change (%)': round(pct_chg, 2),
                'Volume': f"{int(latest['Volume']):,}" if 'Volume' in latest else "N/A" # 지수는 거래량 없을 수 있음
            })
        except KeyError:
            continue

df_summary = pd.DataFrame(rows)

# 4. 화면 구성

# [섹션 1] Risk Monitor (기존 유지 + 데이터 명확화)
st.header("1. Risk Monitor")
col1, col2 = st.columns(2)

# VIX 데이터 추출
vix_df = raw_data['^VIX']
vix_curr = vix_df['Close'].iloc[-1]
vix_prev = vix_df['Close'].iloc[-2]
vix_chg = (vix_curr - vix_prev) / vix_prev * 100

status = "🔴 위험 (Cash Up!)" if vix_curr > 20 else "🟢 안전 (Invest)"

col1.metric("VIX (공포지수)", f"{vix_curr:.2f}", f"{vix_chg:.2f}%", delta_color="inverse")
col2.info(f"💡 시장 상태 판단: **{status}**")

st.divider()

# [섹션 2] Portfolio Overview (차트)
st.header("2. Portfolio Visualization")
if not df_summary.empty:
    fig = px.bar(
        df_summary, 
        x='Ticker', 
        y='Change (%)', 
        color='Category', 
        text='Change (%)', # 막대 위에 수치 표시 추가
        title="실시간 자산 변동률 (%)",
        color_discrete_map={'Defense (좌측-방어)': '#2ecc71', 'Core (우측-핵심)': '#3498db', 'Satellite (우측-위성)': '#e74c3c'}
    )
    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside') # 수치 잘 보이게 설정
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("표시할 데이터가 없습니다.")

st.divider()

# [섹션 3] Detailed Data Table (신규 추가: 요청하신 데이터 값 포함)
st.header("3. Detailed Asset Status")
st.markdown("각 종목별 **현재가, 등락폭, 등락률, 거래량** 상세 데이터입니다.")

# 보기 좋게 스타일링하여 테이블 출력
st.dataframe(
    df_summary.style.format({
        'Price ($)': '{:.2f}',
        'Change ($)': '{:+.2f}',
        'Change (%)': '{:+.2f}'
    }).applymap(lambda x: 'color: red' if x < 0 else 'color: green', subset=['Change (%)']),
    use_container_width=True,
    hide_index=True
)

# [섹션 4] 그룹별 핵심 요약 (신규 추가: 텍스트로 값 확인)
st.subheader("📌 그룹별 핵심 시세")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("##### 🛡️ Defense")
    defense_df = df_summary[df_summary['Category']=='Defense (좌측-방어)']
    for _, row in defense_df.iterrows():
        st.metric(label=row['Ticker'], value=f"${row['Price ($)']}", delta=f"{row['Change (%)']}%")

with c2:
    st.markdown("##### 💎 Core")
    core_df = df_summary[df_summary['Category']=='Core (우측-핵심)']
    for _, row in core_df.iterrows():
        st.metric(label=row['Ticker'], value=f"${row['Price ($)']}", delta=f"{row['Change (%)']}%")

with c3:
    st.markdown("##### 🚀 Satellite")
    sat_df = df_summary[df_summary['Category']=='Satellite (우측-위성)']
    for _, row in sat_df.iterrows():
        st.metric(label=row['Ticker'], value=f"${row['Price ($)']}", delta=f"{row['Change (%)']}%")
