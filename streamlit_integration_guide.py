"""
streamlit_app.py에 추가할 Gemini File Search 통합 코드

이 코드를 streamlit_app.py의 적절한 위치에 추가하세요.
"""

# ============================================================================
# 1. 파일 상단 import 섹션에 추가
# ============================================================================

# 기존 import 아래에 추가
from gemini_file_search import (
    GeminiFileSearchManager,
    search_relevant_guidelines_gemini,
    search_violation_cases_gemini,
    get_gemini_store_manager
)

# ============================================================================
# 2. Session State 초기화 섹션에 추가 (기존 vector_store 초기화 근처)
# ============================================================================

# Gemini File Search 사용 여부 플래그
if 'use_gemini_search' not in st.session_state:
    st.session_state.use_gemini_search = False

# Gemini Store Manager
if 'gemini_store_manager' not in st.session_state:
    st.session_state.gemini_store_manager = None

# ============================================================================
# 3. API 키 설정 섹션 수정 (기존 Gemini API 키 설정 부분)
# ============================================================================

# 기존 코드:
# gemini_api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")

# 수정된 코드:
gemini_api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")

# Gemini File Search Store Manager 초기화
if gemini_api_key and st.session_state.gemini_store_manager is None:
    try:
        st.session_state.gemini_store_manager = get_gemini_store_manager(gemini_api_key)
        print("✅ Gemini File Search Store Manager 초기화 완료")
    except Exception as e:
        print(f"⚠️ Gemini File Search Store Manager 초기화 실패: {e}")

# ============================================================================
# 4. 사이드바에 RAG 모드 선택 옵션 추가
# ============================================================================

# 사이드바 섹션에 추가
with st.sidebar:
    st.markdown("---")
    st.subheader("🔍 검색 엔진 설정")

    use_gemini = st.checkbox(
        "Gemini File Search 사용 (권장)",
        value=st.session_state.use_gemini_search,
        help="기존 pickle 기반 검색 대신 Gemini File Search API를 사용합니다. 더 정확한 검색 결과를 제공합니다."
    )
    st.session_state.use_gemini_search = use_gemini

    if use_gemini:
        if st.session_state.gemini_store_manager:
            st.success("✅ Gemini File Search 활성화됨")
        else:
            st.warning("⚠️ Gemini API 키를 설정해주세요")
            st.info("환경 변수 GEMINI_API_KEY를 설정하거나 .streamlit/secrets.toml에 추가하세요.")
    else:
        st.info("기존 pickle 기반 검색을 사용합니다")

# ============================================================================
# 5. 검색 함수 호출 부분 수정 (여러 곳에 적용)
# ============================================================================

# 예시 1: 관련 가이드라인 검색
# 기존 코드를 찾아서 수정:

# [기존 코드]
# relevant_guidelines, loaded_stores = search_multiple_vectorstores(
#     search_query_pkl,
#     api_key=gemini_api_key,
#     top_k_per_store=3
# )

# [수정된 코드]
if st.session_state.use_gemini_search and st.session_state.gemini_store_manager:
    # Gemini File Search 사용
    try:
        relevant_guidelines = search_relevant_guidelines_gemini(
            query=search_query_pkl,
            api_key=gemini_api_key,
            store_manager=st.session_state.gemini_store_manager,
            top_k=5
        )
        st.info(f"🔍 Gemini File Search: {len(relevant_guidelines)}개 결과 발견")
    except Exception as e:
        st.error(f"Gemini 검색 오류: {e}")
        # 폴백: 기존 방식 사용
        relevant_guidelines, loaded_stores = search_multiple_vectorstores(
            search_query_pkl,
            api_key=gemini_api_key,
            top_k_per_store=3
        )
        st.warning("기존 검색 방식으로 폴백했습니다.")
else:
    # 기존 pickle 기반 검색
    relevant_guidelines, loaded_stores = search_multiple_vectorstores(
        search_query_pkl,
        api_key=gemini_api_key,
        top_k_per_store=3
    )

