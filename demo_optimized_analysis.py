"""
최적화된 위법성 분석 데모
법령명 정규화 및 Gemini API 호출 최적화 기능을 시연합니다.
"""

import streamlit as st
from comprehensive_violation_analysis import analyze_comprehensive_violations_optimized
import os

def main():
    st.set_page_config(
        page_title="최적화된 위법성 분석 데모",
        page_icon="⚖️",
        layout="wide"
    )

    st.title("⚖️ 최적화된 위법성 분석 시스템")
    st.markdown("---")

    st.markdown("""
    ## 🚀 주요 최적화 기능

    ### 1. 법령명 정규화
    - **국가법령정보센터 API** 연동
    - 띄어쓰기 차이 해결 (예: "지방자치법" ↔ "지방 자치법")
    - 중복 법령 자동 제거

    ### 2. Gemini API 호출 최적화
    - 고위험 사례만 선별 (위험도 0.6 이상)
    - 텍스트 길이 제한 (사례별 500자)
    - 관련 법령 상위 5개로 제한
    - **예상 효과**: API 호출 50-70% 절약

    ### 3. 분석 품질 향상
    - 정규화된 법령으로 정확한 분석
    - 중복 제거로 혼란 방지
    - 집중된 고위험 사례로 품질 개선
    """)

    st.markdown("---")

    # 조례안 입력
    st.header("📝 조례안 입력")

    sample_ordinance = """
제1조(목적) 이 조례는 지방자치법 제22조에 따라 주민의 복리 증진을 위한 사무를 규정함을 목적으로 한다.

제2조(정의) 이 조례에서 사용하는 용어의 뜻은 다음과 같다.
1. "허가사무"라 함은 법률에서 정한 사무를 말한다.
2. "지정사무"라 함은 시장이 지정하는 사무를 말한다.

제3조(권한의 위임) ① 시장은 필요하다고 인정하는 경우 법률에서 정하지 않은 사무라도 관련 부서에 위임할 수 있다.
② 전항의 위임사무에 대해서는 별도의 조례로 정할 수 있다.

제4조(처분권한) 시장은 건축허가, 환경영향평가 등의 처분권한을 행사할 수 있다.

제5조(재의요구) 시의회가 의결한 사항에 대하여 이 조례에서 정한 요건에 해당하지 않더라도 시장은 재의를 요구할 수 있다.
"""

    ordinance_text = st.text_area(
        "조례안을 입력하세요:",
        value=sample_ordinance,
        height=300
    )

    # PKL 파일 경로 설정
    pkl_files = []
    pkl_path = r"C:\jo(9.11.)\enhanced_vectorstore_20250914_101739.pkl"
    if os.path.exists(pkl_path):
        pkl_files.append(pkl_path)
        st.success(f"✅ PKL 파일 발견: {os.path.basename(pkl_path)}")
    else:
        st.error("❌ PKL 파일을 찾을 수 없습니다.")
        st.info("PKL 파일 경로를 확인해주세요.")

    # 분석 실행 버튼
    if st.button("🔍 최적화된 위법성 분석 실행", type="primary") and pkl_files:

        with st.spinner("분석 중..."):
            # 최적화된 분석 실행
            result = analyze_comprehensive_violations_optimized(ordinance_text, pkl_files)

            if result.get('success'):
                st.success("✅ 분석 완료!")

                # 결과 요약
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "분석된 조문 수",
                        result['articles_count']
                    )

                with col2:
                    st.metric(
                        "위험 발견 조문",
                        result['violations_found']
                    )

                with col3:
                    reduction_rate = result['law_normalization'].get('reduction_rate', 0)
                    st.metric(
                        "법령명 중복 제거율",
                        f"{reduction_rate:.1f}%"
                    )

                # 최적화 효과
                st.markdown("---")
                st.header("📊 최적화 효과")

                optimization = result['optimization_summary']

                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("🎯 위법 사례 최적화")
                    st.write(f"- 전체 사례: {optimization['original_violations']}개")
                    st.write(f"- 선별된 사례: {optimization['selected_violations']}개")

                    if optimization['original_violations'] > 0:
                        selection_rate = (optimization['selected_violations'] / optimization['original_violations']) * 100
                        st.write(f"- 선별율: {selection_rate:.1f}%")
                        st.write(f"- **API 호출 절약**: {100 - selection_rate:.1f}%")

                with col2:
                    st.subheader("📋 법령명 정규화")
                    st.write(f"- 원본 법령 수: {optimization['laws_original']}개")
                    st.write(f"- 정규화 후: {optimization['laws_normalized']}개")
                    st.write(f"- **중복 제거 효과**: {optimization['reduction_rate']:.1f}%")

                # 정규화된 법령 미리보기
                if result['law_normalization'].get('law_details'):
                    st.markdown("---")
                    st.header("📋 정규화된 관련 법령")

                    law_details = result['law_normalization']['law_details'][:5]  # 상위 5개만

                    for i, law in enumerate(law_details, 1):
                        with st.expander(f"{i}. {law['law_name']}", expanded=False):
                            col1, col2 = st.columns(2)

                            with col1:
                                if law.get('law_number'):
                                    st.write(f"**법령번호**: {law['law_number']}")
                                if law.get('law_type'):
                                    st.write(f"**법령유형**: {law['law_type']}")
                                if law.get('enforcement_date'):
                                    st.write(f"**시행일자**: {law['enforcement_date']}")

                            with col2:
                                st.write(f"**유사도**: {law.get('similarity_score', 0):.2f}")
                                if law.get('related_articles'):
                                    st.write(f"**관련 조문**: {len(law['related_articles'])}개")
                                    st.write("- " + "\n- ".join(law['related_articles'][:3]))

                                if law.get('api_error'):
                                    st.warning(f"API 오류: {law['api_error']}")

                # Gemini 프롬프트 미리보기
                st.markdown("---")
                st.header("🤖 생성된 Gemini 프롬프트")

                prompt_preview = result['gemini_prompt'][:1000]
                st.text_area(
                    "프롬프트 미리보기 (처음 1000자):",
                    value=prompt_preview + "..." if len(result['gemini_prompt']) > 1000 else prompt_preview,
                    height=200,
                    disabled=True
                )

                # 전체 프롬프트 다운로드
                if st.button("📄 전체 프롬프트 다운로드"):
                    st.download_button(
                        label="💾 Gemini 프롬프트 텍스트 파일로 저장",
                        data=result['gemini_prompt'],
                        file_name="optimized_gemini_prompt.txt",
                        mime="text/plain"
                    )

                # 상세 분석 결과
                with st.expander("🔍 상세 분석 데이터", expanded=False):
                    st.json(result['optimized_payload'])

            else:
                st.error(f"❌ 분석 실패: {result.get('error', '알 수 없는 오류')}")

    # 추가 정보
    st.markdown("---")
    st.header("💡 사용 가이드")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🎯 최적화 전략")
        st.markdown("""
        1. **고위험 우선**: 위험도 0.6 이상만 선별
        2. **텍스트 제한**: 사례별 500자로 압축
        3. **상위 법령**: 유사도 기준 상위 5개
        4. **중복 제거**: 85% 유사도로 통합
        """)

    with col2:
        st.subheader("📈 예상 효과")
        st.markdown("""
        - **API 비용**: 50-70% 절감
        - **분석 품질**: 고위험 집중으로 향상
        - **처리 속도**: 데이터 압축으로 개선
        - **정확도**: 정규화로 오류 감소
        """)

if __name__ == "__main__":
    main()