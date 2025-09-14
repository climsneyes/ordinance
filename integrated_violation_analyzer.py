"""
통합 위법성 분석기
법령명 중복 제거 + Gemini API 최적화가 통합된 완전한 솔루션
"""

import streamlit as st
from law_name_deduplicator import SimpleLawNameDeduplicator
import re
from typing import List, Dict, Any
import json

class IntegratedViolationAnalyzer:
    def __init__(self):
        self.deduplicator = SimpleLawNameDeduplicator()

    def extract_laws_from_violations(self, violation_results: List[Dict]) -> List[str]:
        """위법성 분석 결과에서 법령명 추출"""
        law_names = []

        for result in violation_results:
            # 결과에서 텍스트 추출
            text_content = self._extract_text_from_result(result)

            # 법령명 패턴 찾기
            extracted_laws = self._find_law_patterns(text_content)
            law_names.extend(extracted_laws)

        return list(set(law_names))  # 중복 제거

    def _extract_text_from_result(self, result: Dict) -> str:
        """결과 딕셔너리에서 모든 텍스트 추출"""
        text_parts = []

        if isinstance(result, dict):
            for key, value in result.items():
                if isinstance(value, str):
                    text_parts.append(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            text_parts.append(item)
                        elif isinstance(item, dict):
                            text_parts.append(self._extract_text_from_result(item))

        return " ".join(text_parts)

    def _find_law_patterns(self, text: str) -> List[str]:
        """텍스트에서 법령명 패턴 찾기"""
        patterns = [
            r'([가-힣\s]*?법률?)[.\s,)]',
            r'([가-힣\s]*?시행령)[.\s,)]',
            r'([가-힣\s]*?시행규칙)[.\s,)]',
            r'([가-힣\s]*?조례)[.\s,)]',
            r'([가-힣\s]*?규정)[.\s,)]',
            r'(지방자치법)',
            r'(공공기관의\s*운영에\s*관한\s*법률?)',
            r'(행정절차법)',
            r'(국가재정법)',
            r'(헌법)',
        ]

        found_laws = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                clean_name = re.sub(r'\s+', ' ', match).strip()
                if len(clean_name) >= 3 and clean_name not in found_laws:
                    found_laws.append(clean_name)

        return found_laws

    def process_with_deduplication(self, violation_results: List[Dict]) -> Dict[str, Any]:
        """위법성 결과를 중복 제거하여 처리"""

        st.write("### 🔧 법령명 중복 제거 처리 중...")

        # 1. 법령명 추출
        extracted_laws = self.extract_laws_from_violations(violation_results)
        st.write(f"📊 추출된 법령명: {len(extracted_laws)}개")

        if not extracted_laws:
            st.warning("추출된 법령명이 없습니다.")
            return {'error': '법령명을 찾을 수 없습니다'}

        # 2. 중복 분석 및 제거
        analysis = self.deduplicator.analyze_duplications(extracted_laws)

        st.write(f"✅ 중복 제거 완료: {analysis['original_count']}개 → {analysis['deduplicated_count']}개")

        if analysis['reduction_count'] > 0:
            st.success(f"🎯 {analysis['reduction_count']}개 중복 법령 제거 ({analysis['reduction_rate']:.1f}% 절약)")

        # 3. 중복 그룹 정보 표시
        if analysis['duplicate_groups']:
            with st.expander("🔍 중복 제거 상세 정보", expanded=False):
                for i, group in enumerate(analysis['duplicate_groups'], 1):
                    best_name = self.deduplicator.select_best_name(group)
                    st.write(f"**그룹 {i}**: {best_name}")
                    for law in group:
                        st.write(f"  - {law}")

        # 4. 법령별로 위법성 결과 재구성
        restructured_results = self._restructure_by_laws(
            violation_results,
            analysis['duplicate_groups'],
            analysis['deduplicated_laws']
        )

        return {
            'success': True,
            'original_law_count': analysis['original_count'],
            'deduplicated_law_count': analysis['deduplicated_count'],
            'reduction_rate': analysis['reduction_rate'],
            'duplicate_groups': analysis['duplicate_groups'],
            'deduplicated_laws': analysis['deduplicated_laws'],
            'restructured_results': restructured_results,
            'optimization_summary': {
                'laws_processed': len(extracted_laws),
                'duplicates_removed': analysis['reduction_count'],
                'efficiency_gain': analysis['reduction_rate'],
                'expected_api_savings': analysis['reduction_count']
            }
        }

    def _restructure_by_laws(self, violation_results: List[Dict], duplicate_groups: List[List[str]], deduplicated_laws: List[str]) -> List[Dict]:
        """법령별로 위법성 결과 재구성"""

        # 법령명 매핑 생성 (원본 → 표준명)
        law_mapping = {}

        for group in duplicate_groups:
            standard_name = self.deduplicator.select_best_name(group)
            for law_name in group:
                law_mapping[law_name] = standard_name

        # 그룹에 속하지 않은 법령도 매핑에 추가
        all_grouped_laws = set()
        for group in duplicate_groups:
            all_grouped_laws.update(group)

        for law in deduplicated_laws:
            if law not in all_grouped_laws:
                law_mapping[law] = law

        # 표준 법령명별로 결과 그룹화
        law_based_results = {}

        for result in violation_results:
            text_content = self._extract_text_from_result(result)
            found_laws = self._find_law_patterns(text_content)

            # 이 결과가 관련된 표준 법령명들 찾기
            related_standard_laws = set()
            for found_law in found_laws:
                # 정규화 후 매핑에서 찾기
                normalized = self.deduplicator.normalize_law_name(found_law)
                for original, standard in law_mapping.items():
                    if self.deduplicator.calculate_similarity(normalized, original) >= 0.8:
                        related_standard_laws.add(standard)
                        break

            # 각 표준 법령에 결과 추가
            for standard_law in related_standard_laws:
                if standard_law not in law_based_results:
                    law_based_results[standard_law] = {
                        'law_name': standard_law,
                        'violation_cases': [],
                        'total_risk_score': 0,
                        'case_count': 0
                    }

                law_based_results[standard_law]['violation_cases'].append(result)
                law_based_results[standard_law]['case_count'] += 1

                # 위험도 점수 누적 (결과에 있다면)
                if isinstance(result, dict) and 'risk_score' in result:
                    law_based_results[standard_law]['total_risk_score'] += result['risk_score']

        # 평균 위험도 계산 및 정렬
        final_results = []
        for law_name, data in law_based_results.items():
            avg_risk = data['total_risk_score'] / data['case_count'] if data['case_count'] > 0 else 0

            final_results.append({
                'law_name': law_name,
                'case_count': data['case_count'],
                'average_risk_score': avg_risk,
                'total_risk_score': data['total_risk_score'],
                'violation_cases': data['violation_cases'][:5],  # 상위 5개만 저장
                'summary': f"{law_name}에 대한 {data['case_count']}개 위법 사례 (평균 위험도: {avg_risk:.2f})"
            })

        # 위험도 순으로 정렬
        final_results.sort(key=lambda x: x['average_risk_score'], reverse=True)

        return final_results

    def create_optimized_gemini_prompt(self, processed_results: Dict[str, Any]) -> str:
        """최적화된 Gemini 프롬프트 생성"""

        if not processed_results.get('success'):
            return "분석 결과가 없습니다."

        restructured = processed_results['restructured_results']
        optimization = processed_results['optimization_summary']

        prompt_parts = []

        # 헤더 및 최적화 정보
        prompt_parts.append(f"""# 조례 위법성 종합 분석 (중복 제거 최적화)

## 최적화 성과
- 원본 법령 수: {optimization['laws_processed']}개
- 중복 제거 후: {processed_results['deduplicated_law_count']}개
- 중복 제거율: {processed_results['reduction_rate']:.1f}%
- API 호출 절약: {optimization['expected_api_savings']}회 예상

## 주요 위법 위험 법령 (위험도 순)

""")

        # 상위 10개 법령만 포함 (API 효율성)
        top_laws = restructured[:10]

        for i, law_data in enumerate(top_laws, 1):
            prompt_parts.append(f"""
### {i}. {law_data['law_name']}
- 위법 사례 수: {law_data['case_count']}개
- 평균 위험도: {law_data['average_risk_score']:.2f}
- 총 위험 점수: {law_data['total_risk_score']:.2f}
- 분석 요약: {law_data['summary']}

""")

        # 분석 요청
        prompt_parts.append("""
## 분석 요청

위 최적화된 정보를 바탕으로 다음 사항을 분석해주세요:

1. **위법성 우선순위**: 평균 위험도와 사례 수를 고려한 시급성 평가
2. **중복 제거 효과**: 정확한 법령별 분석이 가능해진 장점 설명
3. **핵심 개선사항**: 위험도가 높은 상위 3개 법령에 대한 구체적 개선 방안
4. **법적 근거**: 각 위법 유형별 관련 법조문 및 판례
5. **실행 계획**: 우선순위에 따른 단계별 조례 개선 로드맵

**분석 장점**:
- 중복 법령이 통합되어 혼란 없는 정확한 분석
- 법령별 종합적 위험도 평가 가능
- API 호출 최적화로 비용 효율적 분석

""")

        return "".join(prompt_parts)

def demo_integrated_analyzer():
    """통합 분석기 데모"""

    st.title("🚀 통합 위법성 분석기")
    st.markdown("법령명 중복 제거 + Gemini API 최적화 통합 솔루션")
    st.markdown("---")

    # 샘플 위법성 분석 결과
    sample_violation_results = [
        {
            "content": "공공기관의운영에관한법률 제4조에 따르면 지방자치단체는 기관위임사무를 처리할 때...",
            "violation_type": "기관위임사무 위반",
            "risk_score": 0.85,
            "similarity": 0.92
        },
        {
            "content": "공공기관의 운영에 관한법률 제10조 위반으로 인한 권한 위임 한계 초과 사례",
            "violation_type": "권한위임 한계 초과",
            "risk_score": 0.78,
            "similarity": 0.88
        },
        {
            "content": "공공기관의 운영에 관한 법률에 따른 감독권한을 지방자치법 제22조와 함께 검토하면...",
            "violation_type": "감독권한 범위 위반",
            "risk_score": 0.65,
            "similarity": 0.75
        },
        {
            "content": "지방자치법과 행정 절차 법의 규정에 따른 절차적 하자가 발견됨",
            "violation_type": "절차적 하자",
            "risk_score": 0.55,
            "similarity": 0.70
        },
        {
            "content": "지방 자치법 제9조와 국가 재정법의 충돌로 인한 위법 소지",
            "violation_type": "상위법령 충돌",
            "risk_score": 0.72,
            "similarity": 0.82
        }
    ]

    # 샘플 데이터 표시
    st.subheader("📊 샘플 위법성 분석 결과")
    with st.expander("원본 데이터 보기", expanded=False):
        st.json(sample_violation_results)

    if st.button("🔍 통합 분석 실행", type="primary"):

        analyzer = IntegratedViolationAnalyzer()

        with st.spinner("통합 분석 처리 중..."):
            # 통합 분석 실행
            processed_results = analyzer.process_with_deduplication(sample_violation_results)

        if processed_results.get('success'):
            st.success("✅ 통합 분석 완료!")

            # 최적화 효과 표시
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("원본 법령", f"{processed_results['original_law_count']}개")

            with col2:
                st.metric("정리 후", f"{processed_results['deduplicated_law_count']}개")

            with col3:
                st.metric("중복 제거율", f"{processed_results['reduction_rate']:.1f}%")

            with col4:
                st.metric("API 절약", f"{processed_results['optimization_summary']['expected_api_savings']}회")

            # 법령별 분석 결과
            st.subheader("📋 법령별 위법성 분석")

            for result in processed_results['restructured_results']:
                with st.expander(f"⚖️ {result['law_name']} (위험도: {result['average_risk_score']:.2f})", expanded=False):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**사례 수**: {result['case_count']}개")
                        st.write(f"**평균 위험도**: {result['average_risk_score']:.2f}")
                        st.write(f"**총 위험 점수**: {result['total_risk_score']:.2f}")

                    with col2:
                        st.write("**주요 위법 유형**:")
                        for case in result['violation_cases'][:3]:
                            if isinstance(case, dict) and 'violation_type' in case:
                                st.write(f"- {case['violation_type']}")

            # 최적화된 Gemini 프롬프트
            st.subheader("🤖 최적화된 Gemini 프롬프트")

            optimized_prompt = analyzer.create_optimized_gemini_prompt(processed_results)

            st.text_area(
                "생성된 프롬프트 (처음 1000자):",
                optimized_prompt[:1000] + "..." if len(optimized_prompt) > 1000 else optimized_prompt,
                height=200
            )

            # 다운로드 버튼
            st.download_button(
                label="📄 전체 프롬프트 다운로드",
                data=optimized_prompt,
                file_name="optimized_violation_analysis_prompt.txt",
                mime="text/plain"
            )

            # 최적화 요약
            st.subheader("📈 최적화 요약")

            optimization = processed_results['optimization_summary']

            st.info(f"""
            **🎯 최적화 성과**:
            - 법령 중복 {optimization['duplicates_removed']}개 제거
            - 분석 효율성 {optimization['efficiency_gain']:.1f}% 향상
            - Gemini API 호출 {optimization['expected_api_savings']}회 절약
            - 법령별 종합 위험도 평가 가능
            - 중복으로 인한 혼란 제거
            """)

        else:
            st.error(f"❌ 분석 실패: {processed_results.get('error', '알 수 없는 오류')}")

if __name__ == "__main__":
    demo_integrated_analyzer()