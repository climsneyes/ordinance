# Gemini File Search 마이그레이션 가이드

## 📋 개요

기존 pickle 기반 RAG 시스템을 Gemini File Search API로 대체하는 가이드입니다.

### 기존 시스템 문제점
- ❌ 단순 코사인 유사도만 사용
- ❌ 수동 청크 관리 및 임베딩 생성
- ❌ 확장성 부족
- ❌ 검색 품질 제한

### Gemini File Search 장점
- ✅ 자동 청크 분할 및 임베딩
- ✅ 의미 기반 고급 검색
- ✅ 인용 추적 기능
- ✅ Google 인프라 기반 확장성
- ✅ 비용 효율적 (쿼리 무료)

---

## 🚀 설치 및 설정

### 1. 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. API 키 설정

#### 옵션 A: 환경 변수 (권장)
```bash
# Windows
set GEMINI_API_KEY=your-api-key-here

# Linux/Mac
export GEMINI_API_KEY=your-api-key-here
```

#### 옵션 B: Streamlit secrets
`.streamlit/secrets.toml` 파일 생성:
```toml
GEMINI_API_KEY = "your-api-key-here"
```

---

## 📁 PDF 파일 준비

### 필요한 PDF 파일

1. **자치법규 입안 가이드** (`jachi_guide_2022.pdf`)
2. **재의·제소 조례 모음집** (`3. 지방자치단체의 재의·제소 조례 모음집(Ⅸ) (1).pdf`)

### 파일 위치 확인

현재 프로젝트에는 `.pkl` 파일만 있고 원본 PDF가 없습니다.

**해결 방법:**
1. 원본 PDF 파일을 구합니다
2. 프로젝트 루트 디렉토리에 배치합니다
3. 또는 `setup_gemini_store.py`에서 파일 경로를 수정합니다

---

## 🔧 초기 설정 (1회만 실행)

### 1. setup_gemini_store.py 편집

PDF 파일 경로를 실제 경로로 수정:

```python
PDF_FILES = [
    "2022년_자치법규입안길라잡이.pdf",
    "3. 지방자치단체의 재의·제소 조례 모음집(Ⅸ) (1).pdf",
    "자치법규_Q&A (1).pdf",
    "자치법규_쟁점_사전검토_지원_사례집 (1).pdf",
]
```

### 2. 설정 스크립트 실행

```bash
python setup_gemini_store.py
```

실행 결과:
- ✅ File Search Store 생성
- ✅ PDF 파일 업로드
- ✅ 자동 인덱싱
- ✅ 검색 테스트 (선택)

---

## 🔄 Streamlit 앱 통합

### 방법 1: 기존 함수 대체 (권장)

`streamlit_app.py`에 다음 코드 추가:

```python
from gemini_file_search import (
    GeminiFileSearchManager,
    search_relevant_guidelines_gemini,
    get_gemini_store_manager
)

# Gemini API 키 가져오기
gemini_api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

# Store Manager 초기화 (캐싱됨)
if gemini_api_key:
    store_manager = get_gemini_store_manager(gemini_api_key)
```

### 방법 2: 점진적 마이그레이션

기존 함수와 병렬로 실행하여 비교:

```python
# 기존 방식
old_results = search_relevant_guidelines(query, vector_store, api_key)

# 새로운 방식
new_results = search_relevant_guidelines_gemini(query, gemini_api_key, store_manager)

# 두 결과 비교
st.write("### 기존 방식 결과")
st.write(old_results)

st.write("### Gemini File Search 결과")
st.write(new_results)
```

---

## 📊 함수 매핑

### 검색 함수 대체

| 기존 함수 | 새 함수 | 설명 |
|----------|---------|------|
| `search_relevant_guidelines()` | `search_relevant_guidelines_gemini()` | 가이드라인 검색 |
| `search_multiple_vectorstores()` | `search_relevant_guidelines_gemini()` | 통합 검색 (단일 Store 사용) |
| `search_comprehensive_violation_cases()` | `search_violation_cases_gemini()` | 판례 검색 |

### 코드 예시

#### Before (기존)
```python
results = search_relevant_guidelines(
    query=search_query,
    vector_store=st.session_state.vector_store,
    api_key=gemini_api_key,
    top_k=5
)
```

