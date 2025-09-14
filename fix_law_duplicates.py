"""
실제 데이터에서 법령명 중복 문제를 해결하는 실용적인 스크립트
"""

from law_name_deduplicator import SimpleLawNameDeduplicator
from typing import List, Dict, Any
import streamlit as st

def process_violation_results_with_deduplication(violation_results: List[Dict]) -> List[Dict]:
    """위법성 분석 결과에서 법령명 중복을 제거하고 통합"""

    if not violation_results:
        return violation_results

    deduplicator = SimpleLawNameDeduplicator()

    st.write("### 🔧 법령명 중복 제거 처리")

    # 1. 모든 법령명 추출
    all_law_names = []
    law_name_to_results = {}  # 법령명별 관련 결과들 매핑

    for result in violation_results:
        # 결과에서 법령명 추출 (실제 데이터 구조에 따라 조정 필요)
        law_names = extract_law_names_from_result(result)

        for law_name in law_names:
            if law_name not in law_name_to_results:
                law_name_to_results[law_name] = []
            law_name_to_results[law_name].append(result)
            all_law_names.append(law_name)

    st.write(f"📊 추출된 법령명: {len(set(all_law_names))}개 (중복 포함: {len(all_law_names)}개)")

    # 2. 중복 분석 및 제거
    analysis = deduplicator.analyze_duplications(list(set(all_law_names)))

    if analysis['reduction_count'] > 0:
        st.success(f"✅ 중복 제거 효과: {analysis['reduction_count']}개 법령 정리 ({analysis['reduction_rate']:.1f}% 절약)")

        # 중복 그룹 표시
        with st.expander("🔍 중복 제거 상세", expanded=False):
            for i, group in enumerate(analysis['duplicate_groups'], 1):
                best_name = deduplicator.select_best_name(group)
                st.write(f"**그룹 {i}**: {best_name}")
                for law in group:
                    st.write(f"  - {law}")

    # 3. 통합된 결과 생성
    consolidated_results = consolidate_results_by_law(
        violation_results,
        analysis['duplicate_groups'],
        deduplicator
    )

    st.write(f"📋 최종 결과: {len(consolidated_results)}개 법령으로 정리")

    return consolidated_results

