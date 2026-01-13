import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. 기본 설정
st.set_page_config(page_title="Hybrid Barbell & Value Compass", layout="wide")
st.title("🛡️ 하이브리드 바벨 & 가치 나침반")

tab1, tab2 = st.tabs(["📊 포트폴리오 모니터", "🧭 보수적 가치 나침반"])

# ==========================================
# Tab 1: 포트폴리오 모니터 (안전 모드)
# ==========================================
with tab1:
    assets = {
        'Defense (방어)': ['COST', 'WM', 'XLV'],
        'Core (핵심)': ['MSFT', 'GOOGL'],
        'Satellite (위성)': ['VRT', 'ETN']
    }
    
    @st.cache_data(ttl=3600)
    def fetch_data_safe():
        data_list = []
        vix_val, vix_chg = 0.0, 0.0
        
        # 자산 데이터 개별 수집
        for cat, tickers in assets.items():
            for t in tickers:
                try:
                    df = yf.Ticker(t).history(period="5d")
                    if len(df) >= 2:
                        curr = df['Close'].iloc[-1]
                        prev = df['Close'].iloc[-2]
                        pct = (curr - prev) / prev * 100
                        vol = df['Volume'].iloc[-1]
                        data_list.append([cat, t, curr, pct, vol])
                except:
                    continue
        
        # VIX 수집
        try:
            v_df = yf.Ticker('^VIX').history(period="5d")
            if len(v_df) >= 2:
                vix_val = v_df['Close'].iloc[-1]
                vix_chg = (vix_val - v_df['Close'].iloc[-2]) / v_df['Close'].iloc[-2] * 100
        except:
            pass
            
        return pd.DataFrame(data_list, columns=['Category', 'Ticker', 'Price', 'Change', 'Volume']), vix_val, vix_chg

    # 데이터 실행
    try:
        df_res, v_val, v_chg = fetch_data_safe()
    except:
        st.error("데이터 수집 실패")
        st.stop()

    # 화면 표시
    st.header("1. Risk Monitor")
    c1, c2 = st.columns(2)
    status = "🔴 위험 (Cash Up!)" if v_val > 20 else "🟢 안전 (Invest)"
    c1.metric("VIX (공포지수)", f"{v_val:.2f}", f"{v_chg:.2f}%", delta_color="inverse")
    c2.info(f"💡 시장 상태: **{status}**")
    
    st.divider()
    st.header("2. Portfolio Status")
    
    if not df_res.empty:
        col_chart, col_table = st.columns([1.5, 1])
        with col_chart:
            fig = px.bar(df_res, x='Ticker', y='Change', color='Category', text='Change', title="실시간 변동률(%)")
            fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        with col_table:
            st.markdown("##### 📋 상세 시세표")
            # 포맷팅 후 출력 (오류 방지를 위해 단순화)
            show_df = df_res.copy()
            show_df['Price'] = show_df['Price'].apply(lambda x: f"{x:,.2f}")
            show_df['Change'] = show_df['Change'].apply(lambda x: f"{x:+.2f}%")
            show_df['Volume'] = show_df['Volume'].apply(lambda x: f"{x:,.0f}")
            st.dataframe(show_df, hide_index=True, use_container_width=True)
    else:
        st.warning("데이터를 불러오지 못했습니다.")

