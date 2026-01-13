import streamlit as st
import yfinance as yf
import pandas as pd
import streamlit.components.v1 as components

# -----------------------------------------------------------------------------
# 1. 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Hybrid Dashboard", layout="wide")
st.title("🛡️ 하이브리드 바벨 & 가치 나침반 (Final Fix)")

tab1, tab2, tab3 = st.tabs(["📊 고급 차트 & 포트폴리오", "🧭 보수적 가치 나침반", "🌸 AI 인프라 재무 필터"])

# =============================================================================
# Tab 1: 트레이딩뷰 고급 차트
# =============================================================================
with tab1:
    assets = {
        'Defense': ['COST', 'WM', 'XLV'],
        'Core': ['MSFT', 'GOOGL'],
        'Satellite': ['VRT', 'ETN']
    }
    all_tickers = [t for cat in assets.values() for t in cat] + ['^VIX', '^TNX', '005930.KS']

    col_chart, col_list = st.columns([3, 1])

    with col_chart:
        st.subheader("📈 트레이딩뷰 차트")
        selected_ticker = st.selectbox("종목 선택", all_tickers, index=3)

        def get_tv_symbol(t):
            if t.endswith('.KS'): return f"KRX:{t.replace('.KS','')}"
            if t.endswith('.KQ'): return f"KOSDAQ:{t.replace('.KQ','')}"
            if t == '^VIX': return "CBOE:VIX"
            if t == '^TNX': return "TVC:TNX"
            return t 

        tv_sym = get_tv_symbol(selected_ticker)

        # 고급 차트 위젯 (JavaScript)
        html_code = f"""
        <div class="tradingview-widget-container" style="height:500px;width:100%">
          <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
          {{
          "autosize": true,
          "symbol": "{tv_sym}",
          "interval": "D",
          "timezone": "Asia/Seoul",
          "theme": "light",
          "style": "1",
          "locale": "kr",
          "enable_publishing": false,
          "allow_symbol_change": true,
          "support_host": "https://www.tradingview.com"
        }}
          </script>
        </div>
        """
        components.html(html_code, height=510)

    with col_list:
        st.subheader("📋 시세 요약")
        if st.button("새로고침"):
            st.cache_data.clear()

        @st.cache_data(ttl=3600)
        def get_prices():
            data = []
            for cat, ts in assets.items():
                for t in ts:
                    try:
                        h = yf.Ticker(t).history(period='2d')
                        if len(h)>=2:
                            now = h['Close'].iloc[-1]
                            prev = h['Close'].iloc[-2]
                            pct = (now - prev)/prev*100
                            data.append([t, now, pct])
                    except: continue
            return pd.DataFrame(data, columns=['Ticker', 'Price', 'Chg'])

        try:
            df = get_prices()
            if not df.empty:
                st.dataframe(
                    df.style.format({'Price':'{:.2f}', 'Chg':'{:+.2f}%'})
                      .applymap(lambda x: 'color:red' if x<0 else 'color:green', subset=['Chg']),
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("로딩 중...")
        except:
            st.error("API 제한")

# =============================================================================
# Tab 2: 가치 나침반
# =============================================================================
with tab2:
    st.markdown("> **\"숫자로 기다리는 인간이 되어라.\"**")
    
    c_input, c_calc = st.columns([1, 1.2])

    with c_input:
        st.subheader("Step 0. 데이터 입력")
        t_col, b_col = st.columns([2,1])
        target = t_col.text_input("티커 입력", value="005930.KS")
        
        if 'val_data' not in st.session_state:
            st.session_state.val_data = {
                'o1':0.0, 'o2':0.0, 'o3':0.0, 
                'debt':0.0, 'cash':0.0, 'shares':0.0, 'curr_p':0.0, 'cur':'KRW'
            }

        if b_col.button("📥 데이터 가져오기"):
            try:
                with st.spinner("로딩 중..."):
                    tk = yf.Ticker(target)
                    info = tk.info
                    cur = info.get('currency', 'KRW')
                    div = 100000000 if cur == 'KRW' else 1000000
                    
                    fs = tk.financials
                    if fs is not None and not fs.empty:
                        row = next((i for i in fs.index if 'Operating' in str(i) and ('Income' in str(i) or 'Profit' in str(i))), None)
                        if row:
                            vals = fs.loc[row].values[:3]
                            if len(vals)>0: st.session_state.val_data['o3'] = float(vals[0]/div)
                            if len(vals)>1: st.session_state.val_data['o2'] = float(vals[1]/div)
                            if len(vals)>2: st.session_state.val_data['o1'] = float(vals[2]/div)
                    
                    bs = tk.balance_sheet
                    if bs is not None and not bs.empty:
                        d_row = next((i for i in bs.index if 'Total Debt' in str(i)), None)
                        if d_row: st.session_state.val_data['debt'] = float(bs.loc[d_row].iloc[0]/div)
                        c_row = next((i for i in bs.index if 'Cash' in str(i) and 'Equivalents' in str(i)), None)
                        if c_row: st.session_state.val_data['cash'] = float(bs.loc[c_row].iloc[0]/div)
                    
                    st.session_state.val_data['shares'] = float(info.get('sharesOutstanding', 0))
                    try:
                        hist = tk.history(period='1d')
                        if not hist.empty:
                            st.session_state.val_data['curr_p'] = float(hist['Close'].iloc[-1])
                    except:
                        st.session_state.val_data['curr_p'] = 0.0

                    st.session_state.val_data['cur'] = cur
                    st.success("완료")
            except Exception as e:
                st.error(f"실패: {e}")

        d = st.session_state.val_data
        unit = "억 원" if d['cur'] == 'KRW' else "백만 달러"
        
        st.info(f"단위: {unit}")
        o1 = st.number_input("2년전 영업이익", value=d['o1'])
        o2 = st.number_input("1년전 영업이익", value=d['o2'])
        o3 = st.number_input("최근 영업이익", value=d['o3'])
        one_off = st.number_input("일회성 비용 (+) [필수]", value=0.0)
        debt = st.number_input("총차입금", value=d['debt'])
        cash = st.number_input("현금성자산", value=d['cash'])
        shares = st.number_input("주식수 (주)", value=d['shares'], format="%.0f")

    with c_calc:
        st.subheader("🏁 가치 판정 결과")
        worst_oi = min(o1, o2, o3)
        norm_oi = worst_oi + one_off
        multiple = st.slider("적용 멀티플 (보수적 5~6)", 3, 10, 5)
        ev = norm_oi * multiple
        net_debt = debt - cash
        eq_val = ev - net_debt
        u_mul = 100000000 if d['cur']=='KRW' else 1000000
        fair_price = (eq_val * u_mul) / shares if shares > 0 else 0
        
        st.markdown(f"""
        1. **정상화 이익:** {norm_oi:,.0f} (최악 {worst_oi:,.0f} + 조정 {one_off})
        2. **기업가치 (EV):** {ev:,.0f}
        3. **자기자본 가치:** {eq_val:,.0f}
        """)
        st.divider()
        st.markdown(f"### 👑 보수적 적정가: **{fair_price:,.0f}**")
        
        curr_p_input = st.number_input("현재 주가 입력 (비교용)", value=d['curr_p'])
        if curr_p_input > 0 and fair_price > 0:
            margin = (fair_price - curr_p_input) / fair_price * 100
            st.metric("현재 안전마진", f"{margin:.1f}%")
            if margin > 30:
                st.success("✅ **[진입 승인]** 안전마진 30% 확보됨")
                st.balloons()
            elif margin > 0:
                st.warning("⚠️ **[관망]** 마진 부족")
            else:
                over_pct = abs(margin)
                drop_needed = (curr_p_input - fair_price) / curr_p_input * 100
                st.error(f"""
                ⛔ **[진입 금지]** 적정가보다 **{over_pct:.1f}%** 비쌉니다.
                📉 현재가에서 **{drop_needed:.1f}% 하락**해야 진입 가능합니다.
                """)
        elif fair_price <= 0:
            st.error("⚠️ 적정 주가 0 이하 (계산 불가)")

# =============================================================================
# Tab 3: AI 인프라 재무 필터 (PEG 로직 강화)
# =============================================================================
with tab3:
    st.markdown("""
    ### 🌸 겨울을 견디고 봄에 보상받을 기업 (AI Infra Filter)
    """)
    
    col_f_in, col_f_res = st.columns([1, 2])
    
    with col_f_in:
        filter_ticker = st.text_input("검증할 티커 (예: VRT, ETN, MSFT)", value="VRT")
        run_btn = st.button("🔍 재무 건전성 정밀 진단")
        
        st.info("""
        **[진단 항목]**
        1. 부채 안정성 (Net Debt/EBITDA)
        2. 이자 감당 능력 (ICR)
        3. 현금 창출력 (FCF > Capex)
        4. 파산 저항성 (Altman Z-Score)
        5. 고객 집중도 (수동)
        6. 자본 효율성 (ROIC)
        7. 주주 친화성 (희석 여부)
        8. 진입 밸류에이션 (PEG)
        """)

    with col_f_res:
        if run_btn:
            try:
                with st.spinner(f"{filter_ticker} 정밀 분석 중..."):
                    stock = yf.Ticker(filter_ticker)
                    
                    # 데이터 수집 (안전장치 포함)
                    info = stock.info
                    bs = stock.balance_sheet
                    is_stmt = stock.financials
                    cf = stock.cashflow
                    
                    if bs.empty or is_stmt.empty:
                        st.error("❌ 재무 데이터를 불러올 수 없습니다. (API 제한 또는 데이터 없음)")
                        st.stop()

                    # --- [1] 부채 안정성 (Net Debt / EBITDA <= 2.5) ---
                    try:
                        total_debt = info.get('totalDebt', 0)
                        cash = info.get('totalCash', 0)
                        ebitda = info.get('ebitda', 1) # 0 나누기 방지
                        net_debt = total_debt - cash
                        ratio_1 = net_debt / ebitda
                        pass_1 = ratio_1 <= 2.5
                    except: ratio_1, pass_1 = 999, False

                    # --- [2] 이자 감당 능력 (EBIT / Interest >= 5.0) ---
                    try:
                        ebit = is_stmt.loc['EBIT'].iloc[0] if 'EBIT' in is_stmt.index else info.get('ebitda', 0)
                        interest = abs(is_stmt.loc['Interest Expense'].iloc[0]) if 'Interest Expense' in is_stmt.index else 1
                        ratio_2 = ebit / interest if interest != 0 else 0
                        pass_2 = ratio_2 >= 5.0
                    except: ratio_2, pass_2 = 0, False

                    # --- [3] 현금 창출력 (FCF > Capex) ---
                    try:
                        fcf = info.get('freeCashflow', 0)
                        capex = abs(cf.loc['Capital Expenditure'].iloc[0]) if 'Capital Expenditure' in cf.index else 0
                        pass_3 = fcf > capex
                        val_3 = f"FCF: {fcf/1e9:.1f}B / Capex: {capex/1e9:.1f}B"
                    except: pass_3, val_3 = False, "Data N/A"

                    # --- [4] Altman Z-Score (> 3.0) ---
                    try:
                        total_assets = bs.loc['Total Assets'].iloc[0]
                        total_liab = bs.loc['Total Liabilities Net Minority Interest'].iloc[0]
                        working_capital = bs.loc['Working Capital'].iloc[0] if 'Working Capital' in bs.index else (total_assets - total_liab)
                        retained_earnings = bs.loc['Retained Earnings'].iloc[0] if 'Retained Earnings' in bs.index else 0
                        market_cap = info.get('marketCap', 0)
                        sales = is_stmt.loc['Total Revenue'].iloc[0]

                        A = working_capital / total_assets
                        B = retained_earnings / total_assets
                        C = ebit / total_assets
                        D = market_cap / total_liab
                        E = sales / total_assets

                        z_score = (1.2*A) + (1.4*B) + (3.3*C) + (0.6*D) + (1.0*E)
                        pass_4 = z_score > 3.0
                    except: z_score, pass_4 = 0, False

                    # --- [5] 고객 집중도 ---
                    pass_5 = "Manual Check"
                    
                    # --- [6] 자본 효율성 (ROIC > 10%) ---
                    try:
                        tax_rate = 0.21
                        nopat = ebit * (1 - tax_rate)
                        invested_capital = (total_debt + info.get('marketCap', 0)) - cash
                        roic_cal = (nopat / invested_capital) * 100 if invested_capital else 0
                        pass_6 = roic_cal > 10.0
                    except: roic_cal, pass_6 = 0, False

                    # --- [7] 주주 친화성 ---
                    pass_7 = "Manual Check"

                    # --- [8] 밸류에이션 (PEG < 1.0) - 로직 강화 ---
                    try:
                        # 1차 시도: info에서 가져오기
                        peg = info.get('pegRatio', None)
                        
                        # 2차 시도: 직접 계산 (PER / Growth Rate)
                        if peg is None:
                            per = info.get('trailingPE', 0)
                            # 성장률 추정 (내년 EPS / 올해 EPS)
                            if 'forwardEps' in info and 'trailingEps' in info:
                                growth = ((info['forwardEps'] - info['trailingEps']) / info['trailingEps']) * 100
                                if growth > 0 and per > 0:
                                    peg = per / growth
                                else:
                                    peg = 99 # 적자거나 역성장
                            else:
                                peg = 99
                        
                        pass_8 = peg < 1.0
                    except: peg, pass_8 = 99, False

                    # ---------------- 결과 출력 ----------------
                    st.subheader(f"📊 {filter_ticker} 진단 결과")
                    
                    res_data = [
                        ["1. 부채 안정성", "Net Debt/EBITDA ≤ 2.5", f"{ratio_1:.2f}배", "✅ 통과" if pass_1 else "❌ 위험"],
                        ["2. 이자 감당 능력", "EBIT/Interest ≥ 5.0", f"{ratio_2:.1f}배", "✅ 통과" if pass_2 else "❌ 위험"],
                        ["3. 현금 창출력", "FCF > Capex", val_3, "✅ 통과" if pass_3 else "❌ 부족"],
                        ["4. 파산 저항성", "Altman Z-Score > 3.0", f"{z_score:.2f}", "✅ 안전" if pass_4 else "❌ 주의"],
                        ["5. 고객 집중도", "단일 고객 < 20%", "확인 불가", "⚠️ 수동 확인 (10-K)"],
                        ["6. 자본 효율성", "ROIC > 10% (WACC)", f"{roic_cal:.1f}%", "✅ 우수" if pass_6 else "❌ 저조"],
                        ["7. 주주 친화성", "희석 이력 없음", "API 한계", "⚠️ 수동 확인"],
                        ["8. 밸류에이션", "PEG < 1.0", f"{peg:.2f}", "✅ 저평가" if pass_8 else "❌ 고평가"]
                    ]
                    
                    res_df = pd.DataFrame(res_data, columns=["필터 항목", "기준", "현재 수치", "판정"])
                    st.table(res_df)
                    
                    success_cnt = sum([1 for x in [pass_1, pass_2, pass_3, pass_4, pass_6, pass_8] if x is True])
                    st.markdown(f"#### 💡 종합 점수: {success_cnt} / 6 (자동 진단 항목)")
                    
                    if success_cnt >= 5:
                        st.success("🏆 **[Top Tier]** 겨울을 견디고 봄을 맞이할 강력한 후보입니다.")
                    elif success_cnt >= 3:
                        st.warning("⚖️ **[Middle]** 일부 지표가 기준에 미달합니다. 정밀 분석이 필요합니다.")
                    else:
                        st.error("🥶 **[Winter Risk]** 재무적 기초체력이 약합니다. 신중한 접근이 필요합니다.")
                        
            except Exception as e:
                st.error(f"분석 중 오류 발생: {e}")
