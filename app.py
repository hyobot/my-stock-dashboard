import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------------
# [기본 설정] 페이지 타이틀 및 레이아웃
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Hybrid Barbell Dashboard", layout="wide")
st.title("🛡️ 하이브리드 바벨 & 가치 나침반")

# 탭 분리
tab1, tab2 = st.tabs(["📊 포트폴리오 모니터", "🧭 보수적 가치 나침반"])

# =============================================================================
# [Tab 1] 포트폴리오 모니터링 (안전 모드)
# =============================================================================
with tab1:
    assets = {
        'Defense (방어)': ['COST', 'WM', 'XLV'],
        'Core (핵심)': ['MSFT', 'GOOGL'],
        'Satellite (위성)': ['VRT', 'ETN']
    }
    
    @st.cache_data(ttl=60)
    def fetch_safe_data():
        summary_data = []
        vix_info = (0.0, 0.0)
        
        # (1) 자산 데이터 수집
        for cat, tickers in assets.items():
            for t in tickers:
                try:
                    ticker_obj = yf.Ticker(t)
                    df = ticker_obj.history(period="5d")
                    if len(df) >= 2:
                        latest = df.iloc[-1]
                        prev = df.iloc[-2]
                        pct_chg = ((latest['Close'] - prev['Close']) / prev['Close']) * 100
                        summary_data.append({
                            'Category': cat, 'Ticker': t,
                            'Price ($)': latest['Close'], 'Change (%)': pct_chg,
                            'Volume': latest['Volume']
                        })
                except:
                    continue 

        # (2) VIX 데이터 수집
        try:
            vix_df = yf.Ticker('^VIX').history(period="5d")
            if len(vix_df) >= 2:
                v_curr = vix_df['Close'].iloc[-1]
                v_prev = vix_df['Close'].iloc[-2]
                vix_info = (v_curr, (v_curr - v_prev) / v_prev * 100)
        except:
            pass

        return pd.DataFrame(summary_data), vix_info

    # 데이터 로드
    try:
        df_summary, vix_data = fetch_safe_data()
    except Exception as e:
        st.error(f"초기화 오류: {e}")
        st.stop()

    # 화면 구성
    st.header("1. Risk Monitor")
    c1, c2 = st.columns(2)
    v_val, v_chg = vix_data
    status = "🔴 위험 (Cash Up!)" if v_val > 20 else "🟢 안전 (Invest)"
    c1.metric("VIX (공포지수)", f"{v_val:.2f}", f"{v_chg:.2f}%", delta_color="inverse")
    c2.info(f"💡 시장 상태: **{status}**")

    st.divider()

    st.header("2. Portfolio Status")
    if not df_summary.empty:
        col_chart, col_table = st.
