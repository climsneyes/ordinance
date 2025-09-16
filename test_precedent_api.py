#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
국가법령정보센터 판례 검색 API 테스트 스크립트
"""

import requests
import xml.etree.ElementTree as ET
import json

# API 설정
OC = "climsneyes85"
precedent_search_url = "http://www.law.go.kr/DRF/lawSearch.do"
detail_url = "http://www.law.go.kr/DRF/lawService.do"

def test_precedent_search(query_keywords, max_results=5):
    """판례 검색 테스트"""
    try:
        print(f"\n[검색] 판례 검색 테스트")
        print(f"검색 키워드: {query_keywords}")
        print(f"최대 결과 수: {max_results}")
        print("-" * 50)

        # API 요청 파라미터
        params = {
            'OC': OC,
            'target': 'prec',  # 판례 검색
            'type': 'XML',
            'query': query_keywords,
            'display': min(max_results, 20)
        }

        print(f"API 요청 URL: {precedent_search_url}")
        print(f"요청 파라미터: {params}")

        response = requests.get(precedent_search_url, params=params, timeout=30)
        print(f"HTTP 상태 코드: {response.status_code}")

        if response.status_code != 200:
            print(f"[오류] API 오류: HTTP {response.status_code}")
            return []

        print(f"응답 길이: {len(response.text)} 문자")
        print(f"응답 미리보기 (첫 500자):")
        print(response.text[:500])
        print()

        # XML 파싱
        try:
            root = ET.fromstring(response.text)
            print(f"XML 루트 태그: {root.tag}")

            # 모든 하위 요소 확인
            print("XML 구조:")
            for child in root:
                print(f"  - {child.tag}: {child.text[:50] if child.text else 'None'}...")

        except ET.ParseError as e:
            print(f"❌ XML 파싱 오류: {e}")
            print("응답이 XML이 아닐 수 있습니다.")
            return []

        precedents = []

        # XML 응답에서 판례 정보 추출
        for prec_elem in root.findall('.//PrecSearch'):
            try:
                print(f"\n📄 판례 요소 발견:")
                for child in prec_elem:
                    value = child.text if child.text else ''
                    print(f"  {child.tag}: {value[:100]}...")

                prec_id = prec_elem.find('판례일련번호')
                case_name = prec_elem.find('사건명')
                court = prec_elem.find('법원명')
                date = prec_elem.find('선고일자')
                case_type = prec_elem.find('사건종류명')

                if all(elem is not None for elem in [prec_id, case_name]):
                    precedent = {
                        'id': prec_id.text,
                        'case_name': case_name.text,
                        'court': court.text if court is not None else '',
                        'date': date.text if date is not None else '',
                        'case_type': case_type.text if case_type is not None else '',
                    }
                    precedents.append(precedent)
                    print(f"✅ 판례 추가됨: {precedent['case_name']}")
                else:
                    print(f"❌ 필수 정보 부족 (판례일련번호, 사건명)")

            except Exception as e:
                print(f"❌ 판례 파싱 오류: {e}")
                continue

        print(f"\n📋 검색 결과: {len(precedents)}개 판례")
        for i, p in enumerate(precedents):
            print(f"{i+1}. {p['case_name']} ({p['court']}, {p['date']})")

        return precedents

    except Exception as e:
        print(f"❌ 검색 오류: {str(e)}")
        return []

def test_precedent_detail(precedent_id):
    """판례 상세 조회 테스트"""
    try:
        print(f"\n🔍 판례 상세 조회 테스트")
        print(f"판례 ID: {precedent_id}")
        print("-" * 50)

        params = {
            'OC': OC,
            'target': 'prec',
            'ID': precedent_id,
            'type': 'XML'
        }

        print(f"API 요청 URL: {detail_url}")
        print(f"요청 파라미터: {params}")

        response = requests.get(detail_url, params=params, timeout=30)
        print(f"HTTP 상태 코드: {response.status_code}")

        if response.status_code != 200:
            print(f"❌ API 오류: HTTP {response.status_code}")
            return None

        print(f"응답 길이: {len(response.text)} 문자")
        print(f"응답 미리보기 (첫 500자):")
        print(response.text[:500])
        print()

        # XML 파싱
        try:
            root = ET.fromstring(response.text)
            print(f"XML 루트 태그: {root.tag}")

            # 판례 상세 정보 확인
            content = ""

            # 판시사항
            decision_matters = root.find('.//판시사항')
            if decision_matters is not None and decision_matters.text:
                content += f"[판시사항]\n{decision_matters.text}\n\n"
                print(f"✅ 판시사항: {len(decision_matters.text)} 문자")

            # 판결요지
            decision_summary = root.find('.//판결요지')
            if decision_summary is not None and decision_summary.text:
                content += f"[판결요지]\n{decision_summary.text}\n\n"
                print(f"✅ 판결요지: {len(decision_summary.text)} 문자")

            # 참조조문
            ref_articles = root.find('.//참조조문')
            if ref_articles is not None and ref_articles.text:
                content += f"[참조조문]\n{ref_articles.text}\n\n"
                print(f"✅ 참조조문: {len(ref_articles.text)} 문자")

            # 전문
            full_text = root.find('.//전문')
            if full_text is not None and full_text.text:
                print(f"✅ 전문: {len(full_text.text)} 문자")
                full_content = full_text.text
                if len(full_content) > 2000:
                    full_content = full_content[:2000] + "..."
                content += f"[전문]\n{full_content}\n\n"

            print(f"\n📄 총 추출된 내용: {len(content)} 문자")
            if content:
                print("내용 미리보기:")
                print(content[:300] + "..." if len(content) > 300 else content)

            return content.strip() if content else None

        except ET.ParseError as e:
            print(f"❌ XML 파싱 오류: {e}")
            return None

    except Exception as e:
        print(f"❌ 상세 조회 오류: {str(e)}")
        return None

def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("국가법령정보센터 판례 검색 API 테스트")
    print("=" * 60)

    # 테스트 케이스들
    test_cases = [
        "기관위임사무",
        "포괄위임금지원칙",
        "건축허가",
        "조례 위법",
        "법령위반"
    ]

    for test_query in test_cases:
        precedents = test_precedent_search(test_query, max_results=3)

        if precedents:
            # 첫 번째 판례의 상세 정보 조회
            first_precedent = precedents[0]
            detail_content = test_precedent_detail(first_precedent['id'])

            if detail_content:
                print(f"✅ 상세 조회 성공!")
            else:
                print(f"❌ 상세 조회 실패")
        else:
            print(f"❌ '{test_query}' 검색 결과 없음")

        print("\n" + "="*60)

    print("🎯 테스트 완료!")

if __name__ == "__main__":
    main()