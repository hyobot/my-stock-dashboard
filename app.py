import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------------
# [기본 설정] 페이지 타이틀 및 레이아웃
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Hybrid Barbell & Value Compass", layout="wide")
st.title("🛡️ 하이브리드 바벨 & 가치 나침반")

# 탭 분리: 모니터링(Tab 1) vs 가치 계산기(Tab 2)
tab1, tab2 = st.tabs(["📊 포트폴리오 모니터", "🧭 보수적 가치 나침반"])

# =============================================================================
# [Tab 1] 기존 포트폴리오 모니터링 기능
# =============================================================================
with tab1:
    # 1. 자산 및 설정
    assets = {
        'Defense (좌측-방어)': ['COST', 'WM', 'XLV'],
        'Core (우측-핵심)': ['MSFT', 'GOOGL'],
        'Satellite (우측-위성)': ['VRT', 'ETN']
    }
    risk_tickers = {'VIX': '^VIX', '10Y Yield': '^TNX'}
    all_tickers = [t for cat in assets.values() for t in cat] + list(risk_tickers.values())

    # 2. 데이터 가져오기 (캐싱 적용)
    @st.cache_data(ttl=60)
    def fetch_market_data():
        # group_by='ticker'로 설정하여 다중 종목 데이터 구조화
        data = yf.download(all_tickers, period="5d", group_by='ticker', progress=False)
        return data

    try:
        raw_data = fetch_market_data()
    except Exception as e:
        st.error(f"데이터 로딩 실패: {e}")
        st.stop()

    # 데이터 가공
    rows = []
    for cat, tickers in assets.items():
        for t in tickers:
            try:
                df_t = raw_data[t]
                latest = df_t.iloc[-1]
                prev = df_t.iloc[-2]
                
                # 변동폭 계산
                chg = latest['Close'] - prev['Close']
                pct_chg = (chg / prev['Close']) * 100
                
                rows.append({
                    'Category': cat, 
                    'Ticker': t,
                    'Price ($)': round(latest['Close'], 2),
                    'Change (%)': round(pct_chg, 2),
                    'Volume': f"{int(latest['Volume']):,}" if 'Volume' in latest else "N/A"
                })
            except KeyError:
                continue
    
    df_summary = pd.DataFrame(rows)

    # 3. 화면 구성 (Risk Monitor)
    st
