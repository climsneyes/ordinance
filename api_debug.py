#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests

# API 설정
OC = "climsneyes85"

def test_different_targets():
    print("국가법령정보센터 API 테스트 - 다양한 타겟")
    print("=" * 50)

    base_url = "http://www.law.go.kr/DRF/lawSearch.do"

    # 여러 타겟 테스트
    test_targets = [
        ('law', '법령'),
        ('prec', '판례'),
        ('admrul', '행정규칙'),
        ('jorei', '자치법규')
    ]

    for target, name in test_targets:
        print(f"\n[테스트] {name} 검색 (target={target})")

        params = {
            'OC': OC,
            'target': target,
            'type': 'XML',
            'query': '조례',
            'display': 3
        }

        try:
            response = requests.get(base_url, params=params, timeout=30)
            print(f"상태코드: {response.status_code}")
            print(f"응답 길이: {len(response.text)}")

            # 응답이 XML인지 HTML인지 확인
            content = response.text.strip()
            if content.startswith('<?xml') or content.startswith('<'):
                if '<!DOCTYPE html' in content:
                    print("HTML 오류 페이지 반환됨")
                    # 오류 메시지 추출 시도
                    if 'error' in content.lower():
                        print("오류 관련 내용 발견")
                else:
                    print("XML 응답으로 보임")
                    print("응답 시작 부분:")
                    print(content[:500])
            else:
                print("예상치 못한 응답 형식")
                print("응답 내용:")
                print(content[:300])

        except Exception as e:
            print(f"오류: {e}")

        print("-" * 30)

def test_simple_law_search():
    """기본 법령 검색으로 API 동작 확인"""
    print("\n기본 법령 검색 테스트")
    print("=" * 30)

    params = {
        'OC': OC,
        'target': 'law',
        'type': 'XML',
        'query': '건축법',
        'display': 1
    }

    try:
        response = requests.get("http://www.law.go.kr/DRF/lawSearch.do", params=params, timeout=30)
        print(f"상태코드: {response.status_code}")

        if response.status_code == 200:
            content = response.text
            print(f"응답 길이: {len(content)}")

            if content.startswith('<?xml'):
                print("정상 XML 응답")
                # XML 내용 일부 출력
                lines = content.split('\n')[:10]
                for line in lines:
                    print(line)
            else:
                print("비정상 응답:")
                print(content[:500])
    except Exception as e:
        print(f"오류: {e}")

if __name__ == "__main__":
    test_different_targets()
    test_simple_law_search()