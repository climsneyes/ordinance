#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import xml.etree.ElementTree as ET

# API 설정
OC = "climsneyes85"
search_url = "http://www.law.go.kr/DRF/lawSearch.do"
detail_url = "http://www.law.go.kr/DRF/lawService.do"

def test_api():
    print("국가법령정보센터 판례 검색 API 테스트")
    print("=" * 50)

    # 테스트 키워드
    test_query = "기관위임사무"
    print(f"검색 키워드: {test_query}")

    try:
        # 판례 검색
        params = {
            'OC': OC,
            'target': 'prec',
            'type': 'XML',
            'query': test_query,
            'display': 3
        }

        print(f"API 요청: {search_url}")
        response = requests.get(search_url, params=params, timeout=30)
        print(f"상태코드: {response.status_code}")

        if response.status_code == 200:
            print(f"응답 길이: {len(response.text)} 문자")
            print("응답 내용 (첫 1000자):")
            print(response.text[:1000])

            # XML 파싱 시도
            try:
                root = ET.fromstring(response.text)
                print(f"XML 루트: {root.tag}")

                # 판례 요소 찾기
                precedents = root.findall('.//PrecSearch')
                print(f"판례 개수: {len(precedents)}")

                for i, prec in enumerate(precedents[:2]):
                    print(f"\n--- 판례 {i+1} ---")
                    for child in prec:
                        if child.text:
                            print(f"{child.tag}: {child.text[:100]}")

            except ET.ParseError as e:
                print(f"XML 파싱 오류: {e}")

        else:
            print(f"API 오류: {response.status_code}")
            print("응답 내용:")
            print(response.text[:500])

    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    test_api()