def extract_law_names_from_result(result: Dict) -> List[str]:
    """결과 데이터에서 법령명 추출 (실제 데이터 구조에 맞게 수정 필요)"""
    law_names = []

    # 결과 텍스트에서 법령명 패턴 찾기
    text_content = ""

    # 여러 텍스트 필드에서 내용 수집
    if isinstance(result, dict):
        for key, value in result.items():
            if isinstance(value, str) and any(keyword in key.lower() for keyword in ['content', 'text', 'summary', 'title']):
                text_content += value + " "
    elif isinstance(result, str):
        text_content = result

    # 법령명 패턴 추출
    import re
    patterns = [
        r'([^.\n]*?법률?)[.\s,]',
        r'([^.\n]*?령)[.\s,]',
        r'([^.\n]*?규칙)[.\s,]',
        r'([^.\n]*?조례)[.\s,]',
        r'(지방자치법)',
        r'(공공기관의\s*운영에\s*관한\s*법률?)',
        r'(행정절차법)',
        r'(국가재정법)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text_content, re.IGNORECASE)
        for match in matches:
            clean_name = re.sub(r'\s+', ' ', match).strip()
            if len(clean_name) >= 3 and clean_name not in law_names:
                law_names.append(clean_name)

    return law_names

def consolidate_results_by_law(violation_results: List[Dict], duplicate_groups: List[List[str]], deduplicator) -> List[Dict]:
    """중복 법령을 기준으로 결과들을 통합"""

    # 각 그룹의 표준 법령명 결정
    law_mapping = {}  # 원본 법령명 -> 표준 법령명

    for group in duplicate_groups:
        standard_name = deduplicator.select_best_name(group)
        for law_name in group:
            law_mapping[law_name] = standard_name

    # 그룹화되지 않은 법령들도 매핑에 추가
    all_laws_in_groups = set()
    for group in duplicate_groups:
        all_laws_in_groups.update(group)

    for result in violation_results:
        law_names = extract_law_names_from_result(result)
        for law_name in law_names:
            if law_name not in all_laws_in_groups:
                law_mapping[law_name] = deduplicator.normalize_law_name(law_name)

    # 표준 법령명별로 결과 그룹화
    consolidated = {}

    for result in violation_results:
        law_names = extract_law_names_from_result(result)

        # 이 결과가 속할 표준 법령명들 찾기
        standard_laws = set()
        for law_name in law_names:
            if law_name in law_mapping:
                standard_laws.add(law_mapping[law_name])

        # 각 표준 법령명에 이 결과 추가
        for standard_law in standard_laws:
            if standard_law not in consolidated:
                consolidated[standard_law] = {
                    'law_name': standard_law,
                    'original_names': set(),
                    'related_results': [],
                    'total_content_length': 0
                }

            consolidated[standard_law]['original_names'].update(law_names)
            consolidated[standard_law]['related_results'].append(result)

            # 내용 길이 계산 (대략적)
            content = str(result)
            consolidated[standard_law]['total_content_length'] += len(content)

    # 최종 결과 리스트로 변환
    final_results = []
    for standard_law, data in consolidated.items():
        final_result = {
            'standard_law_name': standard_law,
            'original_law_names': list(data['original_names']),
            'related_results_count': len(data['related_results']),
            'total_content_length': data['total_content_length'],
            'related_results': data['related_results'][:5],  # 상위 5개만 포함
            'summary': f"{standard_law}에 대한 {len(data['related_results'])}개 위법 사례"
        }
        final_results.append(final_result)

    # 관련 결과 수 기준으로 정렬
    final_results.sort(key=lambda x: x['related_results_count'], reverse=True)

    return final_results

def create_gemini_optimized_prompt(consolidated_results: List[Dict]) -> str:
    """통합된 결과로 최적화된 Gemini 프롬프트 생성"""

    if not consolidated_results:
        return "분석할 데이터가 없습니다."

    prompt_parts = []

    # 헤더
    prompt_parts.append("# 조례 위법성 종합 분석 (최적화됨)\n")

    # 요약
    total_laws = len(consolidated_results)
    total_cases = sum(result['related_results_count'] for result in consolidated_results)

    prompt_parts.append(f"""
## 분석 개요
- 관련 법령: {total_laws}개 (중복 제거 후)
- 총 위법 사례: {total_cases}개
- 최적화 효과: 중복 법령 통합으로 분석 효율성 향상

## 주요 위법 위험 법령

""")

    # 상위 10개 법령만 포함 (Gemini API 효율성)
    top_results = consolidated_results[:10]

    for i, result in enumerate(top_results, 1):
        prompt_parts.append(f"""
### {i}. {result['standard_law_name']}
- 위법 사례 수: {result['related_results_count']}개
- 원본 법령명: {', '.join(result['original_law_names'][:3])}{'...' if len(result['original_law_names']) > 3 else ''}
- 내용 분량: {result['total_content_length']:,}자
- 요약: {result['summary']}

""")

    # 분석 요청
    prompt_parts.append("""
## 분석 요청

위 정보를 바탕으로 다음 사항을 분석해주세요:

1. **위법성 우선순위**: 위험도가 높은 법령 순으로 평가
2. **통합 분석의 장점**: 중복 제거로 얻은 분석 품질 개선 효과
3. **핵심 개선 방안**: 가장 시급한 3가지 조례 수정사항
4. **법적 근거**: 각 위법 위험에 대한 구체적 법적 근거

**참고사항**: 중복된 법령명이 하나로 통합되어 더 정확한 분석이 가능합니다.
""")

    final_prompt = "".join(prompt_parts)

    return final_prompt

# 데모 함수
def demo_fix_duplicates():
    st.title("🔧 실제 데이터 법령명 중복 해결")

    # 샘플 데이터 (실제 위법성 분석 결과 형태 시뮬레이션)
    sample_results = [
        {
            "content": "공공기관의운영에관한법률 제4조에 따르면 지방자치단체는...",
            "summary": "기관위임사무 위반 사례",
            "risk_score": 0.8
        },
        {
            "content": "공공기관의 운영에 관한법률 제10조 위반으로 인한...",
            "summary": "권한 위임 한계 초과",
            "risk_score": 0.7
        },
        {
            "content": "공공기관의 운영에 관한 법률에 따른 감독권한을...",
            "summary": "감독권한 범위 위반",
            "risk_score": 0.6
        },
        {
            "content": "지방자치법 제22조와 행정 절차 법 규정에...",
            "summary": "절차적 하자",
            "risk_score": 0.5
        },
    ]

    st.subheader("📊 샘플 데이터")
    st.json(sample_results)

    if st.button("🚀 중복 제거 및 최적화 실행"):

        # 중복 제거 처리
        consolidated = process_violation_results_with_deduplication(sample_results)

        st.subheader("📋 통합 결과")
        for result in consolidated:
            with st.expander(f"📄 {result['standard_law_name']} ({result['related_results_count']}개 사례)", expanded=False):
                st.write(f"**원본 법령명들:** {', '.join(result['original_law_names'])}")
                st.write(f"**관련 사례 수:** {result['related_results_count']}개")
                st.write(f"**내용 분량:** {result['total_content_length']:,}자")
                st.write(f"**요약:** {result['summary']}")

        # 최적화된 Gemini 프롬프트 생성
        st.subheader("🤖 최적화된 Gemini 프롬프트")
        prompt = create_gemini_optimized_prompt(consolidated)

        st.text_area("생성된 프롬프트:", prompt, height=300)

        # 최적화 효과 표시
        original_count = len(sample_results)
        consolidated_count = len(consolidated)

        if original_count > consolidated_count:
            st.success(f"""
            🎯 **최적화 효과**
            - 원본 분석 대상: {original_count}개 결과
            - 통합 후: {consolidated_count}개 법령 그룹
            - API 호출 효율성: {((original_count - consolidated_count) / original_count * 100):.1f}% 개선
            """)

if __name__ == "__main__":
    demo_fix_duplicates()