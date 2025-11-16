#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import xml.etree.ElementTree as ET

# API 설정
OC = "climsneys85"
url = "http://www.law.go.kr/DRF/lawSearch.do"

def test_search_queries():
    """검색 쿼리 형식 테스트"""
    print("판례 검색 쿼리 형식 테스트")
    print("=" * 50)

    # 테스트할 검색 쿼리들
    test_queries = [
        "조례",  # 기본
        "조례 AND 기관위임사무",  # AND 조건
        "조례 AND (기관위임사무 OR 자치사무)",  # AND + OR 조건
        "조례 AND (기관위임사무 OR 자치사무 OR 위임사무)",  # 복합 조건
    ]

    for query in test_queries:
        print(f"\n[테스트 쿼리: {query}]")
        print("-" * 40)

        params = {
            'OC': OC,
            'target': 'prec',
            'type': 'XML',
            'query': query,
            'display': 3
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            print(f"상태코드: {response.status_code}")

            if response.status_code == 200:
                content = response.text

                if content.startswith('<?xml'):
                    root = ET.fromstring(content)

                    # totalCnt 확인
                    total_cnt_elem = root.find('totalCnt')
                    total_cnt = int(total_cnt_elem.text) if total_cnt_elem is not None else 0

                    # prec 요소 개수 확인
                    prec_elements = root.findall('prec')
                    prec_count = len(prec_elements)

                    print(f"총 판례 수: {total_cnt}")
                    print(f"반환된 판례 수: {prec_count}")

                    if prec_count > 0:
                        print("✅ 검색 성공!")

                        # 첫 번째 판례의 사건명 확인
                        first_prec = prec_elements[0]
                        case_name_elem = first_prec.find('사건명')
                        if case_name_elem is not None:
                            case_name = case_name_elem.text
                            print(f"첫 번째 판례: {case_name[:100]}...")
                    else:
                        print("❌ 검색 결과 없음")

                else:
                    print("❌ XML이 아닌 응답")
                    print(content[:200])

        except Exception as e:
            print(f"❌ 오류: {e}")

        print("-" * 40)

if __name__ == "__main__":
    test_search_queries()