# ==========================================
# Tab 2: 가치 나침반 (로직 검증 완료)
# ==========================================
with tab2:
    st.markdown("> **\"숫자로 기다리는 인간이 되어라.\"**")
    
    col_input, col_result = st.columns([1, 1.2])
    
    with col_input:
        st.subheader("Step 0. 데이터 입력")
        c_t, c_b = st.columns([2, 1])
        ticker = c_t.text_input("티커", value="005930.KS")
        
        # 세션 초기화
        if 'fd' not in st.session_state:
            st.session_state.fd = {'o1':0.0, 'o2':0.0, 'o3':0.0, 'd':0.0, 'c':0.0, 's':0.0, 'cur':'KRW'}

        # 자동 데이터 로드
        if c_b.button("📥 데이터 가져오기"):
            try:
                with st.spinner("분석 중..."):
                    tk = yf.Ticker(ticker)
                    inf = tk.info
                    cur = inf.get('currency', 'KRW')
                    div = 100000000 if cur == 'KRW' else 1000000
                    
                    fs = tk.financials
                    if fs is not None and not fs.empty:
                        # 영업이익 찾기 (단순화)
                        for idx in fs.index:
                            if 'Operating' in str(idx) and ('Income' in str(idx) or 'Profit' in str(idx)):
                                vals = fs.loc[idx].values[:3]
                                if len(vals) > 0: st.session_state.fd['o3'] = float(vals[0]/div)
                                if len(vals) > 1: st.session_state.fd['o2'] = float(vals[1]/div)
                                if len(vals) > 2: st.session_state.fd['o1'] = float(vals[2]/div)
                                break
                    
                    bs = tk.balance_sheet
                    if bs is not None and not bs.empty:
                        # 부채/현금 찾기
                        for idx in bs.index:
                            if 'Total Debt' in str(idx):
                                st.session_state.fd['d'] = float(bs.loc[idx].iloc[0]/div)
                            if 'Cash' in str(idx) and 'Equivalents' in str(idx):
                                st.session_state.fd['c'] = float(bs.loc[idx].iloc[0]/div)
                    
                    st.session_state.fd['s'] = float(inf.get('sharesOutstanding', 0))
                    st.session_state.fd['cur'] = cur
                    st.success("로드 완료")
            except Exception as e:
                st.error(f"실패: {e}")

        # 입력 필드
        if st.checkbox("금융/플랫폼/적자전환 기업 (체크 시 중단)"):
            st.error("분석 불가")
            st.stop()

        d = st.session_state.fd
        u_label = "억 원" if d['cur'] == 'KRW' else "백만 달러"
        
        st.markdown(f"**단위: {u_label}**")
        o1 = st.number_input("2년전 영업이익", value=d['o1'])
        o2 = st.number_input("1년전 영업이익", value=d['o2'])
        o3 = st.number_input("최근 영업이익", value=d['o3'])
        one_off = st.number_input("일회성 비용 (+)", value=0.0)
        debt = st.number_input("총차입금", value=d['d'])
        cash = st.number_input("현금성자산", value=d['c'])
        shares = st.number_input("주식수", value=d['s'], format="%.0f")

    with col_result:
        st.subheader("🏁 가치 판정")
        
        worst = min(o1, o2, o3)
        norm = worst + one_off
        mul = st.slider("멀티플", 3, 10, 5)
        
        ev = norm * mul
        net_debt = debt - cash
        eq_val = ev - net_debt
        
        # 주당가치 계산
        u_mul = 100000000 if d['cur'] == 'KRW' else 1000000
        final = (eq_val * u_mul) / shares if shares > 0 else 0
        
        st.info(f"""
        1. 정상화 이익: {norm:,.1f} (최악 {worst:,.1f})
        2. 기업가치: {ev:,.1f}
        3. 자기자본가치: {eq_val:,.1f}
        """)
        
        st.markdown(f"### 👑 적정가: **{final:,.0f}**")
        
        curr_p = st.number_input("현재 주가", value=0.0)
        # 현재가 자동 로드
        if curr_p == 0 and ticker:
            try:
                h = yf.Ticker(ticker).history(period='1d')
                if not h.empty: curr_p = h['Close'].iloc[-1]
            except: pass
            
        if curr_p > 0 and final > 0:
            margin = (final - curr_p) / final * 100
            st.metric("안전마진", f"{margin:.1f}%")
            if margin > 30:
                st.success("✅ [진입 승인] 안전마진 30% 초과")
            elif margin > 0:
                st.warning("⚠️ [관망] 마진 부족")
            else:
                st.error("⛔ [진입 금지] 고평가")
        elif final <= 0:
            st.error("적정가가 0 이하입니다.")
