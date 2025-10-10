import streamlit as st
import pandas as pd

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
    </style>
""", unsafe_allow_html=True)

# 제목
st.markdown("<h2 style='text-align:center;'>🔎 계정 검색</h2>", unsafe_allow_html=True)

# 검색 상태 관리
if "search_clicked" not in st.session_state:
    st.session_state.search_clicked = False

# 입력창 (검색어)
query = st.text_input("", "", placeholder="예: 히마리 히카리 (띄어쓰기로 여러 캐릭터 검색)")

# 필터
min_price, max_price = st.slider("가격대 (만원)", 0, 100, (0, 100), step=1)
min_limit = st.number_input("최소 한정 캐릭터 개수", min_value=0, max_value=100, value=0, step=1)

# 버튼들
col1, col2 = st.columns(2)
with col1:
    if st.button("검색"):
        st.session_state.search_clicked = True
with col2:
    if st.button("처음으로 돌아가기"):
        st.session_state.search_clicked = False

# ✅ 검색 결과 표시
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

    # 검색어 AND 조건
    if terms:
        filtered = filtered[filtered["캐릭터 목록"].apply(lambda x: all(term in str(x) for term in terms))]

    # 결과 출력
    if not filtered.empty:
        st.write(f"🔍 총 {len(filtered)}개 계정이 검색되었습니다.")
        st.dataframe(filtered[["번호", "한정", "가격", "캐릭터 목록"]], use_container_width=True)
    else:
        st.warning("조건에 맞는 계정이 없습니다.")
else:
    st.info("검색어를 입력하고 [검색] 버튼을 눌러주세요.")

# 사용 방법 안내
st.markdown("""
---
### 💡 사용 방법
1️⃣ 검색창에 캐릭터 이름을 띄어쓰기로 구분해 입력하세요.  
  예: `히마리 히카리 네루`  
2️⃣ 가격대 슬라이더로 원하는 가격 범위를 설정하세요.  
3️⃣ ‘최소 한정 캐릭터 개수’를 조정하여 조건을 세밀하게 지정할 수 있습니다.  
4️⃣ [검색] 버튼을 누르면 조건에 맞는 계정이 표로 표시됩니다.  
5️⃣ 결과 화면 하단의 [처음으로 돌아가기] 버튼을 눌러 초기 화면으로 복귀할 수 있습니다.
""", unsafe_allow_html=True)
