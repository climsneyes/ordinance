"""
국가법령정보센터 API를 활용한 법령명 정규화 모듈
"""

import requests
import xml.etree.ElementTree as ET
import re
from typing import List, Dict, Optional
from difflib import SequenceMatcher
import time

class LawNameNormalizer:
    def __init__(self):
        self.base_url = "http://www.law.go.kr/DRF/lawSearch.do"
        self.cache = {}  # 간단한 캐시

    def _clean_law_name(self, law_name: str) -> str:
        """법령명 정리 (특수문자, 공백 정규화)"""
        # 괄호 내용 제거
        cleaned = re.sub(r'\([^)]*\)', '', law_name)
        cleaned = re.sub(r'（[^）]*）', '', cleaned)

        # 여러 공백을 하나로 통일
        cleaned = re.sub(r'\s+', ' ', cleaned)

        # 앞뒤 공백 제거
        cleaned = cleaned.strip()

        return cleaned

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """두 문자열 간 유사도 계산"""
        return SequenceMatcher(None, str1, str2).ratio()

    def search_law_by_name(self, law_name: str, max_results: int = 5) -> List[Dict]:
        """법령명으로 검색하여 정확한 법령명 찾기"""

        # 캐시 확인
        cache_key = f"{law_name}_{max_results}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            # API 파라미터
            params = {
                'OC': 'yonom2024',  # API 키 (실제 사용시 발급받아야 함)
                'target': 'law',    # 검색대상 (law: 법령)
                'type': 'XML',      # 응답형식
                'query': self._clean_law_name(law_name)  # 검색어
            }

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            # XML 파싱
            root = ET.fromstring(response.content)

            results = []

            # 법령 정보 추출
            for law in root.findall('.//law'):
                law_title_elem = law.find('법령명한글')
                law_no_elem = law.find('법령번호')
                law_type_elem = law.find('법종구분')
                enf_date_elem = law.find('시행일자')

                if law_title_elem is not None:
                    law_title = law_title_elem.text
                    law_no = law_no_elem.text if law_no_elem is not None else ""
                    law_type = law_type_elem.text if law_type_elem is not None else ""
                    enf_date = enf_date_elem.text if enf_date_elem is not None else ""

                    # 유사도 계산
                    similarity = self._calculate_similarity(
                        self._clean_law_name(law_name).lower(),
                        self._clean_law_name(law_title).lower()
                    )

                    results.append({
                        'title': law_title,
                        'number': law_no,
                        'type': law_type,
                        'enforcement_date': enf_date,
                        'similarity': similarity,
                        'original_query': law_name
                    })

            # 유사도 순으로 정렬
            results.sort(key=lambda x: x['similarity'], reverse=True)

            # 최대 결과 수로 제한
            results = results[:max_results]

            # 캐시 저장
            self.cache[cache_key] = results

            return results

        except Exception as e:
            print(f"법령 검색 오류: {e}")
            # API 실패시 원본 이름 반환
            return [{
                'title': law_name,
                'number': '',
                'type': '',
                'enforcement_date': '',
                'similarity': 1.0,
                'original_query': law_name,
                'error': str(e)
            }]

    def normalize_law_name(self, law_name: str, min_similarity: float = 0.8) -> str:
        """법령명 정규화 (가장 유사한 정확한 법령명 반환)"""

        # 이미 정리된 법령명인 경우 그대로 반환
        cleaned_name = self._clean_law_name(law_name)
        if not cleaned_name:
            return law_name

        # API로 검색
        results = self.search_law_by_name(cleaned_name, max_results=3)

        if results and results[0]['similarity'] >= min_similarity:
            # 가장 유사한 정확한 법령명 반환
            return results[0]['title']
        else:
            # 유사도가 낮으면 정리된 원본 이름 반환
            return cleaned_name

    def get_best_match_with_info(self, law_name: str) -> Dict:
        """가장 적합한 법령 정보 반환 (상세 정보 포함)"""

        results = self.search_law_by_name(law_name, max_results=1)

        if results:
            return results[0]
        else:
            return {
                'title': law_name,
                'number': '',
                'type': '',
                'enforcement_date': '',
                'similarity': 0.0,
                'original_query': law_name,
                'error': 'No results found'
            }

    def deduplicate_laws(self, law_list: List[str], min_similarity: float = 0.9) -> List[str]:
        """법령명 목록에서 중복 제거 (유사한 법령명들을 하나로 통합)"""

        if not law_list:
            return []

        # 각 법령명을 정규화
        normalized_laws = []
        seen_laws = set()

        for law_name in law_list:
            normalized = self.normalize_law_name(law_name, min_similarity=0.7)

            # 이미 비슷한 법령이 있는지 확인
            is_duplicate = False
            for seen_law in seen_laws:
                if self._calculate_similarity(normalized.lower(), seen_law.lower()) >= min_similarity:
                    is_duplicate = True
                    break

            if not is_duplicate:
                normalized_laws.append(normalized)
                seen_laws.add(normalized)

        return normalized_laws


def test_normalizer():
    """테스트 함수"""
    normalizer = LawNameNormalizer()

    # 테스트 케이스
    test_laws = [
        "지방자치법",
        "지방 자치법",
        "지방자치 법",
        "공공기관의 운영에 관한 법률",
        "공공기관의운영에관한법률",
        "헌법"
    ]

    print("=== 법령명 정규화 테스트 ===")
    for law in test_laws:
        normalized = normalizer.normalize_law_name(law)
        print(f"원본: '{law}' → 정규화: '{normalized}'")

    print("\n=== 중복 제거 테스트 ===")
    deduplicated = normalizer.deduplicate_laws(test_laws)
    print(f"원본 개수: {len(test_laws)}")
    print(f"중복 제거 후: {len(deduplicated)}")
    for law in deduplicated:
        print(f"- {law}")


if __name__ == "__main__":
    test_normalizer()