# ============================================================================
# 예시 2: 위법성 판례 검색
# ============================================================================

# [기존 코드]
# violation_cases = search_comprehensive_violation_cases(
#     ordinance_articles,
#     vectorstore_paths,
#     max_results=12
# )

# [수정된 코드]
if st.session_state.use_gemini_search and st.session_state.gemini_store_manager:
    # Gemini File Search 사용
    try:
        violation_cases = search_violation_cases_gemini(
            ordinance_articles=ordinance_articles,
            api_key=gemini_api_key,
            store_manager=st.session_state.gemini_store_manager,
            max_results=12
        )
        st.info(f"📚 Gemini File Search: {len(violation_cases)}개 판례 발견")
    except Exception as e:
        st.error(f"Gemini 판례 검색 오류: {e}")
        # 폴백: 기존 방식
        violation_cases = search_comprehensive_violation_cases(
            ordinance_articles,
            vectorstore_paths,
            max_results=12
        )
else:
    # 기존 방식
    violation_cases = search_comprehensive_violation_cases(
        ordinance_articles,
        vectorstore_paths,
        max_results=12
    )

# ============================================================================
# 6. 결과 표시 형식 조정 (필요시)
# ============================================================================

# Gemini File Search 결과도 기존 형식과 동일하게 표시됨
# 추가 정보를 표시하고 싶다면:

if st.session_state.use_gemini_search:
    st.markdown("---")
    st.caption("🤖 Powered by Gemini File Search API")

# ============================================================================
# 7. 비교 모드 (선택사항 - 디버깅/테스트용)
# ============================================================================

# 사이드바에 비교 모드 추가
with st.sidebar:
    if st.checkbox("🔬 검색 결과 비교 모드", value=False):
        st.session_state.comparison_mode = True
    else:
        st.session_state.comparison_mode = False

# 비교 모드 활성화 시 양쪽 결과 모두 표시
if st.session_state.get('comparison_mode', False):
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("기존 방식 (Pickle)")
        old_results = search_multiple_vectorstores(
            search_query_pkl,
            api_key=gemini_api_key,
            top_k_per_store=3
        )[0]
        st.write(f"결과: {len(old_results)}개")
        for i, result in enumerate(old_results[:3], 1):
            st.write(f"{i}. 유사도: {result.get('similarity', 0):.3f}")
            st.caption(result.get('text', '')[:200])

    with col2:
        st.subheader("Gemini File Search")
        if st.session_state.gemini_store_manager:
            new_results = search_relevant_guidelines_gemini(
                query=search_query_pkl,
                api_key=gemini_api_key,
                store_manager=st.session_state.gemini_store_manager,
                top_k=5
            )
            st.write(f"결과: {len(new_results)}개")
            for i, result in enumerate(new_results[:3], 1):
                st.write(f"{i}. 순위 기반 점수: {result.get('similarity', 0):.3f}")
                st.caption(result.get('text', '')[:200])
        else:
            st.error("Gemini Store Manager가 초기화되지 않았습니다")

# ============================================================================
# 8. 통합 완료 체크리스트
# ============================================================================

"""
✅ 체크리스트:

1. [ ] import 문 추가됨
2. [ ] Session state 초기화 추가됨
3. [ ] Gemini API 키 설정 확인
4. [ ] 사이드바에 검색 엔진 선택 옵션 추가됨
5. [ ] 모든 검색 함수 호출 부분 수정됨
6. [ ] 폴백 로직 구현됨
7. [ ] 에러 핸들링 추가됨
8. [ ] 테스트 완료

다음 단계:
1. streamlit_app.py 백업 생성
2. 위 코드를 적절한 위치에 통합
3. python test_gemini_setup.py 실행
4. streamlit run streamlit_app.py 실행
5. 기능 테스트
"""
