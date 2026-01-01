import streamlit as st
import pandas as pd

# CSV 불러오기
df = pd.read_csv("accounts.csv")

# === 패스 갯수 컬럼 처리 ===
if '패스 갯수' in df.columns:
    df['패스 갯수'] = pd.to_numeric(df['패스 갯수'], errors='coerce').fillna(0).astype(int)

# 기본 페이지 설정
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
            height: 85vh;
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

# 검색 입력창
query = st.text_input("", "", placeholder="예: 히마리 히카리 (띄어쓰기로 여러 캐릭터 검색)")

# 가격 필터
min_price, max_price = st.slider("가격대 (만원)", 0, 100, (0, 100), step=1)

# === 패스 갯수 필터 ===
if '패스 갯수' in df.columns:
    min_pass = int(df['패스 갯수'].min())
    max_pass = int(df['패스 갯수'].max())
    pass_range = st.slider('패스 갯수', min_pass, max_pass, (min_pass, max_pass))

# 한정 캐릭터 최소 개수
min_limit = st.number_input("최소 한정 캐릭터 개수", min_value=0, max_value=100, value=0, step=1)

# 검색 버튼
search_clicked = st.button("검색")

# 검색 결과 영역
if search_clicked:
    # 여러 단어(공백 구분)를 모두 포함하는 계정 찾기 (AND 조건)
    terms = query.split()
    filtered = df.copy()

    # 필터 적용
    if "가격" in df.columns:
        filtered["가격"] = pd.to_numeric(filtered["가격"], errors="coerce")
        filtered = filtered[(filtered["가격"] >= min_price) & (filtered["가격"] <= max_price)]

    if "한정" in df.columns:
        filtered["한정"] = pd.to_numeric(filtered["한정"], errors="coerce")
        filtered = filtered[filtered["한정"] >= min_limit]

    if terms:
        filtered = filtered[filtered["캐릭터 목록"].apply(lambda x: all(term in str(x) for term in terms))]

    if not filtered.empty:
        st.dataframe(filtered[["번호", "한정", "가격", "캐릭터 목록"]], use_container_width=True)
    else:
        st.warning("조건에 맞는 계정이 없습니다.")

# 사용방법 안내 (항상 하단에 표시)
st.markdown("""
---
### 💡 사용 방법
1️⃣ 검색창에 캐릭터 이름을 띄어쓰기로 구분해 입력하세요.  
  예: `히마리 히카리 네루`  
2️⃣ 가격대 슬라이더로 원하는 가격 범위를 설정하세요.  
3️⃣ ‘최소 한정 캐릭터 개수’를 조정하여 조건을 세밀하게 지정할 수 있습니다.  
4️⃣ [검색] 버튼을 누르면 조건에 맞는 계정이 표로 표시됩니다.
""", unsafe_allow_html=True)