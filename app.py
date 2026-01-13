import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="Hybrid Barbell & Value Compass", layout="wide")
st.title("🛡️ 하이브리드 바벨 & 가치 나침반")

# 탭 분리: 모니터링 vs 가치 계산기
tab1, tab2 = st.tabs(["📊 포트폴리오 모니터", "🧭 보수적 가치 나침반"])

# ==========================================
# Tab 1: 기존 포트폴리오 모니터링 기능
# ==========================================
with tab1:
    # 1. 자산 및 설정
    assets = {
        'Defense (좌측-방어)': ['COST', 'WM', 'XLV'],
        'Core (우측-핵심)': ['MSFT', 'GOOGL'],
        'Satellite (우측-위성)': ['VRT', 'ETN']
    }
    risk_tickers = {'VIX': '^VIX', '10Y Yield': '^TNX'}
    all_tickers = [t for cat in assets.values() for t in cat] + list(risk_tickers.values())

    # 2. 데이터 가져오기
    @st.cache_data(ttl=60)
    def fetch_market_data():
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
                chg = latest['Close'] - prev['Close']
                pct_chg = (chg / prev['Close']) * 100
                
                rows.append({
                    'Category': cat, 'Ticker': t,
                    'Price ($)': round(latest['Close'], 2),
                    'Change (%)': round(pct_chg, 2)
                })
            except KeyError:
                continue
    df_summary = pd.DataFrame(rows)

    # 3. 화면 구성 (Risk Monitor)
    st.header("1. Risk Monitor")
    c1, c2 = st.columns(2)
    vix_df = raw_data['^VIX']
    vix_curr = vix_df['Close'].iloc[-1]
    status = "🔴 위험 (Cash Up!)" if vix_curr > 20 else "🟢 안전 (Invest)"
    c1.metric("VIX (공포지수)", f"{vix_curr:.2f}", delta_color="inverse")
    c2.info(f"💡 시장 상태: **{status}**")

    st.divider()

    # 4. 포트폴리오 차트
    st.header("2. Portfolio Status")
    if not df_summary.empty:
        fig = px.bar(df_summary, x='Ticker', y='Change (%)', color='Category', 
                     text='Change (%)', title="실시간 자산 변동률 (%)",
                     color_discrete_map={'Defense (좌측-방어)': '#2ecc71', 'Core (우측-핵심)': '#3498db', 'Satellite (우측-위성)': '#e74c3c'})
        fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# Tab 2: 보수적 가치 나침반 (신규 기능)
# ==========================================
with tab2:
    st.markdown("""
    > **"이제 말로 하는 투자는 끝이다. 숫자로 기다리는 인간이 되어라."** > 이 나침반은 기회를 찾기 위한 도구가 아니라, **기다림을 끝내기 위한 문턱**입니다. [cite: 1, 11]
    """)
    
    col_input, col_result = st.columns([1, 1.2])

    with col_input:
        st.subheader("Step 0. 기초 데이터 입력")
        target_ticker = st.text_input("분석할 종목 티커 (예: 005930.KS, AAPL)", value="005930.KS")
        
        # --- 예외 처리 규칙 (봉인) ---
        st.markdown("##### ❌ 예외 처리 (봉인 규칙)")
        is_finance = st.checkbox("금융업 (은행/보험/증권) 입니까? [cite: 8]")
        is_platform = st.checkbox("플랫폼/네트워크 기업 (이익 왜곡) 입니까? [cite: 9]")
        is_turnaround = st.checkbox("적자 → 흑자 전환 기업입니까? [cite: 10]")
        
        if is_finance or is_platform or is_turnaround:
            st.error("🚫 **[분석 불가]** 나침반 사용 금지 대상입니다. 다른 밸류에이션 방법을 사용하십시오.")
            st.stop()
            
        st.divider()
        
        # --- 재무 데이터 입력 ---
        st.markdown("##### 📄 손익계산서 (단위: 억 원/백만 달러)")
        oi_y1 = st.number_input("2년 전 영업이익", value=1200)
        oi_y2 = st.number_input("1년 전 영업이익", value=800)
        oi_y3 = st.number_input("최근(올해) 영업이익", value=500)
        
        st.markdown("##### 📄 주석 및 재무상태표")
        one_off_cost = st.number_input("구조조정 등 일회성 비용 (+)", value=100, help="영업이익에 더해줄 일회성 비용")
        total_debt = st.number_input("총차입금 (Total Debt)", value=3000)
        cash_equiv = st.number_input("현금성자산 (Cash & Equivalents)", value=1000)
        total_shares = st.number_input("완전희석 주식수 (단위: 주)", value=100000000)

    with col_result:
        st.subheader("🏁 가치 산출 및 판정")
        
        # Step 1. 최악의 해 정상화 이익
        worst_oi_raw = min(oi_y1, oi_y2, oi_y3)
        normalized_oi = worst_oi_raw + one_off_cost
        
        # Step 2. 보수적 배수 (Default 5)
        target_multiple = st.slider("Step 2. 적용 멀티플 (보수적: 5~6)", 3, 10, 5) # [cite: 5]
        
        # 계산 로직
        ev = normalized_oi * target_multiple # Enterprise Value
        net_debt = total_debt - cash_equiv   # 순차입금
        equity_value = ev - net_debt         # 자기자본 가치
        
        if total_shares > 0:
            conservative_price = equity_value / total_shares * 100000000 # 단위 보정(억 원 기준이면 * 1억) -> 여기서는 사용자가 단위를 맞췄다고 가정
            # 편의상 입력값이 '억 원' 단위이고 주식수가 '주' 단위면 -> (억 / 주) * 1억 = 원
            # 🚨 중요: 사용자가 단위를 헷갈릴 수 있으므로, 단순 나눗셈 후 단위 보정 옵션 제공
            
            # (단위 보정 로직: 입력값이 억 원 단위라고 가정)
            final_fair_value = (equity_value * 100000000) / total_shares
        else:
            final_fair_value = 0

        # 결과 표시 카드
        st.markdown(f"""
        #### 📐 계산 결과
        1. **최악의 해 영업이익:** {worst_oi_raw:,.0f} 
        2. **정상화 이익 (Normalized):** {normalized_oi:,.0f} 
        3. **기업가치 (EV):** {ev:,.0f} (멀티플 {target_multiple}배)
        4. **순차입금:** {net_debt:,.0f}
        5. **자기자본 가치:** {equity_value:,.0f}
        """)
        
        st.divider()
        st.markdown(f"### 👑 보수적 적정 주가: **{final_fair_value:,.0f} 원(달러)**")

        # Step 5. 진입 조건 판정 (현재가 비교) 
        current_price_input = st.number_input("현재 주가 입력 (비교용)", value=6800)
        
        if current_price_input > 0:
            discount_rate = (final_fair_value - current_price_input) / final_fair_value * 100
            
            st.metric("현재 안전마진 (Discount Rate)", f"{discount_rate:.1f}%")
            
            if discount_rate > 30:
                st.success("✅ **[진입 승인]** 안전마진 30% 초과. 기다림 종료 규칙 발동. (단, 3개월 유지 체크 필요)")
            elif discount_rate > 0:
                st.warning("⚠️ **[관망]** 저평가 구간이나 안전마진(30%) 부족.")
            else:
                st.error("⛔ **[진입 금지]** 현재 주가가 보수적 가치보다 비쌉니다.")
        
        st.info("※ 주의: 모든 입력 단위(억 원, 달러 등)는 통일해서 입력해야 정확한 결과가 나옵니다.")
