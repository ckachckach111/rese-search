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
# 컬럼 이름 보정(약간의 유연성)
# -------------------------
# 기대 컬럼 이름
expected_cols = ["번호", "한정", "가격", "캐릭터 목록"]

# 간단히 공백/명칭 차이 보정: '캐릭터목록' -> '캐릭터 목록'
cols = list(df.columns)
cols_fixed = []
for c in cols:
    cc = c.strip()
    if cc == "캐릭터목록":
        cc = "캐릭터 목록"
    cols_fixed.append(cc)
df.columns = cols_fixed

missing = [c for c in expected_cols if c not in df.columns]
if missing:
    st.error(f"CSV에 필요한 열이 없습니다: {missing}  — 파일의 헤더(맨 윗줄)를 확인하세요.")
    st.stop()

# -------------------------
# 텍스트 정규화 및 토큰화 함수 (강화)
# -------------------------
def normalize_text_for_tokens(s: str):
    """텍스트를 정규화하고 토큰 리스트(소문자 영문/숫자, 한글 토큰) 반환"""
    if not isinstance(s, str):
        return []
    # 1. Unicode NFKC (전각->반각 등)
    s = unicodedata.normalize("NFKC", s)
    # 2. 공백 통일
    s = s.replace("\u3000", " ").replace("\xa0", " ").strip()
    # 3. 제거할 패턴 (안전하게)
    s = re.sub(r'\(\+\s*\d+\s*\)', ' ', s)
    s = re.sub(r'\+\s*\d+', ' ', s)
    s = re.sub(r'\b[45]\s*성\b', ' ', s)  # 4성, 5성 제거
    # 4. 괄호/구분자/특수문자 -> 공백
    s = re.sub(r'[,\|/·;:()\[\]【】\-\—\_\/\\\*•…·"\'`~<>«»]', ' ', s)
    # 5. 이모지 제거 (대략)
    s = re.sub(r'[\U00010000-\U0010ffff]', ' ', s)
    # 6. 연속 공백 정리
    s = re.sub(r'\s+', ' ', s).strip()
    # 7. 토큰화: 한글 연속 문자열 OR 영문/숫자 연속
    tokens = re.findall(r'[가-힣]+|[A-Za-z0-9]+', s)
    tokens = [t.lower() for t in tokens if t.strip()]
    return tokens

def normalize_search_terms(raw_query: str):
    """사용자 입력을 같은 방식으로 정규화하여 검색 토큰 리스트 반환"""
    if not raw_query or not str(raw_query).strip():
        return []
    parts = [p for p in re.split(r'[\s,]+', raw_query.strip()) if p]
    normalized = []
    for p in parts:
        p2 = unicodedata.normalize("NFKC", p)
        p2 = p2.replace("\u3000", " ").replace("\xa0", " ").strip()
        p2 = re.sub(r'\b[45]\s*성\b', '', p2)
        p2 = re.sub(r'\+\s*\d+', '', p2)
        # 영문/숫자/한글만 남김
        p2 = re.sub(r'[^가-힣A-Za-z0-9]', '', p2)
        p2 = p2.lower().strip()
        if p2:
            # further tokenization if composite, but keep simple:
            # e.g., '우미카' -> '우미카'
            normalized.append(p2)
    return normalized

# -------------------------
# 토큰 컬럼 생성 (캐시된 컬럼이 없으면 생성)
# -------------------------
if "_tokens" not in df.columns:
    df["_tokens"] = df["캐릭터 목록"].fillna("").astype(str).apply(normalize_text_for_tokens)

# -------------------------
# UI 설정
# -------------------------
st.set_page_config(page_title="계정 검색", layout="centered")
st.markdown("""
    <style>
        .stTextInput { text-align: center; }
        div[data-testid="stTextInput"] label { display: none; }
        .block-container { display:flex; flex-direction:column; justify-content:center; align-items:center; }
        div[data-testid="stDataFrame"] td { white-space: pre-wrap !important; word-break: break-word !important; }
        div[data-testid="stDataFrame"] td:nth-child(4) { min-width: 450px !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align:center;'>🎮 계정 검색</h2>", unsafe_allow_html=True)

# session state for search
if "search_clicked" not in st.session_state:
    st.session_state.search_clicked = False

# 입력창 및 필터
query = st.text_input("", "", placeholder="예: 히마리 히카리 (띄어쓰기로 여러 캐릭터 검색)")
min_price, max_price = st.slider("가격대 (만원)", 0, 100, (0, 100), step=1)
min_limit = st.number_input("최소 한정 캐릭터 개수", min_value=0, max_value=100, value=0, step=1)

if st.button("검색"):
    st.session_state.search_clicked = True

# -------------------------
# 검색 처리
# -------------------------
if st.session_state.search_clicked:
    # normalize search tokens
    search_tokens = normalize_search_terms(query)
    filtered = df.copy()

    # 가격 필터 (numeric 안전 처리)
    filtered["가격"] = pd.to_numeric(filtered["가격"], errors="coerce")
    filtered = filtered[(filtered["가격"] >= min_price) & (filtered["가격"] <= max_price)]

    # 한정 필터
    filtered["한정"] = pd.to_numeric(filtered["한정"], errors="coerce").fillna(0)
    filtered = filtered[filtered["한정"] >= min_limit]

    # 토큰 기반 AND 매칭: 모든 검색 토큰이 _tokens에 포함되어야 함
    if search_tokens:
        def match_all_tokens(token_list):
            if not isinstance(token_list, (list, tuple)):
                return False
            # 정확 일치 토큰(소문자)
            return all(any(term == tok for tok in token_list) for term in search_tokens)
        filtered = filtered[filtered["_tokens"].apply(match_all_tokens)]

    # 결과 출력
    if not filtered.empty:
        st.write(f"🔍 총 {len(filtered)}개 계정이 검색되었습니다.")
        st.dataframe(filtered[["번호", "한정", "가격", "캐릭터 목록"]], use_container_width=True, height=600)
    else:
        st.warning("조건에 맞는 계정이 없습니다. 아래 디버그 정보를 확인하세요.")
        # 디버그: 샘플 + 근접 매칭 후보
        st.markdown("**디버그: CSV 샘플 (토큰 포함)**")
        sample = df.head(10)[["번호", "한정", "가격", "캐릭터 목록", "_tokens"]]
        st.dataframe(sample, use_container_width=True, height=300)

        if search_tokens:
            st.markdown("**디버그: 검색 토큰**")
            st.write(search_tokens)

            st.markdown("**디버그: 근접 후보 (토큰 하나라도 포함되는 행, 최대 30행)**")
            def any_match(token_list):
                if not isinstance(token_list, (list, tuple)):
                    return False
                return any(term in token_list for term in search_tokens)
            near = df[df["_tokens"].apply(any_match)].head(30)[["번호", "한정", "가격", "캐릭터 목록", "_tokens"]]
            if not near.empty:
                st.dataframe(near, use_container_width=True, height=400)
            else:
                st.info("근접 후보 없음. CSV의 문자(특수문자/붙어있는 형태 등)를 확인하세요.")

# 사용 방법
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
