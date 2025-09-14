"""
XML API 디버깅 모듈
국가법령정보센터 API의 XML 응답을 디버깅합니다.
"""

import requests
import xml.etree.ElementTree as ET
import re

# API 설정
OC = "20241020143052810"  # 예시 OC
search_url = "https://www.law.go.kr/DRF/lawSearch.do"
detail_url = "https://www.law.go.kr/DRF/lawService.do"

def debug_law_search(law_name: str = "도로교통법"):
    """법령 검색 디버깅"""
    print(f"법령 검색 디버깅: {law_name}")
    
    search_params = {
        'OC': OC,
        'target': 'law',
        'type': 'XML',
        'query': law_name,
        'display': 5
    }
    
    try:
        response = requests.get(search_url, params=search_params, timeout=30)
        print(f"HTTP 상태: {response.status_code}")
        print(f"응답 길이: {len(response.text)}")
        
        if response.status_code == 200:
            # XML 파싱
            root = ET.fromstring(response.text)
            
            # 현행 법령 찾기
            current_laws = []
            for law in root.findall('.//law'):
                status = law.find('현행연혁코드')
                if status is not None and status.text == '현행':
                    law_id = law.find('법령ID')
                    law_name_elem = law.find('법령명한글')
                    if law_id is not None and law_name_elem is not None:
                        current_laws.append({
                            'id': law_id.text,
                            'name': law_name_elem.text
                        })
            
            print(f"현행 법령 수: {len(current_laws)}")
            for law in current_laws:
                print(f"  - {law['name']} (ID: {law['id']})")
            
            return current_laws
        else:
            print(f"검색 실패: {response.status_code}")
            
    except Exception as e:
        print(f"오류: {str(e)}")
    
    return []

def debug_law_detail(law_id: str):
    """법령 상세 정보 디버깅"""
    print(f"\n법령 상세 디버깅: {law_id}")
    
    detail_params = {
        'OC': OC,
        'target': 'law',
        'type': 'XML',
        'ID': law_id
    }
    
    try:
        response = requests.get(detail_url, params=detail_params, timeout=30)
        print(f"HTTP 상태: {response.status_code}")
        print(f"응답 길이: {len(response.text)}")
        
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            
            # 조문 수 계산
            jo_count = len(root.findall('.//조문내용'))
            hang_count = len(root.findall('.//항내용'))
            ho_count = len(root.findall('.//호내용'))
            
            print(f"조문내용: {jo_count}개")
            print(f"항내용: {hang_count}개")
            print(f"호내용: {ho_count}개")
            
            # 샘플 조문 출력
            sample_articles = root.findall('.//조문내용')[:3]
            print(f"\n샘플 조문 (처음 3개):")
            for i, article in enumerate(sample_articles):
                if article.text:
                    clean_text = re.sub(r'<[^>]+>', '', article.text)
                    clean_text = clean_text.replace('&nbsp;', ' ').strip()
                    print(f"  [{i+1}] {clean_text[:100]}...")
            
            return True
        else:
            print(f"상세 조회 실패: {response.status_code}")
            
    except Exception as e:
        print(f"오류: {str(e)}")
    
    return False

def full_debug_process(law_name: str = "도로교통법"):
    """전체 디버깅 프로세스"""
    print(f"{'='*60}")
    print(f"법령 디버깅 프로세스: {law_name}")
    print(f"{'='*60}")
    
    # 1단계: 검색
    current_laws = debug_law_search(law_name)
    
    if current_laws:
        # 2단계: 첫 번째 법령 상세 조회
        first_law = current_laws[0]
        print(f"\n선택된 법령: {first_law['name']} (ID: {first_law['id']})")
        debug_law_detail(first_law['id'])
    else:
        print("검색된 현행 법령이 없습니다.")

if __name__ == "__main__":
    # 여러 법령 테스트
    test_laws = ["도로교통법", "건축법", "환경보전법"]
    
    for law_name in test_laws:
        full_debug_process(law_name)
        print("\n" + "="*60 + "\n")