#### After (Gemini File Search)
```python
results = search_relevant_guidelines_gemini(
    query=search_query,
    api_key=gemini_api_key,
    store_manager=store_manager,
    top_k=5
)
```

---

## 🧪 테스트

### 1. 기본 검색 테스트

```python
from gemini_file_search import GeminiFileSearchManager

# Manager 생성
manager = GeminiFileSearchManager(api_key)
manager.create_or_get_store()

# 검색 테스트
result = manager.search("조례의 위법성 판단 기준은?")
print(result['answer'])
print(f"출처: {len(result['sources'])}개")
```

### 2. 성능 비교

```python
import time

# 기존 방식
start = time.time()
old_results = search_relevant_guidelines(query, vector_store, api_key)
old_time = time.time() - start

# Gemini File Search
start = time.time()
new_results = search_relevant_guidelines_gemini(query, api_key, store_manager)
new_time = time.time() - start

print(f"기존 방식: {old_time:.2f}초, {len(old_results)}개 결과")
print(f"Gemini: {new_time:.2f}초, {len(new_results)}개 결과")
```

---

## 💰 비용 정보

### Gemini File Search 요금
- **색인화**: $0.15 / 1M 토큰 (1회만)
- **저장소**: 무료
- **쿼리**: 무료

### 예상 비용 (PDF 2개 기준)
- PDF 1: ~200페이지 = ~50K 토큰 = $0.0075
- PDF 2: ~300페이지 = ~75K 토큰 = $0.01125
- **총 색인화 비용: ~$0.02 (1회)**
- **쿼리 비용: $0 (무제한)**

---

## 🔍 고급 기능

### 1. 메타데이터 필터링

```python
# 특정 문서 타입만 검색
result = manager.search_with_metadata_filter(
    query="재의 요구 사례",
    metadata_filter={'type': '판례'}
)
```

### 2. 커스텀 청크 설정

```python
# 업로드 시 청크 크기 지정
manager.upload_file(
    file_path="document.pdf",
    config={
        'chunking_config': {
            'max_tokens_per_chunk': 500,
            'max_overlap_tokens': 100
        }
    }
)
```

### 3. 인용 추적

```python
result = manager.search(query, include_sources=True)

# 출처 정보 확인
for source in result['sources']:
    print(f"제목: {source['title']}")
    print(f"내용: {source['text']}")
    print(f"URI: {source['uri']}")
```

---

## 🐛 문제 해결

### Q1: "API 키 오류" 발생
**A:** 환경 변수 또는 secrets.toml에 API 키가 올바르게 설정되었는지 확인

```bash
# Windows
echo %GEMINI_API_KEY%

# Linux/Mac
echo $GEMINI_API_KEY
```

### Q2: "파일을 찾을 수 없음" 오류
**A:** PDF 파일 경로를 절대 경로로 지정하거나 파일 존재 확인

```python
import os
pdf_path = r"C:\full\path\to\file.pdf"
print(f"파일 존재: {os.path.exists(pdf_path)}")
```

### Q3: "저장소가 없음" 오류
**A:** `setup_gemini_store.py`를 먼저 실행하여 저장소 생성

### Q4: 검색 결과가 없음
**A:**
1. 파일이 제대로 업로드되었는지 확인
2. 쿼리를 더 구체적으로 작성
3. 파일 내용과 쿼리의 관련성 확인

---

## 📝 다음 단계

1. ✅ **코드 작성 완료** (`gemini_file_search.py`)
2. 🔄 **PDF 파일 준비** (원본 PDF 구하기)
3. ⏳ **초기 설정 실행** (`setup_gemini_store.py`)
4. ⏳ **Streamlit 앱 통합**
5. ⏳ **테스트 및 비교**

---

## 🤝 도움이 필요하면

1. PDF 파일 위치 확인
2. API 키 설정 확인
3. 에러 메시지 전체 내용 공유
4. 사용 중인 Python 버전 확인 (`python --version`)

---

## 📚 참고 자료

- [Gemini File Search 공식 문서](https://ai.google.dev/gemini-api/docs/file-search?hl=ko)
- [Google GenAI SDK](https://github.com/google/generative-ai-python)
