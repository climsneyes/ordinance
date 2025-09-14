"""
간단한 법령명 중복 제거 유틸리티
API 없이도 기본적인 띄어쓰기 통일과 중복 제거 수행
"""

import re
from difflib import SequenceMatcher
from typing import List, Dict
import streamlit as st

class SimpleLawNameDeduplicator:
    def __init__(self):
        # 기본적인 법령명 정규화 규칙
        self.normalization_rules = {
            # 공백 정규화
            r'\s+': ' ',
            # 괄호 정규화
            r'[\(\（]([^\)\）]*?)[\)\）]': r'(\1)',
            # 법령 접미사 정규화
            r'에\s*관한\s*법률': '에 관한 법률',
            r'에\s*대한\s*법률': '에 대한 법률',
            r'의\s*운영\s*에\s*관한': '의 운영에 관한',
            r'공공기관의\s*운영\s*에\s*관한\s*법률': '공공기관의 운영에 관한 법률',
            r'지방\s*자치\s*법': '지방자치법',
            r'행정\s*절차\s*법': '행정절차법',
            r'국가\s*재정\s*법': '국가재정법',
        }

    def normalize_law_name(self, law_name: str) -> str:
        """법령명 정규화"""
        if not law_name or len(law_name.strip()) < 2:
            return law_name

        normalized = law_name.strip()

        # 정규화 규칙 적용
        for pattern, replacement in self.normalization_rules.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        # 앞뒤 공백 제거
        normalized = normalized.strip()

        return normalized

    def calculate_similarity(self, str1: str, str2: str) -> float:
        """두 문자열 간 유사도 계산 (0.0 ~ 1.0)"""
        if not str1 or not str2:
            return 0.0

        # 정규화된 문자열로 비교
        s1 = self.normalize_law_name(str1).lower()
        s2 = self.normalize_law_name(str2).lower()

        return SequenceMatcher(None, s1, s2).ratio()

    def group_similar_laws(self, law_names: List[str], similarity_threshold: float = 0.85) -> List[List[str]]:
        """유사한 법령명들을 그룹으로 묶기"""
        if not law_names:
            return []

        groups = []
        processed = set()

        for i, law1 in enumerate(law_names):
            if law1 in processed:
                continue

            group = [law1]
            processed.add(law1)

            for j, law2 in enumerate(law_names[i+1:], i+1):
                if law2 in processed:
                    continue

                similarity = self.calculate_similarity(law1, law2)
                if similarity >= similarity_threshold:
                    group.append(law2)
                    processed.add(law2)

            groups.append(group)

        return groups

    def deduplicate_laws(self, law_names: List[str], similarity_threshold: float = 0.85) -> List[str]:
        """법령명 중복 제거 (각 그룹에서 가장 표준적인 이름 선택)"""
        if not law_names:
            return []

        # 유사한 법령명 그룹화
        groups = self.group_similar_laws(law_names, similarity_threshold)

        deduplicated = []

        for group in groups:
            if len(group) == 1:
                deduplicated.append(self.normalize_law_name(group[0]))
            else:
                # 그룹에서 가장 표준적인 이름 선택
                best_name = self.select_best_name(group)
                deduplicated.append(best_name)

        return deduplicated

    def select_best_name(self, law_group: List[str]) -> str:
        """그룹에서 가장 표준적인 법령명 선택"""
        if len(law_group) == 1:
            return self.normalize_law_name(law_group[0])

        # 선택 기준
        scores = {}

        for law_name in law_group:
            normalized = self.normalize_law_name(law_name)
            score = 0

            # 기준 1: 완전한 형태 선호 (짧지 않고 생략되지 않은)
            if len(normalized) >= 5:
                score += 2

            # 기준 2: 정식 명칭 형태 선호 ("법률", "법", "령", "규칙" 포함)
            if any(suffix in normalized for suffix in ['법률', '시행령', '시행규칙']):
                score += 3
            elif normalized.endswith('법'):
                score += 2

            # 기준 3: 공백이 적절히 포함된 형태 선호
            space_count = normalized.count(' ')
            if 1 <= space_count <= 3:
                score += 1

            # 기준 4: 괄호나 특수문자가 적은 형태 선호
            special_char_count = len(re.findall(r'[()（）\[\]【】]', normalized))
            if special_char_count == 0:
                score += 1

            scores[law_name] = score

        # 가장 높은 점수의 법령명 선택
        best_law = max(scores, key=scores.get)
        return self.normalize_law_name(best_law)

    def analyze_duplications(self, law_names: List[str]) -> Dict:
        """중복 현황 분석"""
        if not law_names:
            return {'original_count': 0, 'groups': [], 'deduplicated_count': 0}

        groups = self.group_similar_laws(law_names, 0.85)
        deduplicated = self.deduplicate_laws(law_names, 0.85)

        duplicate_groups = [group for group in groups if len(group) > 1]

        return {
            'original_count': len(law_names),
            'deduplicated_count': len(deduplicated),
            'reduction_count': len(law_names) - len(deduplicated),
            'reduction_rate': ((len(law_names) - len(deduplicated)) / len(law_names) * 100) if law_names else 0,
            'duplicate_groups': duplicate_groups,
            'groups': groups,
            'deduplicated_laws': deduplicated
        }


