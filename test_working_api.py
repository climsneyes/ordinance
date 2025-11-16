#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import xml.etree.ElementTree as ET

def test_precedent_api():
    print("국가법령정보센터 판례 API 테스트")
    print("=" * 40)

    # API 설정 (가이드에서 제공하는 예시와 동일)
    url = "http://www.law.go.kr/DRF/lawSearch.do"

    # 테스트 파라미터 (가이드의 예시)
    params = {
        'OC': 'climsneys85',  # 사용자 이메일 ID
        'target': 'prec',      # 판례 검색
        'type': 'XML',         # XML 형식
        'query': '담보권',      # 검색 키워드 (가이드 예시)
        'display': 3           # 결과 수
    }

    print(f"API URL: {url}")
    print(f"파라미터: {params}")
    print("-" * 40)

    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"HTTP 상태 코드: {response.status_code}")
        print(f"응답 길이: {len(response.text)} 문자")

        content = response.text
        print(f"응답 시작 부분:")
        print(content[:500])
        print()

        if content.startswith('<?xml'):
            print("정상 XML 응답!")
            try:
                root = ET.fromstring(content)
                print(f"XML 루트 태그: {root.tag}")

                # 판례 검색 결과 찾기
                prec_searches = root.findall('.//PrecSearch')
                print(f"판례 검색 결과 수: {len(prec_searches)}")

                for i, prec in enumerate(prec_searches):
                    print(f"\n--- 판례 {i+1} ---")
                    for child in prec:
                        if child.text and len(child.text.strip()) > 0:
                            print(f"{child.tag}: {child.text.strip()}")

            except ET.ParseError as e:
                print(f"XML 파싱 오류: {e}")

        elif '<!DOCTYPE html' in content or '<html' in content:
            print("HTML 응답 (오류 페이지일 가능성)")
            # 오류 메시지 확인
            if "인증" in content or "auth" in content.lower():
                print("인증 관련 오류로 보임")
        else:
            print("예상치 못한 응답 형식")

    except Exception as e:
        print(f"요청 오류: {e}")

def test_with_different_keywords():
    """다양한 키워드로 테스트"""
    print("\n" + "=" * 40)
    print("다양한 키워드 테스트")
    print("=" * 40)

    keywords = ['조례', '위임', '허가']

    for keyword in keywords:
        print(f"\n[테스트] 키워드: {keyword}")

        params = {
            'OC': 'climsneys85',
            'target': 'prec',
            'type': 'XML',
            'query': keyword,
            'display': 1
        }

        try:
            response = requests.get("http://www.law.go.kr/DRF/lawSearch.do",
                                  params=params, timeout=15)
            print(f"상태: {response.status_code}, 길이: {len(response.text)}")

            if response.text.startswith('<?xml'):
                print("XML 응답 OK")
            else:
                print("비XML 응답")

        except Exception as e:
            print(f"오류: {e}")

if __name__ == "__main__":
    test_precedent_api()
    test_with_different_keywords()