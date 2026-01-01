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
    # 제거: (+숫자), +숫자, 4성/5성
    s = re.sub(r'\(\+\s*\d+\s*\)', ' ', s)
    s = re.sub(r'\+\s*\d+', ' ', s)
    s = re.sub(r'\b[45]\s*성\b', ' ', s)
    # 특수문자 -> 공백
    s = re.sub(r'[,\|/·;:()\[\]【】\-\—\_\/\\\*•…·"\'`~<>«»]', ' ', s)
    # 이모지 등 제거(대략)
    s = re.sub(r'[\U00010000-\U0010ffff]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    # 토큰화: 한글 연속 또는 영문/숫자 연속
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
# 토큰 컬럼 생성 (전체 텍스트) — 검색용 (기존 로직 유지)
# -------------------------
df["캐릭터 목록"] = df["캐릭터 목록"].fillna("").astype(str)
df["_tokens"] = df["캐릭터 목록"].apply(normalize_text_for_tokens)

# -------------------------
# 패스 갯수: CSV의 값 사용 (계산 금지) — 여기만 핵심 변경
# -------------------------
# 후보 컬럼명: '패스 갯수', '패스', '패스갯수' 중 하나를 사용
pass_col = None
for candidate in ["패스 갯수", "패스", "패스갯수"]:
    if candidate in df.columns:
        pass_col = candidate
        break

if pass_col is None:
    st.warning("CSV에 '패스 갯수' 컬럼이 없습니다. 패스 필터는 비활성화됩니다.")
    df["패스"] = 0
else:
    # CSV에 적힌 값을 그대로 숫자로 읽어 df['패스']에 넣음 (절대 계산하지 않음)
    df["패스"] = pd.to_numeric(df[pass_col], errors="coerce").fillna(0).astype(int)

# -------------------------
# 페스캐릭터수: CSV에 있으면 사용, 없으면 0으로 설정 (계산 금지)
# -------------------------
if "페스캐릭터수" in df.columns:
    df["페스캐릭터수"] = pd.to_numeric(df["페스캐릭터수"], errors="coerce").fillna(0).astype(int)
else:
    df["페스캐릭터수"] = 0

# -------------------------
# UI 스타일 (테이블 넓이 등)
# -------------------------
st.set_page_config(page_title="계정 검색 (패스 CSV 사용)", layout="wide")
st.markdown("""
<style>
div[data-testid="stDataFrame"] table { width: 100% !important; }
div[data-testid="stDataFrame"] td { white-space: pre-wrap !important; word-break: break-word !important; line-height:1.35em !important; }
div[data-testid="stDataFrame"] td:nth-child(4) { min-width: 600px !important; max-width: 1000px !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align:center;'>🎮 계정 검색 (패스 CSV 사용)</h2>", unsafe_allow_html=True)

# -------------------------
# 검색 조건 UI
# -------------------------
query = st.text_input("", "", placeholder="예: 히마리 히카리 (띄어쓰기로 AND 검색)")
min_price, max_price = st.slider("가격대 (만원)", 0, 100, (0, 100))
min_limit = st.number_input("최소 한정 캐릭터 수", 0, 100, 0)

# 패스 슬라이더: df['패스'] (CSV에서 읽은 값)
min_pass_possible = int(df["패스"].min()) if not df["패스"].isnull().all() else 0
max_pass_possible = int(df["패스"].max()) if not df["패스"].isnull().all() else 0
min_pass, max_pass = st.slider("패스 갯수 (CSV값)", min_pass_possible, max_pass_possible, (min_pass_possible, max_pass_possible))

min_fes = st.number_input("최소 페스 캐릭터 수", min_value=0, max_value=100, value=0, step=1)

if st.button("검색"):
    result = df.copy()
    # 가격/한정 필터 (숫자 안전)
    result["가격"] = pd.to_numeric(result["가격"], errors="coerce")
    result = result[(result["가격"] >= min_price) & (result["가격"] <= max_price)]
    result["한정"] = pd.to_numeric(result["한정"], errors="coerce").fillna(0)
    result = result[result["한정"] >= min_limit]

    # 패스 필터: CSV의 패스 값을 그대로 사용
    result = result[(result["패스"] >= min_pass) & (result["패스"] <= max_pass)]

    # 페스 필터: CSV의 페스캐릭터수 사용 (계산하지 않음)
    result = result[result["페스캐릭터수"] >= min_fes]

    # 캐릭터 AND 검색 (토큰 단위 정확매칭) — 전체 목록 기준
    terms = normalize_search_terms(query)
    if terms:
        result = result[result["_tokens"].apply(lambda toks: all(term in toks for term in terms))]

    # 결과 출력
    if not result.empty:
        st.write(f"🔍 총 {len(result)}개 계정 (패스는 CSV값 사용)")
        st.dataframe(result[["번호", "한정", "가격", "패스", "페스캐릭터수", "캐릭터 목록"]], use_container_width=True, height=700)
    else:
        st.warning("조건에 맞는 계정이 없습니다.")
        debug_cols = ["번호", "한정", "가격", "패스", "페스캐릭터수", "캐릭터 목록", "_tokens"]
        st.dataframe(df.head(10)[[c for c in debug_cols if c in df.columns]], use_container_width=True, height=400)

# 사용 방법
st.markdown("""
---
### 💡 사용 방법
1️⃣ 캐릭터 이름을 띄어쓰기로 입력하면 **AND 검색**됩니다.  
2️⃣ 가격 / 한정 / 패스(CSV값) / 페스캐릭터수 로 필터링 가능합니다.  
3️⃣ 결과 표에서 `패스`(CSV값)와 `페스캐릭터수`를 확인하세요.
""", unsafe_allow_html=True)
