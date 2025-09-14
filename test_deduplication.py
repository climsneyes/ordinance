"""
법령명 중복 제거 기능 테스트
"""

from law_name_deduplicator import SimpleLawNameDeduplicator

def test_law_deduplication():
    """법령명 중복 제거 테스트"""

    # 테스트 데이터 (실제 문제 상황과 동일)
    test_laws = [
        "공공기관의운영에관한법률",
        "공공기관의 운영에 관한법률",
        "공공기관의 운영에 관한 법률",
        "지방자치법",
        "지방 자치법",
        "지방자치 법",
        "행정절차법",
        "행정 절차 법",
        "국가재정법",
        "국가 재정법",
        "헌법"
    ]

    print("=" * 60)
    print("법령명 중복 제거 테스트")
    print("=" * 60)

    # 중복 제거 실행
    deduplicator = SimpleLawNameDeduplicator()
    analysis = deduplicator.analyze_duplications(test_laws)

    print(f"\n[분석 결과]")
    print(f"  - 원본 법령 수: {analysis['original_count']}개")
    print(f"  - 정리된 법령 수: {analysis['deduplicated_count']}개")
    print(f"  - 중복 제거 개수: {analysis['reduction_count']}개")
    print(f"  - 중복 제거율: {analysis['reduction_rate']:.1f}%")

    # 중복 그룹 상세 표시
    if analysis['duplicate_groups']:
        print(f"\n[발견된 중복 그룹] ({len(analysis['duplicate_groups'])}개):")

        for i, group in enumerate(analysis['duplicate_groups'], 1):
            best_name = deduplicator.select_best_name(group)
            print(f"\n  그룹 {i}: {best_name}")

            for law in group:
                similarity = deduplicator.calculate_similarity(law, best_name)
                print(f"    - {law} (유사도: {similarity:.3f})")

    # 최종 정리된 법령 목록
    print(f"\n[최종 정리된 법령 목록]")
    for i, law in enumerate(analysis['deduplicated_laws'], 1):
        print(f"  {i}. {law}")

    # 예상 효과
    print(f"\n[예상 효과]")
    print(f"  - Gemini API 호출 {analysis['reduction_count']}회 절약")
    print(f"  - 분석 정확도 개선 (중복으로 인한 혼란 제거)")
    print(f"  - 데이터 처리 효율성 {analysis['reduction_rate']:.1f}% 향상")

def test_similarity_calculation():
    """유사도 계산 테스트"""

    print("\n" + "=" * 60)
    print("유사도 계산 테스트")
    print("=" * 60)

    deduplicator = SimpleLawNameDeduplicator()

    test_pairs = [
        ("공공기관의운영에관한법률", "공공기관의 운영에 관한 법률"),
        ("지방자치법", "지방 자치법"),
        ("행정절차법", "행정 절차 법"),
        ("국가재정법", "헌법"),  # 다른 법령
        ("지방자치법", "공공기관의 운영에 관한 법률"),  # 완전히 다른 법령
    ]

    for law1, law2 in test_pairs:
        similarity = deduplicator.calculate_similarity(law1, law2)
        status = "[유사]" if similarity >= 0.85 else "[다름]"
        print(f"{status} '{law1}' ↔ '{law2}' (유사도: {similarity:.3f})")

def test_normalization():
    """법령명 정규화 테스트"""

    print("\n" + "=" * 60)
    print("법령명 정규화 테스트")
    print("=" * 60)

    deduplicator = SimpleLawNameDeduplicator()

    test_names = [
        "공공기관의운영에관한법률",
        "공공기관의    운영에    관한    법률",
        "지방   자치법",
        "행정절차   법",
        "국가  재정법",
    ]

    for name in test_names:
        normalized = deduplicator.normalize_law_name(name)
        print(f"원본: '{name}'")
        print(f"정규화: '{normalized}'")
        print()

if __name__ == "__main__":
    test_law_deduplication()
    test_similarity_calculation()
    test_normalization()