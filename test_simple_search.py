#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import xml.etree.ElementTree as ET

# API 설정
OC = "climsneys85"
url = "http://www.law.go.kr/DRF/lawSearch.do"

def test_simple_searches():
    """간단한 검색 테스트"""
    print("=== 판례 검색 테스트 ===")

    # 테스트할 검색 쿼리들
    queries = [
        "조례",
        "조례 기관위임사무",  # 공백으로 연결
        "조례 AND 기관위임사무",  # AND 연산자
        "조례 OR 기관위임사무",   # OR 연산자
    ]

    for query in queries:
        print(f"\n쿼리: {query}")
        print("-" * 30)

        params = {
            'OC': OC,
            'target': 'prec',
            'type': 'XML',
            'query': query,
            'display': 2
        }

        try:
            response = requests.get(url, params=params, timeout=20)

            if response.status_code == 200 and response.text.startswith('<?xml'):
                root = ET.fromstring(response.text)

                # 총 개수 확인
                total_cnt_elem = root.find('totalCnt')
                total_cnt = int(total_cnt_elem.text) if total_cnt_elem is not None else 0

                print(f"결과 개수: {total_cnt}")

                # 실제 판례 개수
                prec_count = len(root.findall('prec'))
                print(f"반환 개수: {prec_count}")

            else:
                print(f"오류: {response.status_code}")

        except Exception as e:
            print(f"오류: {e}")

if __name__ == "__main__":
    test_simple_searches()