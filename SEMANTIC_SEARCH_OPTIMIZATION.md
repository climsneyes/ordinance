# Gemini File Search 시맨틱 검색 최적화

## 문제 진단

### 기존 문제점
- **RAG가 작동하지 않음**: Gemini가 업로드된 PDF 대신 기본 학습 지식만 사용
- **판례 검색 실패**: PDF에 판례가 있음에도 불구하고 검색되지 않음
- **과도한 위법성 판단**: 실제 참고 자료 없이 Gemini의 기본 지식으로만 판단

### 근본 원인
잘못된 검색 쿼리 방식:
```python
# 문제가 있던 방식 - 짧은 키워드 조합
combined_query = "지방자치법 조례 위법 재의 제소 판례"
```

이러한 키워드 기반 쿼리는:
- 전통적인 검색 엔진 스타일
- Gemini File Search의 시맨틱 검색 능력을 활용하지 못함
- 문맥과 의미를 전달하지 못함

## 해결 방안

### 시맨틱 검색의 원리

Google 공식 문서에 따르면:
> "Semantic search is a technique that understands the meaning and context of a question"

시맨틱 검색은:
- 키워드 매칭이 아닌 **의미 기반 검색**
- 문서와 쿼리를 임베딩(숫자 표현)으로 변환
- **의미적 유사성**으로 관련 내용 검색

### 최적화 전략

**자연어 질문 형태의 쿼리 사용**:
```python
# 개선된 방식 - 명확한 자연어 질문
combined_query = """'서울특별시 청소년 보호 조례'과 유사한 내용의 조례 중에서
청소년보호법, 지방자치법과 관련하여
지원 대상, 금지행위에 관한 규정에서
조례가 상위법령에 위배되어 위법하다고 판단되거나 재의·제소된
구체적인 사례와 판례를 찾아주세요.

특히 다음 정보를 포함한 자료를 찾아주세요:
- 어떤 조항이 문제가 되었는지
- 어떤 상위법령(법률, 시행령 등)에 어떻게 위배되었는지
- 위법 판단의 근거와 이유
- 재의 또는 제소 결과
"""
```

## 구현 변경 사항

### 1. search_relevant_guidelines_gemini() 함수

**Before (키워드 추출 방식)**:
```python
# 법령명과 키워드만 조합
search_query = f"{laws_found[0]} {' '.join(key_terms[:3])}"
```

**After (자연어 질문 방식)**:
```python
# 맥락을 담은 구체적인 질문
if '위법' in query or '위반' in query:
    search_query = f"{primary_law}과 관련된 조례가 위법하다고 판단되어 재의 또는 제소된 사례와 판례를 찾아주세요. 어떤 조항이 문제가 되었고 상위법령에 어떻게 위배되었는지 설명된 자료를 찾아주세요."
```

**핵심 개선점**:
- 정보 요구를 명확하게 표현
- 찾고자 하는 내용의 맥락 제공
- 필요한 정보 유형을 구체적으로 명시

### 2. search_violation_cases_gemini() 함수

**Before (키워드 조합 방식)**:
```python
# 짧은 키워드만 나열
combined_query = f"{law_keywords[0]} 조례 위법 재의 제소 판례"
```

**After (맥락 기반 질문 방식)**:
```python
# 조례 분석 결과를 바탕으로 구체적인 질문 생성
query_parts = []

if ordinance_name:
    query_parts.append(f"'{ordinance_name}'과 유사한 내용의 조례 중에서")

if referenced_laws:
    laws_str = ', '.join(list(referenced_laws)[:3])
    query_parts.append(f"{laws_str}과 관련하여")

if article_topics:
    topics_str = ', '.join(article_topics[:3])
    query_parts.append(f"{topics_str}에 관한 규정에서")

combined_query = ' '.join(query_parts) + ' ' + base_question
```

**핵심 개선점**:
- 조례명, 참조 법령, 주요 주제를 맥락으로 제공
- 구체적인 정보 요구 사항 명시
- 어떤 세부 정보가 필요한지 상세히 설명

## 기대 효과

### 1. PDF 문서 활용 개선
- 업로드된 판례집, 가이드라인, 매뉴얼에서 실제로 정보 검색
- Gemini의 기본 지식이 아닌 실제 자료 기반 분석

### 2. 검색 정확도 향상
- 의미적으로 관련된 내용을 더 정확하게 찾음
- 맥락을 이해하므로 유사 사례를 효과적으로 검색

### 3. 위법성 판단 품질 개선
- 실제 판례와 사례를 바탕으로 한 분석
- 근거 있는 위법성 판단

## 테스트 방법

### 1. 쿼리 생성 검증
```bash
python test_semantic_search.py
```

### 2. 실제 조례 분석
1. Streamlit 앱 실행
2. 조례 파일 업로드
3. 분석 결과에서 다음 확인:
   - Gemini File Search 결과에 업로드된 PDF 내용 포함 여부
   - 위법성 판단 시 실제 판례 인용 여부
   - 참고 자료의 출처가 업로드된 문서인지 확인

## 참고 문서

- [Gemini File Search 공식 문서](https://ai.google.dev/gemini-api/docs/file-search?hl=ko)
- [File Search Tool 소개](https://blog.google/technology/developers/file-search-gemini-api/)
- [시맨틱 검색 최적화 가이드](https://www.analyticsvidhya.com/blog/2025/11/gemini-api-file-search/)

## 추가 최적화 가능성

### 1. 메타데이터 필터링
```python
# 문서 유형별 필터링
metadata={'type': '판례집'}
metadata={'type': '가이드라인'}
```

### 2. 청킹 전략 최적화
- 현재: 기본 설정 사용
- 개선 가능: 200 토큰, 20 토큰 오버랩 설정

### 3. 저장소 크기 관리
- 권장: 20GB 이하 유지
- 현재 상태 확인 필요

## 결론

**핵심 교훈**:
시맨틱 검색은 키워드 매칭이 아닌 의미 기반 검색이므로, **정보 요구를 명확하게 표현한 자연어 질문**이 가장 효과적입니다.

키워드를 나열하는 대신, "무엇을 찾고 싶은지", "어떤 맥락에서 찾는지", "어떤 세부 정보가 필요한지"를 자연스러운 문장으로 설명하면 Gemini가 업로드된 PDF 문서에서 의미적으로 관련된 내용을 찾아낼 수 있습니다.
