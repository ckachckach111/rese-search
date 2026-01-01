import streamlit as st
import pandas as pd
import re
import unicodedata

# -------------------------
# 데이터 로드 (인코딩 안전)
# -------------------------
@st.cache_data
def load_data(path="accounts.csv"):
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.DataFrame()

df = load_data()
if df.empty:
    st.error("accounts.csv를 불러올 수 없습니다.")
    st.stop()

# -------------------------
# 컬럼 이름 보정
# -------------------------
df.columns = [c.strip().replace("캐릭터목록", "캐릭터 목록") for c in df.columns]
required = ["번호", "한정", "가격", "캐릭터 목록"]
if any(c not in df.columns for c in required):
    st.error("CSV 컬럼이 맞지 않습니다.")
    st.stop()

# -------------------------
# 정규화 & 토큰화
# -------------------------
def normalize_tokens(text):
    if not isinstance(text, str):
        return []
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r'[^\w가-힣\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return re.findall(r'[가-힣]+|[A-Za-z0-9]+', text.lower())

df["_tokens"] = df["캐릭터 목록"].fillna("").apply(normalize_tokens)

# ✅ 패스 갯수 컬럼 생성 (캐릭터 수)
df["패스"] = df["_tokens"].apply(len)

# -------------------------
# UI
# -------------------------
st.set_page_config(page_title="계정 검색", layout="wide")

st.markdown("""
<style>
div[data-testid="stDataFrame"] td {
    white-space: pre-wrap !important;
    word-break: break-word !important;
}
div[data-testid="stDataFrame"] td:nth-child(4) {
    min-width: 650px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align:center;'>🎮 계정 검색</h2>", unsafe_allow_html=True)

# -------------------------
# 검색 조건
# -------------------------
query = st.text_input("", "", placeholder="예: 히마리 히카리")
min_price, max_price = st.slider("가격대 (만원)", 0, 100, (0, 100))
min_limit = st.number_input("최소 한정 캐릭터 수", 0, 50, 0)

min_pass, max_pass = st.slider(
    "패스 갯수 (캐릭터 수)",
    int(df["패스"].min()),
    int(df["패스"].max()),
    (int(df["패스"].min()), int(df["패스"].max()))
)

if st.button("검색"):
    result = df.copy()

    # 가격
    result["가격"] = pd.to_numeric(result["가격"], errors="coerce")
    result = result[(result["가격"] >= min_price) & (result["가격"] <= max_price)]

    # 한정
    result["한정"] = pd.to_numeric(result["한정"], errors="coerce").fillna(0)
    result = result[result["한정"] >= min_limit]

    # 패스
    result = result[(result["패스"] >= min_pass) & (result["패스"] <= max_pass)]

    # 캐릭터 AND 검색
    terms = normalize_tokens(query)
    if terms:
        result = result[result["_tokens"].apply(
            lambda toks: all(t in toks for t in terms)
        )]

    # -------------------------
    # 결과
    # -------------------------
    if not result.empty:
        st.write(f"🔍 총 {len(result)}개 계정")
        st.dataframe(
            result[["번호", "한정", "가격", "패스", "캐릭터 목록"]],
            use_container_width=True,
            height=700
        )
    else:
        st.warning("조건에 맞는 계정이 없습니다.")

# -------------------------
# 사용 방법
# -------------------------
st.markdown("""
---
### 💡 사용 방법
1️⃣ 캐릭터 이름을 띄어쓰기로 입력하면 **AND 검색**됩니다  
2️⃣ 가격 / 한정 / **패스 갯수(캐릭터 수)** 로 필터링 가능  
3️⃣ 결과 테이블에서 캐릭터 목록을 바로 확인할 수 있습니다
""")
