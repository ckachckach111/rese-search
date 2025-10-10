import streamlit as st
import pandas as pd
import re

# CSV 불러오기
@st.cache_data
def load_data():
    return pd.read_csv("accounts.csv", encoding="utf-8-sig")

df = load_data()

# 페이지 설정
st.set_page_config(page_title="계정 검색", layout="centered")

# 중앙 정렬용 CSS
st.markdown("""
    <style>
        .stTextInput {
            text-align: center;
        }
        div[data-testid="stTextInput"] label {
            display: none;
        }
        .block-container {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        .stSlider {
            width: 400px;
        }
        .stNumberInput {
            width: 200px;
        }
        button[kind="primary"] {
            background-color: #007bff !important;
            color: white !important;
            border-radius: 10px !important;
            padding: 0.5em 1em !important;
        }
        /* ✅ 결과 테이블 스타일 */
        div[data-testid="stDataFrame"] table {
            width: 100% !important;
        }
        div[data-testid="stDataFrame"] td {
            white-space: pre-wrap !important;
            word-break: break-word !important;
            line-height: 1.3em !important;
            font-size: 15px !important;
            vertical-align: top !important;
        }
        /* 캐릭터 목록 열만 넓게 */
        div[data-testid="stDataFrame"] td:nth-child(4) {
            min-width: 450px !important;
        }
    </style>
""", unsafe_allow_html=True)

# 제목
st.markdown("<h2 style='text-align:center;'>🎮 계정 검색</h2>", unsafe_allow_html=True)

# 세션 상태 관리
if "search_clicked" not in st.session_state:
    st.session_state.search_clicked = False

# 입력창
query = st.text_input("", "", placeholder="예: 히마리 히카리 (띄어쓰기로 여러 캐릭터 검색)")

# 필터
min_price, max_price = st.slider("가격대 (만원)", 0, 50, (0, 50), step=1)
min_limit = st.number_input("최소 한정 캐릭터 개수", min_value=0, max_value=100, value=0, step=1)

# 검색 버튼
if st.button("검색"):
    st.session_state.search_clicked = True

# ✅ 검색 결과
if st.session_state.search_clicked:
    terms = query.split()
    filtered = df.copy()

    # 가격 필터
    if "가격" in df.columns:
        filtered["가격"] = pd.to_numeric(filtered["가격"], errors="coerce")
        filtered = filtered[(filtered["가격"] >= min_price) & (filtered["가격"] <= max_price)]

    # 한정 캐릭터 수 필터
    if "한정" in df.columns:
        filtered["한정"] = pd.to_numeric(filtered["한정"], errors="coerce")
        filtered = filtered[filtered["한정"] >= min_limit]

    # 검색어 정확 일치 (AND 조건)
    for term in terms:
        pattern = rf'\\b{re.escape(term)}\\b'
        filtered = filtered[filtered["캐릭터 목록"].str.contains(pattern, na=False, regex=True)]

    # 결과 출력
    if not filtered.empty:
        st.write(f"🔍 총 {len(filtered)}개 계정이 검색되었습니다.")
        st.dataframe(
            filtered[["번호", "한정", "가격", "캐릭터 목록"]],
            use_container_width=True,
            height=600
        )
    else:
        st.warning("조건에 맞는 계정이 없습니다.")

# 사용법 안내
st.markdown("""
---
### 💡 사용 방법
1️⃣ 검색창에 캐릭터 이름을 띄어쓰기로 구분해 입력하세요.  
  예: `히마리 히카리 네루`  
2️⃣ 가격대 슬라이더로 원하는 가격 범위를 설정하세요.  
3️⃣ ‘최소 한정 캐릭터 개수’를 조정하여 조건을 세밀하게 지정할 수 있습니다.  
4️⃣ [검색] 버튼을 누르면 조건에 맞는 계정이 표로 표시됩니다.
5️⃣ 캐릭터 목록을 누르면 상세하게 볼 수 있습니다.
""", unsafe_allow_html=True)

