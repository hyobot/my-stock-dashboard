import streamlit as st
import yfinance as yf
import pandas as pd
import streamlit.components.v1 as components # 트레이딩뷰용

# -----------------------------------------------------------------------------
# 1. 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Hybrid Dashboard", layout="wide")
st.title("🛡️ 하이브리드 바벨 & 가치 나침반 (Final Fix)")

# 탭 구성
tab1, tab2 = st.tabs(["📊 차트 & 포트폴리오", "🧭 보수적 가치 나침반"])

# =============================================================================
# Tab 1: 트레이딩뷰 (화면 안나옴 해결)
# =============================================================================
with tab1:
    # 1. 자산 목록
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
        selected_ticker = st.selectbox("종목 선택", all_tickers, index=3) # MSFT 기본

        # 트레이딩뷰용 심볼 변환 함수
        def get_tv_symbol(t):
            if t.endswith('.KS'): return f"KRX:{t.replace('.KS','')}"
            if t.endswith('.KQ'): return f"KOSDAQ:{t.replace('.KQ','')}"
            if t == '^VIX': return "CBOE:VIX"
            if t == '^TNX': return "TVC:TNX"
            return t # 미국주식

        tv_sym = get_tv_symbol(selected_ticker)

        # HTML 높이 강제 지정 (height=600)
        # 트레이딩뷰 위젯 코드
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
        # 여기서 height를 넉넉하게 주어야 화면에 보입니다.
        components.html(html_code, height=610)

    # [우측] 포트폴리오 시세 (간략화)
    with col_list:
        st.subheader("📋 시세 요약")
        if st.button("시세 새로고침"):
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
            st.error("시세 로드 실패 (API 제한)")

# =============================================================================
# Tab 2: 가치 나침반 (판정 기능 수리)
# =============================================================================
with tab2:
    st.markdown("> **\"숫자로 기다리는 인간이 되어라.\"**")
    
    c_input, c_calc = st.columns([1, 1.2])

    # ---------------------------------------------------------
    # 1. 입력부
    # ---------------------------------------------------------
    with c_input:
        st.subheader("Step 0. 데이터 입력")
        t_col, b_col = st.columns([2,1])
        target = t_col.text_input("티커 입력", value="005930.KS")
        
        # 세션 초기화
        if 'val_data' not in st.session_state:
            st.session_state.val_data = {
                'o1':0.0, 'o2':0.0, 'o3':0.0, 
                'debt':0.0, 'cash':0.0, 'shares':0.0, 'curr_p':0.0, 'cur':'KRW'
            }

        # 데이터 가져오기 버튼
        if b_col.button("📥 데이터 가져오기"):
            try:
                with st.spinner("로딩 중..."):
                    tk = yf.Ticker(target)
                    info = tk.info
                    cur = info.get('currency', 'KRW')
                    div = 1000000
