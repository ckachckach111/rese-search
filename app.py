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
    st.error(f"CSV 컬럼 오류 / 필요: {required}")
    st.stop()

# -------------------------
# 검색용 토큰 처리 (기존 유지)
# -------------------------
def normalize_text_for_tokens(s: str):
    if not isinstance(s, str):
        return []
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r'\(\+\s*\d+\s*\)|\+\s*\d+|\b[45]\s*성\b', ' ', s)
    s = re.sub(r'[^\w가-힣]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return re.findall(r'[가-힣]+|[A-Za-z0-9]+', s.lower())

def normalize_search_terms(q: str):
    if not q:
        return []
    return [re.sub(r'[^\w가-힣]', '', t.lower()) for t in q.split() if t.strip()]

df["캐릭터 목록"] = df["캐릭터 목록"].fillna("").astype(str)
df["_tokens"] = df["캐릭터 목록"].apply(normalize_text_for_tokens)

# -------------------------
# 패스 갯수: CSV 값 그대로 사용
# -------------------------
pass_col = next((c for c in ["패스 갯수", "패스", "패스갯수"] if c in df.columns), None)
df["패스"] = pd.to_numeric(df[pass_col], errors="coerce").fillna(0).astype(int) if pass_col else 0

# -------------------------
# UI
# -------------------------
st.set_page_config(page_title="계정 검색", layout="wide")
st.markdown("<h2 style='text-align:center;'>🎮 계정 검색</h2>", unsafe_allow_html=True)

# -------------------------
# 검색 조건
# -------------------------
query = st.text_input("", placeholder="예: 히마리 히카리 (띄어쓰기 AND 검색)")
min_price, max_price = st.slider("가격대 (만원)", 0, 100, (0, 100))
min_limit = st.number_input("최소 한정 캐릭터 수", 0, 100, 0)

min_pass, max_pass = st.slider(
    "패스 갯수",
    int(df["패스"].min()),
    int(df["패스"].max()),
    (int(df["패스"].min()), int(df["패스"].max()))
)

# -------------------------
# 검색 실행
# -------------------------
if st.button("검색"):
    result = df.copy()

    result["가격"] = pd.to_numeric(result["가격"], errors="coerce")
    result = result[(result["가격"] >= min_price) & (result["가격"] <= max_price)]

    result["한정"] = pd.to_numeric(result["한정"], errors="coerce").fillna(0)
    result = result[result["한정"] >= min_limit]

    result = result[(result["패스"] >= min_pass) & (result["패스"] <= max_pass)]

    terms = normalize_search_terms(query)
    if terms:
        result = result[result["_tokens"].apply(lambda t: all(x in t for x in terms))]

    if not result.empty:
        st.write(f"총 {len(result)}개 계정")
        st.dataframe(
            result[["번호", "한정", "가격", "패스", "캐릭터 목록"]],
            use_container_width=True,
            height=700
        )
    else:
        st.warning("조건에 맞는 계정이 없습니다.")

# -------------------------
# 사용 설명
# -------------------------
st.markdown("""
---
### 사용 방법
- 캐릭터 이름은 **띄어쓰기로 AND 검색**
- 가격 단위는 **만원**
- **패스 갯수는 CSV에 적힌 숫자를 그대로 사용**
- 결과 표 컬럼 순서:
  **번호 / 한정 / 가격 / 패스 / 캐릭터 목록**
""")
