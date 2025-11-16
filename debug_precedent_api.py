#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import xml.etree.ElementTree as ET

# API 설정
OC = "climsneys85"
url = "http://www.law.go.kr/DRF/lawSearch.do"

def test_precedent_search():
    """판례 검색 API 테스트 및 XML 구조 확인"""
    print("판례 검색 API XML 구조 확인 테스트")
    print("=" * 50)

    # 여러 키워드로 테스트
    test_keywords = ['조례', '지방자치', '위임사무']

    for keyword in test_keywords:
        print(f"\n[테스트 키워드: {keyword}]")
        print("-" * 30)

        params = {
            'OC': OC,
            'target': 'prec',  # 판례 검색
            'type': 'XML',
            'query': keyword,
            'display': 2  # 적은 수로 테스트
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            print(f"상태코드: {response.status_code}")
            print(f"응답 길이: {len(response.text)} 문자")

            if response.status_code == 200:
                content = response.text

                # XML인지 확인
                if content.startswith('<?xml'):
                    print("OK: 정상 XML 응답")

                    # XML 파싱
                    root = ET.fromstring(content)
                    print(f"루트 태그: {root.tag}")

                    # 모든 태그 구조 출력
                    print("\n[XML 구조 분석]")
                    for elem in root.iter():
                        if elem.text and elem.text.strip():
                            print(f"  {elem.tag}: {elem.text.strip()[:100]}")

                    # PrecSearch 요소 찾기
                    prec_searches = root.findall('.//PrecSearch')
                    print(f"\nPrecSearch 요소 수: {len(prec_searches)}")

                    if len(prec_searches) > 0:
                        print("\n[첫 번째 판례 상세 정보]")
                        first_prec = prec_searches[0]
                        for child in first_prec:
                            if child.text and child.text.strip():
                                print(f"  {child.tag}: {child.text.strip()}")

                    if len(prec_searches) == 0:
                        print("ERROR: PrecSearch 요소를 찾을 수 없음!")
                        print("다른 요소들 확인:")
                        for child in root:
                            print(f"  루트 하위 요소: {child.tag}")
                            if len(child) > 0:
                                for subchild in child:
                                    print(f"    - {subchild.tag}")

                else:
                    print("ERROR: XML이 아닌 응답:")
                    print(content[:500])

        except Exception as e:
            print(f"ERROR: {e}")

        print("-" * 30)

if __name__ == "__main__":
    test_precedent_search()