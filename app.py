import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------------
# [기본 설정] 페이지 타이틀 및 레이아웃
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Hybrid Barbell Dashboard", layout="wide")
st.title("🛡️ 하이브리드 바벨 & 가치 나침반 (Safe Mode)")

# 탭 분리
tab1, tab2 = st.tabs(["📊 포트폴리오 모니터", "🧭 보수적 가치 나침반"])

# =============================================================================
# [Tab 1] 포트폴리오 모니터링 (안전한 개별 호출 방식 적용)
# =============================================================================
with tab1:
    # 1. 자산 목록 정의
    assets = {
        'Defense (방어)': ['COST', 'WM', 'XLV'],
        'Core (핵심)': ['MSFT', 'GOOGL'],
        'Satellite (위성)': ['VRT', 'ETN']
    }
    
    # 2. 데이터 가져오기 함수 (개별 호출로 안정성 확보)
    @st.cache_data(ttl=60)
    def fetch_safe_data():
        summary_data = []
        vix_info = None
        
        # 진행 상황 표시용 (선택 사항)
        status_text = st.empty()

        # (1) 자산 데이터 수집 (하나씩 순차적으로 시도)
        for cat, tickers in assets.items():
            for t in tickers:
                try:
                    status_text.text(f"데이터 수집 중: {t}...")
                    # 최근 5일치 데이터 개별 호출
                    ticker_obj = yf.Ticker(t)
                    df = ticker_obj.history(period="5d")
                    
                    if len(df) >= 2:
                        latest = df.iloc[-1]
                        prev = df.iloc[-2]
                        
                        chg = latest['Close'] - prev['Close']
                        pct_chg = (chg / prev['Close']) * 100
                        
                        summary_data.append({
                            'Category': cat, 
                            'Ticker': t,
                            'Price ($)': latest['Close'],
                            'Change (%)': pct_chg,
                            'Volume': latest['Volume']
                        })
                    else:
                        print(f"[Warning] {t}: 데이터 부족")
                except Exception as e:
                    print(f"[Error] {t}: {e}")
                    continue # 에러난 종목은 패스하고 다음 종목 진행

        status_text.empty() # 텍스트 제거

        # (2) VIX 데이터 수집 (별도 처리)
        try:
            vix_df = yf.Ticker('^VIX').history(period="5d")
            if len(vix_df) >= 2:
                v_curr = vix_df['Close'].iloc[-1]
                v_prev = vix_df['Close'].iloc[-2]
                v_chg_pct = (v_curr - v_prev) / v_prev * 100
                vix_info = (v_curr, v_chg_pct)
        except:
            vix_info = (0.0, 0.0)

        return pd.DataFrame(summary_data), vix_info

    # 데이터 로딩 실행
    with st.spinner('시장 데이터를 안전하게 불러오는 중...'):
        df_summary, vix_data = fetch_safe_data()

    # 3. 화면 구성: Risk Monitor
    st.header("1. Risk Monitor")
    c1, c2 = st.columns(2)
    
    if vix_data:
        v_val, v_chg = vix_data
        status = "🔴 위험 (Cash Up!)" if v_val > 20 else "🟢 안전 (Invest)"
        c1.metric("VIX (공포지수)", f"{v_val:.2f}", f"{v_chg:.2f}%", delta_color="inverse")
        c2.info(f"💡 시장 상태: **{status}**")
    else:
        c1.warning("VIX 데이터 로드 실패")

    st.divider()

    # 4. 화면 구성: Portfolio Status
    st.header("2. Portfolio Status")
    
    # 데이터가 비어있지 않은지 확인
    if not df_summary.empty:
        col_chart, col_table = st.columns([1.5, 1])
        
        with col_chart:
            # 차트 그리기
            fig = px.bar(df_summary, x='Ticker', y='Change (%)', color='Category', 
                         text='Change (%)', title="실시간 자산 변동률 (%)",
                         color_discrete_map={'Defense (방어)': '#2ecc71', 
                                             'Core (핵심)': '#3498db', 
                                             'Satellite (위성)': '#e74c3c'})
            fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        
        with col_table:
            st.markdown("##### 📋 상세 시세표")
            # 보기 좋게 포맷팅
            display_df = df_summary[['Ticker', 'Price ($)', 'Change (%)', 'Volume']].copy()
            
            # 포맷팅 적용 (문자열 변환)
            display_df['Price ($)'] = display_df['Price ($)'].apply(lambda x: f"{x:,.2f}")
            display_df['Change (%)'] = display_df['Change (%)'].apply(lambda x: f"{x:+.2f}")
            display_df['Volume'] = display_df['Volume'].apply(lambda x: f"{x:,.0f}")
            
            st.dataframe(display_df, hide
