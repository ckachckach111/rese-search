import streamlit as st
import pandas as pd
import re

# CSV 불러오기 (인코딩 자동 처리)
@st.cache_data
def load_data():
    for enc in ["utf-8-sig", "cp949", "utf-8"]:
        try:
            return pd.read_csv("accounts.csv", encoding=enc)
        except Exception:
            continue
    st.error("CSV 파일을 불러올 수 없습니다. UTF-8 또는 CSV UTF-8 형식으로 저장해주세요.")
    return pd.DataFrame()

df = load_data()

# 열 이름 확인
expected_cols = ["번호", "한정", "가격", "캐릭터 목록"]
missing = [c for c in expected_cols if c not in df.columns]
if missing:
    st.error(f"CSV 열 이름이 맞지 않습니다. 누락된 열: {missing}")
    st.stop()

# 페이지 설정
st.set_page_config(page_title="계정 검색", layout="centered")

# CSS 스타일
st.markdown("""
    <style>
        .stTextInput { text-align: center; }
        div[data-testid="stTextInput"] label { display: none; }
        .block-container {
            display: flex; flex-direction: column;
            justify-content: center; align-items: center;
        }
        .stSlider { width: 400px; }
        .stNumberInput { width: 200px; }
        button[kind="primary"] {
            background-color: #007bff !important;
            color: white !important;
            border-radius: 10px !important;
            padding: 0.5em 1em !important;
        }
        /* ✅ 테이블 줄바꿈 & 넓이 조정 */
        div[data-testid="stDataFrame"] td:nth-child(4) {
            min-width: 450px !important;
            white-space: pre-wrap !important;
            word-break: break-word !important;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align:center;'>🎮 계정 검색</h2>", unsafe_allow_html=True)

# 세션 상태
if "search_clicked" not in st.session_state:
    st.session_state.search_clicked = False

# 검색창
query = st.text_input("", "", placeholder="예: 히마리 히카리 (띄어쓰기로 여러 캐릭터 검색)")
min_price, max_price = st.slider("가격대 (만원)", 0, 100, (0, 100), step=1)
min_limit = st.number_input("최소 한정 캐릭터 개수", min_value=0, max_value=100, value=0, step=1)

# 검색 버튼
if st.button("검색"):
    st.session_state.search_clicked = True

# ✅ 검색 결과
if st.session_state.search_clicked:
    terms = query.split()
    filtered = df.copy()

    # 가격 필터
    filtered["가격"] = pd.to_numeric(filtered["가격"], errors="coerce")
    filtered = filtered[(filtered["가격"] >= min_price) & (filtered["가격"] <= max_price)]

    # 한정 캐릭터 수 필터
    filtered["한정"] = pd.to_numeric(filtered["한정"], errors="coerce")
    filtered = filtered[filtered["한정"] >= min_limit]

    # 검색어 정확 일치
    for term in terms:
        pattern = rf'\\b{re.escape(term)}\\b'
        filtered = filtered[filtered["캐릭터 목록"].str.contains(pattern, na=False, regex=True)]

    # ✅ 표 형태로 한 번에 표시
    if not filtered.empty:
        st.write(f"🔍 총 {len(filtered)}개 계정이 검색되었습니다.")
        st.dataframe(
            filtered[["번호", "한정", "가격", "캐릭터 목록"]],
            use_container_width=True,
            height=600
        )
    else:
        st.warning("조건에 맞는 계정이 없습니다.")

# 사용 방법
st.markdown("""
---
### 💡 사용 방법
1️⃣ 검색창에 캐릭터 이름을 띄어쓰기로 구분해 입력하세요.  
  예: `히마리 히카리 네루`  
2️⃣ 가격대 슬라이더로 원하는 가격 범위를 설정하세요.  
3️⃣ ‘최소 한정 캐릭터 개수’를 조정하여 조건을 세밀하게 지정할 수 있습니다.  
4️⃣ [검색] 버튼을 누르면 조건에 맞는 계정이 표로 표시됩니다.  
5️⃣ **캐릭터 목록은 표에서 바로 확인 가능합니다.**
""", unsafe_allow_html=True)
