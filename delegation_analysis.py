"""
위임분석 모듈
기관위임사무 관련 분석을 수행합니다.
"""

import re
from typing import List, Dict, Any

def extract_delegation_patterns(text: str) -> List[Dict[str, str]]:
    """위임 관련 패턴 추출"""
    delegation_patterns = [
        r'위임\s*(?:받은|한|하는)',
        r'권한을\s*(?:위임|위탁)',
        r'사무를\s*(?:위임|위탁)',
        r'시장이\s*(?:정한다|정할\s*수\s*있다)',
        r'규칙으로\s*정한다'
    ]
    
    found_patterns = []
    for pattern in delegation_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            found_patterns.append({
                'pattern': pattern,
                'text': match.group(0),
                'position': match.start()
            })
    
    return found_patterns

def analyze_delegation_scope(ordinance_text: str) -> Dict[str, Any]:
    """위임 범위 분석"""
    patterns = extract_delegation_patterns(ordinance_text)
    
    return {
        'delegation_count': len(patterns),
        'patterns': patterns,
        'analysis': f"{len(patterns)}개의 위임 관련 조항이 발견되었습니다."
    }

if __name__ == "__main__":
    sample_text = "제3조(위임) 시장은 이 조례의 시행에 필요한 사항을 규칙으로 정할 수 있다."
    result = analyze_delegation_scope(sample_text)
    print(result)