def demo_deduplication():
    """중복 제거 데모"""
    st.title("🔧 법령명 중복 제거 데모")

    # 테스트용 법령명 목록
    sample_laws = [
        "공공기관의운영에관한법률",
        "공공기관의 운영에 관한법률",
        "공공기관의 운영에 관한 법률",
        "지방자치법",
        "지방 자치법",
        "지방자치 법",
        "행정절차법",
        "행정 절차 법",
        "국가재정법",
        "지방교부세법",
        "헌법"
    ]

    st.subheader("📝 테스트할 법령명 목록")

    # 사용자 입력
    law_input = st.text_area(
        "법령명을 한 줄씩 입력하세요:",
        value="\n".join(sample_laws),
        height=200
    )

    if st.button("🔍 중복 제거 실행"):
        # 입력 처리
        input_laws = [law.strip() for law in law_input.split('\n') if law.strip()]

        if not input_laws:
            st.error("법령명을 입력해주세요.")
            return

        # 중복 제거 실행
        deduplicator = SimpleLawNameDeduplicator()
        analysis = deduplicator.analyze_duplications(input_laws)

        # 결과 표시
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("원본 법령 수", analysis['original_count'])

        with col2:
            st.metric("정리된 법령 수", analysis['deduplicated_count'])

        with col3:
            st.metric("중복 제거율", f"{analysis['reduction_rate']:.1f}%")

        # 중복 그룹 상세 정보
        if analysis['duplicate_groups']:
            st.subheader("🔍 발견된 중복 그룹")

            for i, group in enumerate(analysis['duplicate_groups'], 1):
                best_name = deduplicator.select_best_name(group)

                with st.expander(f"그룹 {i}: {best_name} ({len(group)}개 유사)", expanded=True):
                    st.write("**🎯 선택된 표준명:**")
                    st.success(f"✅ {best_name}")

                    st.write("**📝 원본 법령명들:**")
                    for law in group:
                        similarity = deduplicator.calculate_similarity(law, best_name)
                        st.write(f"- {law} (유사도: {similarity:.2f})")

        # 최종 정리된 법령 목록
        st.subheader("📋 최종 정리된 법령 목록")

        for i, law in enumerate(analysis['deduplicated_laws'], 1):
            st.write(f"{i}. {law}")

        # 절약 효과 표시
        if analysis['reduction_count'] > 0:
            st.success(f"""
            🎯 **중복 제거 효과**
            - {analysis['reduction_count']}개 중복 법령 정리
            - {analysis['reduction_rate']:.1f}% 데이터 절약
            - Gemini API 호출 {analysis['reduction_count']}회 절약 예상
            """)


if __name__ == "__main__":
    demo_deduplication()