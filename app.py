import streamlit as st
import pandas as pd
import re
import unicodedata

# -------------------------
# 데이터 로드 (인코딩 안전 처리)
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
    st.error("accounts.csv를 읽을 수 없습니다. 인코딩을 UTF-8(CSV UTF-8)로 저장해 보세요.")
    st.stop()

# -------------------------
# 컬럼 이름 보정
# -------------------------
expected_cols = ["번호", "한정", "가격", "캐릭터 목록"]
cols_fixed = []
for c in df.columns:
    cc = c.strip()
    if cc == "캐릭터목록":
        cc = "캐릭터 목록"
    cols_fixed.append(cc)
df.columns = cols_fixed

missing = [c for c in expected_cols if c not in df.columns]
if missing:
    st.error(f"CSV에 필요한 열이 없습니다: {missing}")
    st.stop()

# -------------------------
# 텍스트 정규화 / 토큰화
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
# 토큰 컬럼 생성
# -------------------------
if "_tokens" not in df.columns:
    df["_tokens"] = df["캐릭터 목록"].fillna("").astype(str).apply(normalize_text_for_tokens)

# -------------------------
# UI 스타일 (테이블 넓이 조정)
# -------------------------
st.set_page_config(page_title="계정 검색", layout="wide")

st.markdown("""
    <style>
        .stTextInput { text-align: center; }
        div[data-testid="stTextInput"] label { display: none; }
        .block-container { display:flex; flex-direction:column; justify-content:center; align-items:center; }

        /* ✅ 표 전체 폭 확장 + 캐릭터 목록 넓게 */
        div[data-testid="stDataFrame"] table {
            width: 100% !important;
        }
        div[data-testid="stDataFrame"] td {
            white-space: pre-wrap !important;
            word-break: break-word !important;
            line-height: 1.4em !important;
            font-size: 15px !important;
        }
        /* 캐릭터 목록 열 넓이: 최소 600px 확보 */
        div[data-testid="stDataFrame"] td:nth-child(4) {
            min-width: 600px !important;
            max-width: 900px !important;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align:center;'>🎮 계정 검색</h2>", unsafe_allow_html=True)

if "search_clicked" not in st.session_state:
    st.session_state.search_clicked = False

# -------------------------
# 입력창 / 필터
# -------------------------
query = st.text_input("", "", placeholder="예: 히마리 히카리 (띄어쓰기로 여러 캐릭터 검색)")
min_price, max_price = st.slider("가격대 (만원)", 0, 100, (0, 100), step=1)
min_limit = st.number_input("최소 한정 캐릭터 개수", min_value=0, max_value=100, value=0, step=1)

if st.button("검색"):
    st.session_state.search_clicked = True

# -------------------------
# 검색 로직
# -------------------------
if st.session_state.search_clicked:
    search_tokens = normalize_search_terms(query)
    filtered = df.copy()

    filtered["가격"] = pd.to_numeric(filtered["가격"], errors="coerce")
    filtered = filtered[(filtered["가격"] >= min_price) & (filtered["가격"] <= max_price)]

    filtered["한정"] = pd.to_numeric(filtered["한정"], errors="coerce").fillna(0)
    filtered = filtered[filtered["한정"] >= min_limit]

    if search_tokens:
        def match_all_tokens(token_list):
            if not isinstance(token_list, (list, tuple)):
                return False
            return all(any(term == tok for tok in token_list) for term in search_tokens)
        filtered = filtered[filtered["_tokens"].apply(match_all_tokens)]

    if not filtered.empty:
        st.write(f"🔍 총 {len(filtered)}개 계정이 검색되었습니다.")
        st.dataframe(filtered[["번호", "한정", "가격", "캐릭터 목록"]],
                     use_container_width=True, height=700)
    else:
        st.warning("조건에 맞는 계정이 없습니다.")
        st.markdown("**디버그:** CSV 상위 10행 표시")
        st.dataframe(df.head(10), use_container_width=True, height=400)

# -------------------------
# 사용 방법
# -------------------------
st.markdown("""
---
### 💡 사용 방법
1️⃣ 검색창에 캐릭터 이름을 띄어쓰기로 구분해 입력하세요.  
  예: `히마리 히카리 네루`  
2️⃣ 가격대 슬라이더로 원하는 가격 범위를 설정하세요.  
3️⃣ ‘최소 한정 캐릭터 개수’를 조정하여 조건을 세밀하게 지정할 수 있습니다.  
4️⃣ [검색] 버튼을 누르면 조건에 맞는 계정이 표로 표시됩니다.  
5️⃣ 캐릭터 목록은 표에서 바로 확인 가능합니다.
""", unsafe_allow_html=True)
