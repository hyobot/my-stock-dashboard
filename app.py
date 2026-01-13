import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components # 트레이딩뷰 위젯용

# -----------------------------------------------------------------------------
# [기본 설정] 페이지 타이틀 및 레이아웃
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Hybrid Barbell & Value Compass", layout="wide")
st.title("🛡️ 하이브리드 바벨 & 가치 나침반 (TradingView Ver.)")

# 탭 분리
tab1, tab2 = st.tabs(["📊 차트 & 포트폴리오", "🧭 보수적 가치 나침반"])

# =============================================================================
# [Tab 1] 트레이딩뷰 차트 & 포트폴리오 현황
# =============================================================================
with tab1:
    # 1. 자산 목록 정의
    assets = {
        'Defense (방어)': ['COST', 'WM', 'XLV'],
        'Core (핵심)': ['MSFT', 'GOOGL'],
        'Satellite (위성)': ['VRT', 'ETN']
    }
    # 모든 티커 리스트
    all_tickers = [t for cat in assets.values() for t in cat] + ['^VIX', '^TNX', '005930.KS']

    # 2. 화면 구성 (2단 분할)
    col_chart, col_list = st.columns([2.5, 1])

    # ---------------------------------------------------------
    # [좌측] 트레이딩뷰 위젯 (핵심 기능)
    # ---------------------------------------------------------
    with col_chart:
        st.subheader("📈 TradingView Advanced Chart")
        
        # 차트 종목 선택기
        selected_ticker = st.selectbox("차트 확인할 종목 선택", all_tickers, index=3) # 기본값 MSFT

        # [함수] 야후 티커 -> 트레이딩뷰 심볼 변환
        def get_tv_symbol(ticker):
            # 1. 한국 주식 (005930.KS -> KRX:005930)
            if ticker.endswith('.KS'):
                return f"KRX:{ticker.split('.')[0]}"
            elif ticker.endswith('.KQ'):
                return f"KOSDAQ:{ticker.split('.')[0]}"
            
            # 2. 지수 및 특수 자산
            if ticker == '^VIX': return "CBOE:VIX"
            if ticker == '^TNX': return "TVC:TNX" # 미국 10년물 금리
            
            # 3. 미국 주식 (거래소 자동 매칭을 위해 티커만 보냄, 필요시 NASDAQ: 등 붙임)
            return ticker 

        tv_symbol = get_tv_symbol(selected_ticker)

        # 트레이딩뷰 위젯 HTML 코드
        tv_html = f"""
        <div class="tradingview-widget-container">
          <div id="tradingview_12345"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget(
          {{
            "width": "100%",
            "height": 500,
            "symbol": "{tv_symbol}",
            "interval": "D",
            "timezone": "Asia/Seoul",
            "theme": "light",
            "style": "1",
            "locale": "kr",
            "toolbar_bg": "#f1f3f6",
            "enable_publishing": false,
            "allow_symbol_change": true,
            "container_id": "tradingview_12345"
          }});
          </script>
        </div>
        """
        # HTML 렌더링
        components.html(tv_html, height=500)
        st.caption("※ 차트 내에서 지표 추가, 작도, 줌인/아웃이 모두 가능합니다.")

    # ---------------------------------------------------------
    # [우측] 기존 포트폴리오 시세표 (yfinance 사용 - Safe Mode)
    # ---------------------------------------------------------
    with col_list:
        st.subheader("📋 포트폴리오 요약")
        
        if st.button("시세 새로고침 (yfinance)"):
            st.cache_data.clear() # 캐시 삭제 후 재로딩

        @st.cache_data(ttl=3600) # 1시간 캐시 (차단 방지)
        def fetch_summary():
            data = []
            for cat, tickers in assets.items():
                for t in tickers:
                    try:
                        df = yf.Ticker(t).history(period='2d')
                        if len(df) >= 2:
                            curr = df['Close'].iloc[-1]
                            prev = df['Close'].iloc[-2]
                            pct = (curr - prev)/prev * 100
                            data.append({'종목': t, '등락률': pct, '현재가': curr, '그룹': cat})
                    except: continue
            return pd.DataFrame(data)

        try:
            df_summ = fetch_summary()
            if not df_summ.empty:
                # 간단한 테이블로 표시
                st.dataframe(
                    df_summ.style.format({'등락률': '{:+.2f}%', '현재가': '{:,.2f}'})
                           .applymap(lambda x: 'color: red' if x < 0 else 'color: green', subset=['등락률']),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("데이터 로드 중...")
        except:
            st.error("시세 로드 실패")

# =============================================================================
# [Tab 2] 보수적 가치 나침반 (기존 코드 유지)
# =============================================================================
with tab2:
    st.markdown("> **\"숫자로 기다리는 인간이 되어라.\"**")
    
    col_input, col_result = st.columns([1, 1.2])
    
    with col_input:
        st.subheader("Step 0. 데이터 입력")
        c_t, c_b = st.columns([2, 1])
        ticker = c_t.text_input("티커", value="005930.KS")
        
        if 'fd' not in st.session_state:
            st.session_state.fd = {'o1':0.0, 'o2':0.0, 'o3':0.0, 'd':0.0, 'c':0.0, 's':0.0, 'cur':'KRW'}

        if c_b.button("📥 데이터 가져오기 (Tab2)"):
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
