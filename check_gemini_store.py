"""
Gemini File Search Store 상태 확인
업로드된 파일과 검색 기능을 테스트
"""

import os
from gemini_file_search import GeminiFileSearchManager

def check_store_status():
    """Store 상태 확인"""

    # API 키 확인
    api_key = os.getenv('GEMINI_API_KEY', '')
    if not api_key:
        print("[ERROR] GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
        return

    print(f"[OK] API Key: {api_key[:10]}...")

    try:
        # Store Manager 생성
        manager = GeminiFileSearchManager(api_key)
        print(f"[OK] Manager 생성 완료")

        # Store 생성 또는 가져오기
        manager.create_or_get_store()
        print(f"[OK] Store 이름: {manager.store_name}")

        # 간단한 검색 테스트
        test_queries = [
            "조례",
            "지방자치법",
            "기관위임사무",
            "법률유보원칙"
        ]

        print("\n[검색 테스트]")
        print("=" * 80)

        for query in test_queries:
            print(f"\n[쿼리] {query}")
            result = manager.search(query, top_k=3)

            answer = result.get('answer', '')
            sources = result.get('sources', [])

            if answer:
                print(f"[응답 길이] {len(answer)}자")
                print(f"[응답 미리보기] {answer[:200]}...")
            else:
                print("[응답] 없음")

            if sources:
                print(f"[출처 수] {len(sources)}개")
                for i, source in enumerate(sources[:3], 1):
                    title = source.get('title', 'N/A')
                    print(f"  {i}. {title}")
            else:
                print("[출처] 없음")

            print("-" * 80)

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_store_status()
