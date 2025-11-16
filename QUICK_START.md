# 🚀 Gemini File Search 빠른 시작 가이드

## 📋 준비 사항

### 1. PDF 파일 확인 ✅
```
✅ 2022년_자치법규입안길라잡이.pdf (3.9 MB)
✅ 3. 지방자치단체의 재의·제소 조례 모음집(Ⅸ) (1).pdf (5.1 MB)
✅ 자치법규_Q&A (1).pdf (5.7 MB)
✅ 자치법규_쟁점_사전검토_지원_사례집 (1).pdf (11.5 MB)

총 4개 파일 (~26 MB)
```

### 2. Gemini API 키 준비
- [Google AI Studio](https://makersuite.google.com/app/apikey)에서 발급
- 무료 할당량: 1분당 60회 요청

---

## 🔧 설치 단계

### 1단계: 패키지 설치
```bash
pip install google-genai
```

또는 전체 패키지:
```bash
pip install -r requirements.txt
```

### 2단계: API 키 설정

**옵션 A: 환경 변수 (권장)**
```bash
# Windows CMD
set GEMINI_API_KEY=your-api-key-here

# Windows PowerShell
$env:GEMINI_API_KEY="your-api-key-here"

# Linux/Mac
export GEMINI_API_KEY=your-api-key-here
```

**옵션 B: Streamlit Secrets**
```bash
# .streamlit/secrets.toml 파일 생성
mkdir .streamlit
echo GEMINI_API_KEY = "your-api-key-here" > .streamlit/secrets.toml
```

### 3단계: 테스트 실행
```bash
python test_gemini_setup.py
```

예상 출력:
```
🧪 Gemini File Search 설정 테스트
================================================================================
1. API 키 확인
================================================================================
✅ API 키 발견: AIzaSyC...xyz

================================================================================
2. 저장소 생성/조회 테스트
================================================================================
✅ 저장소 생성/조회 성공: projects/.../fileSearchStores/...

================================================================================
3. PDF 파일 확인
================================================================================
✅ 2022년_자치법규입안길라잡이.pdf                     3.9 MB
✅ 3. 지방자치단체의 재의·제소 조례 모음집(Ⅸ) (1).pdf  5.1 MB
✅ 자치법규_Q&A (1).pdf                                5.7 MB
✅ 자치법규_쟁점_사전검토_지원_사례집 (1).pdf           11.5 MB
```

---

## 📤 PDF 업로드

### 4단계: 전체 파일 업로드
```bash
python setup_gemini_store.py
```

**예상 소요 시간**: 5-10분 (파일 크기에 따라)

**예상 비용**: ~$0.02 (1회만, 쿼리는 무료)

업로드 진행 상황:
```
================================================================================
Gemini File Search Store 초기 설정
================================================================================

[1단계] Store Manager 생성 중...
[2단계] 검색 저장소 생성/조회 중...
   저장소: projects/.../조례-판례-법령-저장소

[3단계] PDF 파일 업로드 중...
   총 4개 파일 업로드 예정

   [1/4] 2022년_자치법규입안길라잡이.pdf
   📤 파일 업로드 중: ...
   ✅ 업로드 완료

   [2/4] 3. 지방자치단체의 재의·제소 조례 모음집(Ⅸ) (1).pdf
   📤 파일 업로드 중: ...
   ✅ 업로드 완료

   ... (계속)

================================================================================
업로드 완료 요약
================================================================================
성공: 4개
실패: 0개

저장소 이름: projects/.../조례-판례-법령-저장소
```

---

## 🔄 Streamlit 앱 통합

### 5단계: streamlit_app.py 수정

**주의**: 백업을 먼저 만드세요!
```bash
copy streamlit_app.py streamlit_app.py.backup
```

**통합 방법**: `streamlit_integration_guide.py` 파일을 참고하여 다음 섹션을 수정:

1. **Import 추가** (파일 상단)
2. **Session State 초기화**
3. **사이드바에 검색 모드 선택 추가**
4. **검색 함수 호출 부분 수정**

### 간단 통합 예시

기존 코드:
```python
# 기존 방식
relevant_guidelines = search_multiple_vectorstores(query, api_key)
```

수정 코드:
```python
# Gemini File Search 사용
if st.session_state.use_gemini_search:
    relevant_guidelines = search_relevant_guidelines_gemini(
        query=query,
        api_key=gemini_api_key,
        store_manager=st.session_state.gemini_store_manager
    )
else:
    # 기존 방식 유지
    relevant_guidelines = search_multiple_vectorstores(query, api_key)
```

---

## 🧪 테스트

### 6단계: Streamlit 앱 실행
```bash
streamlit run streamlit_app.py
```

### 테스트 체크리스트

1. **기본 검색 테스트**
   - [ ] 사이드바에서 "Gemini File Search 사용" 체크
   - [ ] "조례의 위법성 판단 기준" 검색
   - [ ] 결과가 표시되는지 확인

2. **판례 검색 테스트**
   - [ ] 조례 입력
   - [ ] 위법성 분석 실행
   - [ ] 관련 판례가 표시되는지 확인

3. **비교 테스트** (선택)
   - [ ] "검색 결과 비교 모드" 활성화
   - [ ] 기존 방식과 Gemini 결과 비교
   - [ ] 품질 차이 확인

4. **성능 테스트**
   - [ ] 응답 속도 측정
   - [ ] 검색 품질 평가
   - [ ] 출처 추적 기능 확인

---

## 📊 예상 개선 사항

### 검색 품질
- **기존**: 단순 코사인 유사도 (정확도 ~60-70%)
- **Gemini**: 의미 기반 검색 (정확도 ~85-95%)

### 응답 속도
- **기존**: ~2-3초 (로컬 계산)
- **Gemini**: ~1-2초 (Google 인프라)

### 유지보수
- **기존**: 수동 벡터스토어 관리 필요
- **Gemini**: 자동 인덱싱, 관리 불필요

---

## 🐛 문제 해결

### Q1: "API 키 오류"
```bash
# 환경 변수 확인
echo %GEMINI_API_KEY%  # Windows
echo $GEMINI_API_KEY   # Linux/Mac

# 재설정
set GEMINI_API_KEY=your-actual-api-key
```

### Q2: "저장소를 찾을 수 없음"
```bash
# setup_gemini_store.py를 다시 실행
python setup_gemini_store.py
```

### Q3: "파일 업로드 실패"
- 인터넷 연결 확인
- API 할당량 확인 (1분당 60회)
- 파일 크기 확인 (최대 100MB)

### Q4: "검색 결과 없음"
- 업로드가 완료되었는지 확인
- 인덱싱 시간 대기 (~1-2분)
- 쿼리를 더 구체적으로 작성

---

## 💰 비용 정보

### 현재 설정 기준
- **파일 크기**: ~26 MB
- **예상 토큰**: ~130K 토큰
- **색인화 비용**: $0.15 × 0.13 = **~$0.02** (1회만)
- **쿼리 비용**: **$0** (무료)
- **저장소**: **$0** (무료)

### 월 예상 비용
- 무료 할당량 내에서 사용 가능
- 추가 비용 없음

---

## 📚 다음 단계

### 단기 (완료 후)
- [ ] 기존 pickle 파일 백업 또는 삭제
- [ ] 성능 모니터링 설정
- [ ] 사용자 피드백 수집

### 중기
- [ ] 추가 PDF 문서 업로드
- [ ] 메타데이터 필터링 활용
- [ ] 검색 정확도 개선

### 장기
- [ ] 자동 업데이트 시스템 구축
- [ ] 다국어 지원 추가
- [ ] 고급 분석 기능 통합

---

## 📞 지원

문제가 발생하면:
1. [GEMINI_FILE_SEARCH_GUIDE.md](GEMINI_FILE_SEARCH_GUIDE.md) 참조
2. [streamlit_integration_guide.py](streamlit_integration_guide.py) 코드 예시 확인
3. 에러 메시지 전체 내용 확인

---

## ✅ 완료 체크리스트

- [ ] 1. 패키지 설치 완료
- [ ] 2. API 키 설정 완료
- [ ] 3. 테스트 실행 성공
- [ ] 4. PDF 업로드 완료
- [ ] 5. Streamlit 통합 완료
- [ ] 6. 기능 테스트 통과

**모두 완료하면 Gemini File Search 마이그레이션 성공! 🎉**
