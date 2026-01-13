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
# Tab 2: 보수적 가치 나침반 (Auto-Fetch Ver.)
# ==========================================
with tab2:
    st.markdown("""
    > **"숫자로 기다리는 인간이 되어라."** > 기계가 가져온 숫자를 맹신하지 말고, 반드시 **단위와 예외 항목**을 검증하십시오.
    """)
    
    col_input, col_result = st.columns([1, 1.2])

    with col_input:
        st.subheader("Step 0. 기초 데이터 입력")
        
        # 1. 티커 입력 및 자동 로드 버튼 구성
        c_tick, c_btn = st.columns([2, 1])
        target_ticker = c_tick.text_input("종목 티커 (예: 005930.KS, AAPL)", value="005930.KS")
        
        # 세션 상태 초기화 (데이터 로드용)
        if 'f_data' not in st.session_state:
            st.session_state.f_data = {
                'oi_1': 0.0, 'oi_2': 0.0, 'oi_3': 0.0,
                'debt': 0.0, 'cash': 0.0, 'shares': 0.0,
                'currency': 'KRW', 'loaded': False
            }

        # [자동 불러오기 버튼 로직]
        if c_btn.button("📥 데이터 가져오기"):
            try:
                with st.spinner(f"{target_ticker} 재무제표 분석 중..."):
                    stock = yf.Ticker(target_ticker)
                    
                    # 1) 손익계산서 (연간) - 최근 3년 영업이익
                    financials = stock.financials
                    # 'Operating Income' 또는 'Operating Profit' 등 필드명 찾기
                    oi_row_name = next((idx for idx in financials.index if 'Operating' in idx and ('Income' in idx or 'Profit' in idx)), None)
                    
                    if oi_row_name is not None and len(financials.columns) >= 3:
                        # 최신순으로 정렬되어 있으므로 0, 1, 2 인덱스 사용
                        # 단위 변환: 억 원(KRW) 또는 백만 달러(USD) 기준으로 조정 필요
                        # 야후는 기본 단위(원, 달러)로 줌 -> 편의상 '억' 단위로 나누기 (한국 주식 가정 시)
                        
                        currency = stock.info.get('currency', 'KRW')
                        unit_div = 100000000 if currency == 'KRW' else 1000000 # 한국은 억, 미국은 백만 기준
                        
                        vals = financials.loc[oi_row_name].iloc[:3].values
                        st.session_state.f_data['oi_3'] = float(vals[0] / unit_div) # 올해(최신)
                        st.session_state.f_data['oi_2'] = float(vals[1] / unit_div) # 1년전
                        st.session_state.f_data['oi_1'] = float(vals[2] / unit_div) # 2년전
                        st.session_state.f_data['currency'] = currency
                    
                    # 2) 재무상태표 - 차입금, 현금
                    bs = stock.balance_sheet
                    # 총차입금 (Total Debt)
                    debt_name = next((idx for idx in bs.index if 'Total Debt' in idx), None)
                    if debt_name:
                        st.session_state.f_data['debt'] = float(bs.loc[debt_name].iloc[0] / unit_div)
                    
                    # 현금성자산 (Cash And Cash Equivalents)
                    cash_name = next((idx for idx in bs.index if 'Cash' in idx and 'Equivalents' in idx), None)
                    if cash_name:
                        st.session_state.f_data['cash'] = float(bs.loc[cash_name].iloc[0] / unit_div)
                    
                    # 3) 주식수
                    st.session_state.f_data['shares'] = float(stock.info.get('sharesOutstanding', 0))
                    st.session_state.f_data['loaded'] = True
                    
                    st.success(f"데이터 로드 완료! (단위: {currency})")
            
            except Exception as e:
                st.error(f"데이터 로드 실패: {e}")

        # --- 예외 처리 규칙 (봉인) ---
        st.markdown("##### ❌ 예외 처리 (봉인 규칙)")
        is_finance = st.checkbox("금융업 (은행/보험/증권) 입니까?")
        is_platform = st.checkbox("플랫폼/네트워크 기업 (이익 왜곡) 입니까?")
        is_turnaround = st.checkbox("적자 → 흑자 전환 기업입니까?")
        
        if is_finance or is_platform or is_turnaround:
            st.error("🚫 **[분석 불가]** 나침반 사용 금지 대상입니다.")
            st.stop()
            
        st.divider()
        
        # --- 재무 데이터 입력 (자동 로드된 값 바인딩) ---
        # 로드된 데이터가 있으면 default value로 사용
        d = st.session_state.f_data
        unit_label = "억 원" if d['currency'] == 'KRW' else "백만 달러/기타"

        st.markdown(f"##### 📄 손익계산서 (단위: {unit_label})")
        oi_y1 = st.number_input("2년 전 영업이익", value=d['oi_1'])
        oi_y2 = st.number_input("1년 전 영업이익", value=d['oi_2'])
        oi_y3 = st.number_input("최근(올해) 영업이익", value=d['oi_3'])
        
        st.markdown(f"##### 📄 주석 및 재무상태표")
        one_off_cost = st.number_input("구조조정 등 일회성 비용 (+) [수동입력 필수]", value=0.0, help="재무제표 주석을 확인하여 직접 입력해야 합니다.")
        total_debt = st.number_input("총차입금 (Total Debt)", value=d['debt'])
        cash_equiv = st.number_input("현금성자산 (Cash & Equivalents)", value=d['cash'])
        total_shares = st.number_input("완전희석 주식수 (단위: 주)", value=d['shares'], format="%.0f")

    with col_result:
        st.subheader("🏁 가치 산출 및 판정")
        
        # Step 1. 최악의 해 정상화 이익
        worst_oi_raw = min(oi_y1, oi_y2, oi_y3)
        normalized_oi = worst_oi_raw + one_off_cost
        
        # Step 2. 보수적 배수
        target_multiple = st.slider("Step 2. 적용 멀티플 (보수적: 5~6)", 3, 10, 5)
        
        # 계산 로직
        ev = normalized_oi * target_multiple 
        net_debt = total_debt - cash_equiv
        equity_value = ev - net_debt
        
        # 주당 가치 계산 (단위 보정 로직)
        # 한국(KRW): (억 원 * 1억) / 주식수 = 원
        # 미국(USD): (백만 달러 * 100만) / 주식수 = 달러
        unit_multiplier = 100000000 if d['currency'] == 'KRW' else 1000000
        
        if total_shares > 0:
            final_fair_value = (equity_value * unit_multiplier) / total_shares
        else:
            final_fair_value = 0

        # 결과 표시
        st.markdown(f"""
        #### 📐 계산 결과 ({d['currency']})
        1. **최악의 해 영업이익:** {worst_oi_raw:,.1f} 
        2. **정상화 이익 (Normalized):** {normalized_oi:,.1f}
        3. **기업가치 (EV):** {ev:,.1f}
        4. **순차입금:** {net_debt:,.1f}
        5. **자기자본 가치:** {equity_value:,.1f}
        """)
        
        st.divider()
        st.markdown(f"### 👑 보수적 적정 주가: **{final_fair_value:,.0f}**")

        # Step 5. 진입 조건 판정
        # 현재가 가져오기 (자동)
        current_price = 0.0
        if target_ticker:
            try:
                current_price = yf.Ticker(target_ticker).history(period="1d")['Close'].iloc[-1]
            except:
                pass
        
        current_price_input = st.number_input("현재 주가 (비교용)", value=float(current_price))
        
        if current_price_input > 0:
            discount_rate = (final_fair_value - current_price_input) / final_fair_value * 100
            
            st.metric("현재 안전마진 (Discount Rate)", f"{discount_rate:.1f}%")
            
            if discount_rate > 30:
                st.success("✅ **[진입 승인]** 안전마진 30% 초과. (3개월 유지 여부 체크 필요)")
            elif discount_rate > 0:
                st.warning("⚠️ **[관망]** 저평가 구간이나 안전마진(30%) 부족.")
            else:
                st.error("⛔ **[진입 금지]** 현재 주가가 보수적 가치보다 비쌉니다.")
