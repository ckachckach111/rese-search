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
            df = pd.read_csv(path, encoding=enc)
            return df
        except Exception:
            continue
    return pd.DataFrame()

df = load_data()
if df.empty:
    st.error("accounts.csv를 불러올 수 없습니다. 파일과 인코딩을 확인하세요.")
    st.stop()

# -------------------------
# 컬럼 이름 보정
# -------------------------
df.columns = [c.strip().replace("캐릭터목록", "캐릭터 목록") for c in df.columns]
required = ["번호", "한정", "가격", "캐릭터 목록"]
if any(c not in df.columns for c in required):
    st.error(f"CSV 컬럼이 맞지 않습니다. 필요한 컬럼: {required} 현재: {list(df.columns)}")
    st.stop()

# -------------------------
# 정규화 & 토큰화 함수 (검색용)
# -------------------------
def normalize_text_for_tokens(s: str):
    if not isinstance(s, str):
        return []
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u3000", " ").replace("\xa0", " ").strip()
    s = re.sub(r'\(\+\s*\d+\s*\)', ' ', s)
    s = re.sub(r'\+\s*\d+', ' ', s)
    s = re.sub(r'\b[45]\s*성\b', ' ', s)
    s = re.sub(r'[,\|/·;:()\[\]【】\-\—\_\/\\\*•…·"\'`~<>«»]', ' ', s)
    s = re.sub(r'[\U00010000-\U0010ffff]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    tokens = re.findall(r'[가-힣]+|[A-Za-z0-9]+', s)
    return [t.lower() for t in tokens if t.strip()]

def normalize_search_terms(raw_query: str):
    if not raw_query or not str(raw_query).strip():
        return []
    parts = [p for p in re.split(r'[\s,]+', raw_query.strip()) if p]
    normalized = []
    for p in parts:
        p2 = unicodedata.normalize("NFKC", p)
        p2 = p2.replace("\u3000", " ").replace("\xa0", " ").strip()
        p2 = re.sub(r'\b[45]\s*성\b', '', p2)
        p2 = re.sub(r'\+\s*\d+', '', p2)
        p2 = re.sub(r'[^가-힣A-Za-z0-9]', '', p2)
        p2 = p2.lower().strip()
        if p2:
            normalized.append(p2)
    return normalized

# -------------------------
# 토큰 컬럼 생성 (검색용)
# -------------------------
df["캐릭터 목록"] = df["캐릭터 목록"].fillna("").astype(str)
df["_tokens"] = df["캐릭터 목록"].apply(normalize_text_for_tokens)

# -------------------------
# 패스 갯수: CSV 값만 사용
# -------------------------
pass_col = None
for c in ["패스 갯수", "패스", "패스갯수"]:
    if c in df.columns:
        pass_col = c
        break

if pass_col is None:
    df["패스"] = 0
else:
    df["패스"] = pd.to_numeric(df[pass_col], errors="coerce").fillna(0).astype(int)

# -------------------------
# UI
# -------------------------
st.set_page_config(page_title="계정 검색", layout="wide")
st.markdown("""
<style>
div[data-testid="stDataFrame"] table { width: 100% !important; }
div[data-testid="stDataFrame"] td { white-space: pre-wrap !important; word-break: break-word !important; line-height:1.35em !important; }
div[data-testid="stDataFrame"] td:nth-child(4) { min-width: 600px !important; max-width: 1000px !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align:center;'>🎮 계정 검색</h2>", unsafe_allow_html=True)

# -------------------------
# 검색 조건
# -------------------------
query = st.text_input("", "", placeholder="예: 히마리 히카리 (띄어쓰기로 AND 검색)")
min_price, max_price = st.slider("가격대 (만원)", 0, 100, (0, 100))
min_limit = st.number_input("최소 한정 캐릭터 수", 0, 100, 0)

min_pass_possible = int(df["패스"].min())
max_pass_possible = int(df["패스"].max())
min_pass, max_pass = st.slider("패스 갯수", min_pass_possible, max_pass_possible, (min_pass_possible, max_pass_possible))

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
        result = result[result["_tokens"].apply(lambda t: all(term in t for term in terms))]

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
# 사용 설명 (화면 하단)
# -------------------------
st.markdown("---")
st.markdown("""
### 사용 방법
- **검색창**: 캐릭터 이름을 띄어쓰기로 여러 개 입력하면 *AND* 검색됩니다.  
  예: `히카리 히마리` → 두 이름 모두 포함된 계정만 표시됩니다.  
- **가격대 (만원)**: 슬라이더로 원하는 가격 범위를 선택하세요 (단위: 만원).  
- **최소 한정 캐릭터 수**: 한정 캐릭터(숫자) 최소 개수 지정.  
- **패스 갯수**: CSV에 적힌 '패스 갯수' 값을 기준으로 슬라이더 필터가 동작합니다.  
  (CSV 컬럼명이 `패스 갯수`, `패스`, `패스갯수` 중 하나면 자동 인식합니다.)  
- **검색 버튼**: 조건을 설정한 뒤 '검색'을 클릭하면 결과가 표시됩니다.  
- **결과 표 컬럼**: `번호`, `한정`, `가격`, `패스`, `캐릭터 목록` 순으로 표시됩니다.

> 문제 발생 시: CSV의 헤더(첫 줄)와 상위 5개 행을 복사해서 보내주시면 바로 확인해 드리겠습니다.
""")
