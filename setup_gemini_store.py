"""
Gemini File Search Store 초기 설정 스크립트
PDF 파일을 업로드하고 저장소를 준비합니다.
"""

import os
from gemini_file_search import GeminiFileSearchManager


def setup_file_search_store(api_key: str, pdf_files: list):
    """
    Gemini File Search Store를 설정하고 PDF를 업로드합니다.

    Args:
        api_key: Gemini API 키
        pdf_files: 업로드할 PDF 파일 경로 리스트
    """
    print("=" * 80)
    print("Gemini File Search Store 초기 설정")
    print("=" * 80)

    # 1. Store Manager 생성
    print("\n[1단계] Store Manager 생성 중...")
    manager = GeminiFileSearchManager(api_key)

    # 2. 저장소 생성/조회
    print("\n[2단계] 검색 저장소 생성/조회 중...")
    store_name = manager.create_or_get_store(display_name="조례-판례-법령-저장소")
    print(f"   저장소: {store_name}")

    # 3. PDF 파일 업로드
    print("\n[3단계] PDF 파일 업로드 중...")
    print(f"   총 {len(pdf_files)}개 파일 업로드 예정")

    results = []
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n   [{i}/{len(pdf_files)}] {os.path.basename(pdf_path)}")

        if not os.path.exists(pdf_path):
            print(f"   ⚠️  파일을 찾을 수 없습니다: {pdf_path}")
            print(f"   현재 디렉토리의 파일을 확인하세요.")
            continue

        try:
            result = manager.upload_file(pdf_path)
            results.append(result)
            print(f"   ✅ 업로드 완료")
        except Exception as e:
            print(f"   ❌ 업로드 실패: {e}")

    # 4. 결과 요약
    print("\n" + "=" * 80)
    print("업로드 완료 요약")
    print("=" * 80)
    print(f"성공: {len([r for r in results if 'error' not in r])}개")
    print(f"실패: {len([r for r in results if 'error' in r])}개")
    print(f"\n저장소 이름: {store_name}")
    print("\n이제 streamlit_app.py에서 이 저장소를 사용할 수 있습니다.")
    print("=" * 80)

    return manager, results


def test_search(manager: GeminiFileSearchManager):
    """
    간단한 검색 테스트를 수행합니다.

    Args:
        manager: GeminiFileSearchManager 인스턴스
    """
    print("\n" + "=" * 80)
    print("검색 테스트")
    print("=" * 80)

    test_queries = [
        "조례의 위법성 판단 기준은?",
        "재의 요구 사례",
        "지방자치단체의 권한"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n[테스트 {i}] 쿼리: {query}")
        try:
            result = manager.search(query, top_k=3)
            print(f"✅ 답변: {result['answer'][:200]}...")
            print(f"   출처 개수: {len(result['sources'])}개")
        except Exception as e:
            print(f"❌ 검색 실패: {e}")


if __name__ == "__main__":
    # API 키 설정 (환경 변수 또는 직접 입력)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    if not GEMINI_API_KEY:
        print("⚠️  GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("다음 중 하나를 선택하세요:")
        print("1. 환경 변수 설정: set GEMINI_API_KEY=your-api-key")
        print("2. 코드에 직접 입력: GEMINI_API_KEY = 'your-api-key'")
        exit(1)

    # 업로드할 PDF 파일 경로 설정 (실제 경로로 변경 필요)
    PDF_FILES = [
        "2022년_자치법규입안길라잡이.pdf",
        "3. 지방자치단체의 재의·제소 조례 모음집(Ⅸ) (1).pdf",
        "자치법규_Q&A (1).pdf",
        "자치법규_쟁점_사전검토_지원_사례집 (1).pdf",
    ]

    print("\n⚠️  중요: PDF_FILES 리스트에 실제 PDF 파일 경로를 추가하세요!")
    print("현재 설정된 파일:")
    for pdf in PDF_FILES:
        print(f"  - {pdf}")
        print(f"    존재: {'✅' if os.path.exists(pdf) else '❌'}")

    if not PDF_FILES:
        print("\n❌ 업로드할 PDF 파일이 지정되지 않았습니다.")
        print("\n다음 단계:")
        print("1. PDF 파일을 준비합니다.")
        print("2. 이 스크립트의 PDF_FILES 리스트에 파일 경로를 추가합니다.")
        print("3. 스크립트를 다시 실행합니다.")
        exit(1)

    # 설정 실행
    manager, results = setup_file_search_store(GEMINI_API_KEY, PDF_FILES)

    # 검색 테스트 (선택사항)
    if input("\n검색 테스트를 실행하시겠습니까? (y/n): ").lower() == 'y':
        test_search(manager)
