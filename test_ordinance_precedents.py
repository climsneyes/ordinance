#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import xml.etree.ElementTree as ET

# API 설정
OC = "climsneys85"
url = "http://www.law.go.kr/DRF/lawSearch.do"

def test_ordinance_precedents():
    """조례 무효 판례 검색 테스트"""
    print("조례 관련 판례 검색 API 테스트")
    print("=" * 50)

    # 조례 관련 다양한 키워드로 테스트
    test_keywords = [
        "조례 무효",      # 조례 무효 판례
        "조례 위법",      # 조례 위법 판례
        "조례 취소",      # 조례 취소 판례
        "기관위임사무",    # 기관위임사무 관련
        "자치사무",       # 자치사무 관련
        "지방자치법",     # 지방자치법 관련
        "조례안",         # 조례안 관련
        "조례 제정",      # 조례 제정 관련
        "위임조례",       # 위임조례 관련
        "조례 헌법소원",  # 조례 헌법소원
    ]

    for keyword in test_keywords:
        print(f"\n[키워드: {keyword}]")
        print("-" * 30)

        params = {
            'OC': OC,
            'target': 'prec',
            'type': 'XML',
            'query': keyword,
            'display': 5  # 5개씩 테스트
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            print(f"상태코드: {response.status_code}")

            if response.status_code == 200:
                content = response.text

                if content.startswith('<?xml'):
                    root = ET.fromstring(content)

                    # 총 개수 확인
                    total_cnt_elem = root.find('totalCnt')
                    total_cnt = int(total_cnt_elem.text) if total_cnt_elem is not None else 0

                    # 실제 판례 개수
                    prec_elements = root.findall('prec')
                    prec_count = len(prec_elements)

                    print(f"총 판례 수: {total_cnt}")
                    print(f"반환된 판례 수: {prec_count}")

                    if prec_count > 0:
                        print("판례 목록:")
                        for i, prec in enumerate(prec_elements):
                            # 사건명 확인
                            case_name_elem = prec.find('사건명')
                            court_elem = prec.find('법원명')
                            date_elem = prec.find('선고일자')

                            case_name = case_name_elem.text if case_name_elem is not None else "사건명 없음"
                            court = court_elem.text if court_elem is not None else "법원명 없음"
                            date = date_elem.text if date_elem is not None else "선고일 없음"

                            print(f"  {i+1}. {case_name[:80]}...")
                            print(f"     법원: {court}, 선고일: {date}")

                            # 조례 관련인지 확인
                            if any(word in case_name for word in ['조례', '자치', '위임', '지방']):
                                print(f"     OK: 조례 관련 판례 확인!")
                    else:
                        print("ERROR: 검색 결과 없음")

                else:
                    print("ERROR: XML이 아닌 응답")
                    print(content[:300])

        except Exception as e:
            print(f"ERROR: {e}")

        print("-" * 30)

def test_specific_ordinance_cases():
    """구체적인 조례 무효 사례 검색"""
    print("\n\n구체적 조례 무효 사례 검색")
    print("=" * 50)

    # 더 구체적인 조례 관련 키워드
    specific_keywords = [
        "조례 법률위반",
        "조례 상위법령위배",
        "조례 헌법위반",
        "조례 무효확인",
        "조례 효력정지",
        "위임범위초과",
        "포괄위임금지",
        "기관위임사무조례",
    ]

    found_cases = 0

    for keyword in specific_keywords:
        params = {
            'OC': OC,
            'target': 'prec',
            'type': 'XML',
            'query': keyword,
            'display': 3
        }

        try:
            response = requests.get(url, params=params, timeout=20)

            if response.status_code == 200 and response.text.startswith('<?xml'):
                root = ET.fromstring(response.text)
                prec_count = len(root.findall('prec'))

                if prec_count > 0:
                    found_cases += prec_count
                    print(f"OK '{keyword}': {prec_count}개 판례")

                    # 첫 번째 판례 상세 정보
                    first_prec = root.findall('prec')[0]
                    case_name = first_prec.find('사건명')
                    if case_name is not None:
                        print(f"   예시: {case_name.text[:100]}...")
                else:
                    print(f"ERROR '{keyword}': 0개")

        except Exception as e:
            print(f"ERROR '{keyword}' 오류: {e}")

    print(f"\n총 발견된 조례 관련 판례: {found_cases}개")

    if found_cases == 0:
        print("\nWARNING: 문제 분석")
        print("1. API가 조례 관련 판례 데이터를 제대로 제공하지 않을 수 있음")
        print("2. 검색 키워드가 API 데이터베이스와 맞지 않을 수 있음")
        print("3. 판례 데이터가 다른 분류로 저장되어 있을 수 있음")

if __name__ == "__main__":
    test_ordinance_precedents()
    test_specific_ordinance_cases()