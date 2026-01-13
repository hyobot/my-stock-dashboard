import streamlit as st
import yfinance as yf
import pandas as pd
import streamlit.components.v1 as components

# -----------------------------------------------------------------------------
# 1. 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Hybrid Dashboard", layout="wide")
st.title("🛡️ 하이브리드 바벨 & 가치 나침반")

tab1, tab2 = st.tabs(["📊 차트 & 포트폴리오", "🧭 보수적 가치 나침반"])

# =============================================================================
# Tab 1: 트레이딩뷰 & 시세
# =============================================================================
with tab1:
    assets = {
        'Defense': ['COST', 'WM', 'XLV'],
        'Core': ['MSFT', 'GOOGL'],
        'Satellite': ['VRT', 'ETN']
    }
    all_tickers = [t for cat in assets.values() for t in cat] + ['^VIX', '^TNX', '005930.KS']

    col_chart, col_list = st.columns([3, 1])

    # [좌측] 트레이딩뷰 차트
    with col_chart:
        st.subheader("📈 실시간 차트 (TradingView)")
        selected_ticker = st.selectbox("종목 선택", all_tickers, index=3)

        def get_tv_symbol(t):
            if t.endswith('.KS'): return f"KRX:{t.replace('.KS','')}"
            if t.endswith('.KQ'): return f"KOSDAQ:{t.replace('.KQ','')}"
            if t == '^VIX': return "CBOE:VIX"
            if t == '^TNX': return "TVC:TNX"
            return t

        tv_sym = get_tv_symbol(selected_ticker)

        html_code = f"""
        <div class="tradingview-widget-container">
          <div id="tradingview_chart"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget(
          {{
            "width": "100%",
            "height": 600,
            "symbol": "{tv_sym}",
            "interval": "D",
            "timezone": "Asia/Seoul",
            "theme": "light",
            "style": "1",
            "locale": "kr",
            "toolbar_bg": "#f1f3f6",
            "enable_publishing": false,
            "allow_symbol_change": true,
            "container_id": "tradingview_chart"
          }});
          </script>
        </div>
        """
        components.html(html_code, height=610)

    # [우측] 시세 리스트
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
                st.info("데이터 로딩 중...")
        except:
            st.error("시세 로드 실패")

# =============================================================================
# Tab 2: 가치 나침반
# =============================================================================
with tab2:
    st.markdown("> **\"숫자로 기다리는 인간이 되어라.\"**")
    
    c_input, c_calc = st.columns([1, 1.2])

    # 1. 입력부
    with c_input:
        st.subheader("Step 0. 데이터 입력")
        t_col, b_col = st.columns([2,1])
        target = t_col.text_input("티커 입력", value="005930.KS")
        
        if 'val_data' not in st.session_state:
            st.session_state.val_data = {
                'o1':0.0, 'o2':0.0, 'o3':0.0, 
                'debt':0.0, 'cash':0.0, 'shares':0.0, 'curr_p':0.0, 'cur':'KRW'
            }

        # [데이터 가져오기 버튼]
        if b_col.button("📥 데이터 가져오기"):
            try:
                with st.spinner("로딩 중..."):
                    tk = yf.Ticker(target)
                    info = tk.info
                    cur = info.get('currency', 'KRW')
                    
                    # 화폐 단위 설정 (한 줄로 작성하여 에러 방지)
                    if cur == 'KRW':
                        div = 100000000
                    else:
                        div = 1000000
                    
                    # 1. 손익계산서
                    fs = tk.financials
                    if fs is not None and not fs.empty:
                        row = next((i for i in fs.index if 'Operating' in str(i) and ('Income' in str(i) or 'Profit' in str(i))), None)
                        if row:
                            vals = fs.loc[row].values[:3]
                            if len(vals)>0: st.session_state.val_data['o3'] = float(vals[0]/div)
                            if len(vals)>1: st.session_state.val_data['o2'] = float(vals[1]/div)
                            if len(vals)>2: st.session_state.val_data['o1'] = float(vals[2]/div)
                    
                    # 2. 대차대조표
                    bs = tk.balance_sheet
                    if bs is not None and not bs.empty:
                        d_row = next((i for i in bs.index if 'Total Debt' in str(i)), None)
                        if d_row: 
                            st.session_state.val_data['debt'] = float(bs.loc[d_row].iloc[0]/div)
                        
                        c_row = next((i for i in bs.index if 'Cash' in str(i) and 'Equivalents' in str(i)), None)
                        if c_row: 
                            st.session_state.val_data['cash'] = float(bs.loc[c_row].iloc[0]/div)
                    
                    # 3. 주식수 & 현재가
                    st.session_state.val_data['shares'] = float(info.get('sharesOutstanding', 0))
                    
                    try:
                        hist = tk.history(period='1d')
                        if not hist.empty:
                            st.session_state.val_data['curr_p'] = float(hist['Close'].iloc[-1])
                    except:
                        st.session_state.val_data['curr_p'] = 0.0

                    st.session_state.val_data['cur'] = cur
                    st.success("데이터 로드 완료")
            
            except Exception as e:
                st.error(f"로드 실패: {e}")

        # 사용자 입력 UI
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

    # 2. 판정부
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
                st.warning("⚠️ **[관망]** 저평가 상태이나 마진(30%) 부족")
            else:
                st.error("⛔ **[진입 금지]** 적정가보다 비쌈")
        
        elif fair_price <= 0:
            st.error("⚠️ 적정 주가 0 이하 (계산 불가)")
        else:
            st.warning("👈 데이터를 가져오거나 현재 주가를 입력하세요.")
