"""
종합 위법성 분석 모듈
조례안과 PKL 데이터베이스의 위법 판례를 매칭하여 종합적인 위법성 분석을 수행합니다.
법령명 정규화를 통해 중복을 제거하고 Gemini API 호출을 최적화합니다.
"""

import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
import re
import os
from typing import List, Dict, Any, Tuple
import streamlit as st
from law_name_normalizer import LawNameNormalizer

def load_vectorstore_safe(pkl_path: str) -> Dict[str, Any]:
    """안전한 벡터스토어 로드"""
    try:
        if not os.path.exists(pkl_path):
            return None
        
        with open(pkl_path, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        st.error(f"벡터스토어 로드 실패 ({pkl_path}): {str(e)}")
        return None

def extract_ordinance_articles(pdf_text: str) -> List[Dict[str, str]]:
    """조례안에서 조문 추출"""
    articles = []
    
    # 조문 패턴: "제N조", "제N조의N" 등
    article_pattern = r'제\s*(\d+(?:의\d+)?)\s*조(?:\s*[(（][^)）]*[)）])?\s*([^\n]*?)(?=제\s*\d+(?:의\d+)?\s*조|$)'
    
    matches = re.finditer(article_pattern, pdf_text, re.DOTALL | re.MULTILINE)
    
    for match in matches:
        article_num = match.group(1)
        article_title = match.group(2).strip() if match.group(2) else ""
        
        # 조문 내용 추출 (다음 조문까지)
        start_pos = match.start()
        end_pos = match.end()
        
        # 조문 내용을 더 자세히 추출
        content_match = re.search(
            rf'제\s*{re.escape(article_num)}\s*조.*?(?=제\s*\d+(?:의\d+)?\s*조|$)',
            pdf_text[start_pos:start_pos+2000],
            re.DOTALL
        )
        
        if content_match:
            content = content_match.group(0).strip()
        else:
            content = pdf_text[start_pos:min(start_pos+500, len(pdf_text))].strip()
        
        if content and len(content) > 10:  # 너무 짧은 내용 제외
            articles.append({
                'article_number': article_num,
                'article_title': article_title,
                'content': content,
                'start_position': start_pos
            })
    
    return articles

def extract_law_names_from_text(text: str) -> List[str]:
    """텍스트에서 법령명 추출"""
    law_names = []

    # 법령명 패턴들
    patterns = [
        r'([^.\n]*?법)[.\s]',  # ~법
        r'([^.\n]*?령)[.\s]',  # ~령 (시행령, 대통령령 등)
        r'([^.\n]*?규칙)[.\s]',  # ~규칙
        r'([^.\n]*?조례)[.\s]',  # ~조례
        r'([^.\n]*?규정)[.\s]',  # ~규정
        r'헌법\s*제\s*\d+조',  # 헌법 조문
        r'(지방자치법)',  # 특정 중요 법령
        r'(지방교부세법)',
        r'(국가재정법)',
        r'(공공기관의\s*운영에\s*관한\s*법률)',
        r'(행정절차법)',
        r'(행정기본법)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]

            # 정리
            clean_name = re.sub(r'\s+', ' ', match).strip()
            if len(clean_name) >= 3 and clean_name not in law_names:
                law_names.append(clean_name)

    return law_names

def normalize_and_deduplicate_laws(law_names: List[str]) -> List[str]:
    """법령명 정규화 및 중복 제거"""
    if not law_names:
        return []

    normalizer = LawNameNormalizer()

    try:
        # 법령명 정규화 및 중복 제거
        normalized_laws = normalizer.deduplicate_laws(law_names, min_similarity=0.85)

        st.write(f"[DEBUG] 법령명 정규화: {len(law_names)}개 → {len(normalized_laws)}개")

        # 정규화 결과 표시
        if len(law_names) != len(normalized_laws):
            st.write(f"[INFO] 중복 제거된 법령:")
            for i, (original, normalized) in enumerate(zip(law_names, normalized_laws)):
                if original != normalized:
                    st.write(f"  - '{original}' → '{normalized}'")

        return normalized_laws

    except Exception as e:
        st.error(f"법령명 정규화 오류: {e}")
        # 오류시 간단한 중복 제거만 수행
        return list(set(law_names))

def calculate_text_similarity(text1: str, text2: str, model) -> float:
    """두 텍스트 간 유사도 계산"""
    try:
        embeddings = model.encode([text1, text2])
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        return float(similarity)
    except Exception as e:
        st.error(f"유사도 계산 오류: {str(e)}")
        return 0.0

def analyze_violation_risk(ordinance_content: str, case_content: str, case_info: Dict) -> Dict[str, Any]:
    """개별 위법 위험 분석"""
    
    # 키워드 매칭을 통한 관련성 점수
    violation_keywords = {
        '기관위임사무': ['위임', '사무', '권한', '처리', '업무'],
        '상위법령 위배': ['법률', '시행령', '시행규칙', '위배', '충돌', '모순'],
        '법률유보 위배': ['기본권', '제한', '의무', '부과', '권리', '자유'],
        '권한배분 위배': ['국가사무', '지방사무', '자치사무', '배분', '구분']
    }
    
    relevance_score = 0.0
    violation_type = "일반 위법"
    
    ordinance_lower = ordinance_content.lower()
    case_lower = case_content.lower()
    
    # 위법 유형별 관련성 계산
    type_scores = {}
    for v_type, keywords in violation_keywords.items():
        score = 0
        for keyword in keywords:
            if keyword in ordinance_lower and keyword in case_lower:
                score += 1
        type_scores[v_type] = score
    
    # 가장 높은 점수의 위법 유형 선택
    if type_scores:
        violation_type = max(type_scores, key=type_scores.get)
        relevance_score = type_scores[violation_type] / len(violation_keywords[violation_type])
    
    # 위험도 계산 (0.0 ~ 1.0)
    risk_score = min(relevance_score * 0.8 + 0.2, 1.0)  # 기본 0.2 + 관련성 점수
    
    return {
        'violation_type': violation_type,
        'risk_score': risk_score,
        'relevance_score': relevance_score,
        'case_summary': case_content[:200] + "..." if len(case_content) > 200 else case_content,
        'legal_principle': case_info.get('legal_principle', '해당없음'),
        'recommendation': f"{violation_type} 위험이 있으므로 관련 법령 검토 필요",
        'case_source': case_info.get('source', '판례집')
    }

def search_comprehensive_violation_cases(ordinance_articles: List[Dict], pkl_paths: List[str], max_results: int = 5) -> List[Dict]:
    """종합 위법성 판례 검색"""
    if not ordinance_articles:
        return []
    
    try:
        # 모델 로드
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        st.write(f"[DEBUG] 종합 위법성 분석 모델 로드 완료")
        
        comprehensive_results = []
        all_violation_risks = []  # 모든 조례의 위험 사례를 수집
        
        # 1단계: 모든 조례에 대해 관련 사례 검색
        st.write(f"[DEBUG] 총 {len(ordinance_articles)}개 조례에 대해 위법 사례 검색 중...")
        
        for article in ordinance_articles:
            article_results = {
                'ordinance_article': f"제{article['article_number']}조",
                'ordinance_title': article['article_title'],
                'ordinance_content': article['content'],
                'violation_risks': []
            }
            
            # 각 PKL 파일에서 검색
            for pkl_path in pkl_paths:
                if not os.path.exists(pkl_path):
                    continue
                
                vectorstore = load_vectorstore_safe(pkl_path)
                if not vectorstore:
                    continue
                
                try:
                    # 조문에서 핵심 키워드 추출
                    content_keywords = []
                    
                    # 사무 관련 키워드 추출
                    if any(word in article['content'] for word in ['허가', '승인', '신고', '인허가', '지정']):
                        content_keywords.extend(['기관위임사무', '허가사무', '인허가'])
                    
                    # 권한 관련 키워드 추출  
                    if any(word in article['content'] for word in ['권한', '지시', '명령', '처분']):
                        content_keywords.extend(['권한위임', '처분권한'])
                    
                    # 법령 관련 키워드 추출
                    if any(word in article['content'] for word in ['법률', '시행령', '시행규칙']):
                        content_keywords.extend(['상위법령위반', '법령충돌'])
                    
                    # 조문 제목에서 핵심 분야 추출
                    title_field = ""
                    if any(word in article['article_title'] for word in ['건축', '건설', '개발']):
                        title_field = "건축"
                        content_keywords.extend(['건축허가', '개발행위허가'])
                    elif any(word in article['article_title'] for word in ['환경', '대기', '수질']):
                        title_field = "환경"
                        content_keywords.extend(['환경영향평가', '환경허가'])
                    elif any(word in article['article_title'] for word in ['도시', '계획', '용도']):
                        title_field = "도시계획"
                        content_keywords.extend(['도시계획', '용도지역'])
                    
                    # 개선된 검색 쿼리 생성
                    search_queries = [
                        f"{title_field} 기관위임사무 조례 위법" if title_field else "기관위임사무 조례 위법",
                        f"{article['article_title']} 위법 판례",
                        "조례 제정권한 한계 위반",
                        "상위법령 위반 조례",
                    ]
                    
                    # 키워드가 있으면 추가 쿼리 생성
                    if content_keywords:
                        for keyword in content_keywords[:3]:  # 상위 3개만
                            search_queries.append(f"{keyword} 조례 위법")
                    
                    all_similarities = []
                    embeddings = vectorstore.get('embeddings', np.array([]))
                    
                    if len(embeddings) == 0:
                        continue
                    
                    # 다중 쿼리로 검색하여 결과 통합
                    for query in search_queries:
                        query_embedding = model.encode([query])
                        similarities = np.dot(query_embedding, embeddings.T).flatten()
                        all_similarities.extend([(i, sim) for i, sim in enumerate(similarities)])
                    
                    # 중복 제거하고 최고 점수로 정렬
                    idx_scores = {}
                    for idx, score in all_similarities:
                        if idx not in idx_scores or score > idx_scores[idx]:
                            idx_scores[idx] = score
                    
                    # 상위 결과 선택
                    top_items = sorted(idx_scores.items(), key=lambda x: x[1], reverse=True)[:max_results]
                    
                    # PKL 파일 구조에 맞춰 documents 사용
                    chunks = vectorstore.get('chunks', [])
                    if len(chunks) == 0:
                        # chunks가 없으면 documents 사용
                        documents = vectorstore.get('documents', [])
                        if documents:
                            # documents를 chunks 형태로 변환
                            chunks = [{'text': doc} for doc in documents]
                    
                    st.write(f"[DEBUG] {article['article_title']} - 검색된 결과 수: {len(top_items)}, 최고 유사도: {top_items[0][1] if top_items else 0}, chunks: {len(chunks)}개")
                    
                    for idx, similarity in top_items:
                        if similarity > 0.15:  # 임계값 다시 높임 (관련성 중시)
                            chunk = chunks[idx]
                            chunk_text = chunk.get('text', '')
                            
                            # 관련성 검증 - 핵심 키워드가 포함되어 있는지 확인
                            relevance_keywords = ['조례', '위법', '기관위임', '상위법령', '권한', '사무']
                            relevance_score = sum(1 for keyword in relevance_keywords if keyword in chunk_text)
                            
                            # 조례와 관련된 내용인지 추가 확인
                            ordinance_indicators = ['조례안', '조례 제정', '지방자치단체', '자치사무', '위임사무']
                            has_ordinance_context = any(indicator in chunk_text for indicator in ordinance_indicators)
                            
                            # 관련성이 낮으면 제외
                            if relevance_score < 2 and not has_ordinance_context:
                                st.write(f"[DEBUG] 관련성 부족으로 제외: {chunk_text[:100]}...")
                                continue
                            
                            # 위법 위험 분석
                            risk_analysis = analyze_violation_risk(
                                article['content'],
                                chunk['text'],
                                {
                                    'source': chunk.get('source', ''),
                                    'legal_principle': '법령 위반 금지 원칙'
                                }
                            )
                            
                            # 유사도 반영
                            risk_analysis['similarity'] = float(similarity)
                            risk_analysis['risk_score'] = min(
                                risk_analysis['risk_score'] * (1 + similarity), 
                                1.0
                            )
                            
                            # 조례 정보 추가해서 전체 컬렉션에 저장
                            risk_analysis['article_number'] = article['article_number']
                            risk_analysis['article_title'] = article['article_title']
                            article_results['violation_risks'].append(risk_analysis)
                            all_violation_risks.append(risk_analysis)  # 전체 컬렉션에도 추가
                
                except Exception as e:
                    st.error(f"PKL 검색 오류 ({pkl_path}): {str(e)}")
                    continue
            
            # 위험도 순으로 정렬하고 상위 결과만 유지
            article_results['violation_risks'].sort(key=lambda x: x['risk_score'], reverse=True)
            article_results['violation_risks'] = article_results['violation_risks'][:max_results]
            
            if article_results['violation_risks']:  # 위험이 발견된 경우만 추가
                comprehensive_results.append(article_results)
        
        # 2단계: 전체 위험 사례 관련성 필터링 및 최적화
        st.write(f"[DEBUG] 1단계 완료: {len(all_violation_risks)}개 위험 사례 수집")
        
        if all_violation_risks:
            # 관련성 기준으로 전체 사례 정렬
            all_violation_risks.sort(key=lambda x: (x['risk_score'], x['similarity']), reverse=True)
            
            # 텍스트 길이 계산 및 필터링
            total_text_length = 0
            filtered_risks = []
            max_text_limit = 50000  # 약 50K 문자 제한
            
            for risk in all_violation_risks:
                case_text_length = len(risk.get('case_summary', '')) + len(risk.get('violation_type', ''))
                
                if total_text_length + case_text_length <= max_text_limit:
                    filtered_risks.append(risk)
                    total_text_length += case_text_length
                else:
                    # 관련성이 매우 높은 경우(위험도 0.7 이상)만 예외적으로 포함
                    if risk['risk_score'] >= 0.7 and len(filtered_risks) < max_results * 2:
                        filtered_risks.append(risk)
                        total_text_length += case_text_length
            
            st.write(f"[DEBUG] 2단계 완료: {len(filtered_risks)}개 사례로 필터링 (총 {total_text_length:,}자)")
            
            # 조례별로 재분배
            for result in comprehensive_results:
                article_num = int(result['ordinance_article'].replace('제', '').replace('조', ''))
                result['violation_risks'] = [
                    risk for risk in filtered_risks 
                    if risk.get('article_number') == article_num
                ][:max_results]  # 조례당 최대 결과 수 제한
        
        st.write(f"[DEBUG] 종합 위법성 분석 완료: {len(comprehensive_results)}개 조문에서 위험 발견")
        return comprehensive_results

    except Exception as e:
        st.error(f"종합 위법성 분석 오류: {str(e)}")
        return []

def extract_and_normalize_relevant_laws(comprehensive_results: List[Dict]) -> Dict[str, List[str]]:
    """분석 결과에서 관련 법령명을 추출하고 정규화"""
    if not comprehensive_results:
        return {'normalized_laws': [], 'law_details': []}

    st.write("### 📋 관련 법령명 추출 및 정규화")

    all_law_names = []
    law_sources = {}  # 법령이 어느 조문에서 나왔는지 추적

    try:
        # 1. 모든 위법 사례에서 법령명 추출
        for result in comprehensive_results:
            article_num = result.get('ordinance_article', '')

            # 조례 내용에서 법령명 추출
            ordinance_content = result.get('ordinance_content', '')
            if ordinance_content:
                extracted_laws = extract_law_names_from_text(ordinance_content)
                for law in extracted_laws:
                    all_law_names.append(law)
                    if law not in law_sources:
                        law_sources[law] = []
                    law_sources[law].append(f"{article_num} (조례)")

            # 위험 사례 내용에서 법령명 추출
            for violation_risk in result.get('violation_risks', []):
                case_summary = violation_risk.get('case_summary', '')
                if case_summary:
                    extracted_laws = extract_law_names_from_text(case_summary)
                    for law in extracted_laws:
                        all_law_names.append(law)
                        if law not in law_sources:
                            law_sources[law] = []
                        law_sources[law].append(f"{article_num} (사례)")

        st.write(f"[DEBUG] 총 {len(all_law_names)}개 법령명 추출됨")

        # 2. 법령명 정규화 및 중복 제거
        if all_law_names:
            normalized_laws = normalize_and_deduplicate_laws(all_law_names)

            # 3. 정규화된 법령 정보와 출처 매핑
            law_details = []
            normalizer = LawNameNormalizer()

            for law in normalized_laws:
                # 정규화된 법령의 상세 정보 조회
                law_info = normalizer.get_best_match_with_info(law)

                # 출처 정보 추가
                related_sources = []
                for original_law, sources in law_sources.items():
                    # 원본 법령과 정규화된 법령이 유사한지 확인
                    if normalizer._calculate_similarity(
                        original_law.lower(),
                        law.lower()
                    ) >= 0.8:
                        related_sources.extend(sources)

                law_details.append({
                    'law_name': law_info['title'],
                    'law_number': law_info.get('number', ''),
                    'law_type': law_info.get('type', ''),
                    'enforcement_date': law_info.get('enforcement_date', ''),
                    'similarity_score': law_info.get('similarity', 0.0),
                    'related_articles': list(set(related_sources)),  # 중복 제거
                    'api_error': law_info.get('error', None)
                })

            # 결과 요약 표시
            st.write(f"**✅ 정규화 완료**: {len(normalized_laws)}개 법령")

            # 중복 제거 효과 표시
            if len(all_law_names) > len(normalized_laws):
                st.success(f"🎯 중복 제거 효과: {len(all_law_names)}개 → {len(normalized_laws)}개 ({((len(all_law_names) - len(normalized_laws)) / len(all_law_names) * 100):.1f}% 감소)")

            # 상위 관련 법령 표시
            with st.expander("🔍 추출된 주요 법령 미리보기", expanded=False):
                for i, detail in enumerate(law_details[:10], 1):  # 상위 10개만
                    st.write(f"{i}. **{detail['law_name']}**")
                    if detail['law_number']:
                        st.write(f"   - 법령번호: {detail['law_number']}")
                    if detail['related_articles']:
                        st.write(f"   - 관련 조문: {', '.join(detail['related_articles'][:3])}")  # 최대 3개만
                    if detail['api_error']:
                        st.write(f"   ⚠️ API 오류: {detail['api_error']}")

            return {
                'normalized_laws': normalized_laws,
                'law_details': law_details,
                'original_count': len(all_law_names),
                'normalized_count': len(normalized_laws),
                'reduction_rate': ((len(all_law_names) - len(normalized_laws)) / len(all_law_names) * 100) if all_law_names else 0
            }

        else:
            st.warning("추출된 법령명이 없습니다.")
            return {'normalized_laws': [], 'law_details': [], 'original_count': 0, 'normalized_count': 0, 'reduction_rate': 0}

    except Exception as e:
        st.error(f"법령명 추출/정규화 오류: {e}")
        return {'normalized_laws': [], 'law_details': [], 'error': str(e)}

def search_theoretical_background(problem_keywords: List[str], pkl_paths: List[str], max_results: int = 8, context_analysis: Dict = None) -> List[Dict]:
    """발견된 문제점에 대한 이론적 배경을 PKL에서 검색"""
    if not problem_keywords:
        return []
    
    try:
        # 여러 모델을 시도해보기
        models_to_try = [
            'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
            'sentence-transformers/all-MiniLM-L6-v2', 
            'sentence-transformers/all-mpnet-base-v2'
        ]
        
        model = None
        for model_name in models_to_try:
            try:
                model = SentenceTransformer(model_name)
                st.write(f"[DEBUG] 이론적 배경 검색 모델 로드 완료: {model_name}")
                break
            except Exception as e:
                st.write(f"[DEBUG] 모델 {model_name} 로드 실패: {str(e)}")
                continue
        
        if model is None:
            st.error("모든 임베딩 모델 로드에 실패했습니다.")
            return []
        
        theoretical_results = []

        # 🔍 문맥 기반 동적 쿼리 생성
        all_search_queries = []

        if context_analysis:
            st.write(f"[DEBUG] 문맥 분석 결과 활용: {len(context_analysis.get('key_concepts', []))}개 개념")

            # 1. 추출된 핵심 개념 기반 쿼리
            for concept_info in context_analysis.get('key_concepts', []):
                concept = concept_info['concept']
                context = concept_info['context']

                # 문맥에서 추가 키워드 추출
                context_keywords = []
                if '허가' in context: context_keywords.append('허가권한')
                if '승인' in context: context_keywords.append('승인권한')
                if '처분' in context: context_keywords.append('행정처분')
                if '위임' in context: context_keywords.append('권한위임')

                # 개념별 특화 쿼리 생성
                all_search_queries.extend([
                    concept,
                    f"{concept} 조례 위법",
                    f"{concept} 판례",
                    f"{concept} 한계"
                ])
                all_search_queries.extend(context_keywords)

            # 2. 법적 근거 기반 쿼리
            for legal_basis in context_analysis.get('legal_basis', []):
                all_search_queries.extend([
                    legal_basis,
                    f"{legal_basis} 위반",
                    f"{legal_basis} 조례"
                ])

            # 3. 문제점 상세 내용 기반 쿼리 (핵심 단어 추출)
            for problem in context_analysis.get('problem_details', []):
                # 문제점에서 핵심 명사 추출
                problem_keywords_extracted = []
                import re
                # 한글 명사 패턴 추출 (매우 단순한 방식)
                nouns = re.findall(r'[가-힣]{2,}(?:사무|권한|법령|조례|위반|위법|허가|승인|처분)', problem)
                problem_keywords_extracted.extend(nouns[:3])  # 상위 3개만

                all_search_queries.extend([f"{noun} 판례" for noun in problem_keywords_extracted])

        # 기본 키워드 기반 쿼리도 포함
        for keyword in problem_keywords:
            # 키워드별 특화된 검색 쿼리 생성
            if keyword == "기관위임사무":
                all_search_queries.extend([
                    "기관위임사무", "조례 제정 금지", "지방자치법 제22조",
                    "국가사무 위임", "시장 군수 구청장", "위임사무 조례", "기관위임 금지"
                ])
            elif keyword == "상위법령":
                all_search_queries.extend([
                    "상위법령", "법령우위", "조례 무효", "법령 충돌", "상위법 위반", "조례 위법"
                ])
            elif keyword == "권한":
                all_search_queries.extend([
                    "권한 위임", "권한배분", "법률유보", "조례 권한", "지방자치단체 권한"
                ])
            elif keyword == "위법":
                all_search_queries.extend([
                    "조례 위법", "무효 조례", "법령 위반", "조례 위반"
                ])
            elif keyword == "헌법위반":
                all_search_queries.extend([
                    "헌법위반", "기본권침해", "헌법재판소", "위헌조례", "헌법적 한계"
                ])
            elif keyword == "기본권":
                all_search_queries.extend([
                    "기본권침해", "재산권", "영업의자유", "평등권", "기본권 제한"
                ])
            elif keyword in ["평등원칙", "비례원칙"]:
                all_search_queries.extend([
                    f"{keyword}", f"{keyword} 위반", "헌법원칙", "조례 한계"
                ])
            elif keyword in ["조세", "벌금", "과태료"]:
                all_search_queries.extend([
                    "조세법률주의", "벌금 부과", "과태료", "법률유보", "조례 벌칙"
                ])
            else:
                all_search_queries.extend([keyword, f"{keyword} 조례", f"{keyword} 위법", f"{keyword} 판례"])

        # 중복 제거 및 우선순위 정렬
        unique_queries = list(dict.fromkeys(all_search_queries))  # 순서 유지하며 중복 제거
        st.write(f"[DEBUG] 생성된 검색 쿼리: {len(unique_queries)}개")
        st.write(f"[DEBUG] 상위 5개 쿼리: {unique_queries[:5]}")

        # PKL 파일별 검색 (동적 쿼리 사용)
        for pkl_path in pkl_paths:
                if not os.path.exists(pkl_path):
                    continue
                
                vectorstore = load_vectorstore_safe(pkl_path)
                if not vectorstore:
                    continue
                
                try:
                    # PKL 파일 구조 상세 확인
                    st.write(f"[DEBUG] {pkl_path} 구조 확인:")
                    st.write(f"[DEBUG]   - keys: {list(vectorstore.keys())}")
                    
                    embeddings = vectorstore.get('embeddings', np.array([]))
                    # PKL 파일 구조에 맞춰 documents 사용
                    chunks = vectorstore.get('chunks', [])
                    if len(chunks) == 0:
                        # chunks가 없으면 documents 사용
                        documents = vectorstore.get('documents', [])
                        if documents:
                            # documents를 chunks 형태로 변환
                            chunks = [{'text': doc} for doc in documents]
                            st.write(f"[DEBUG] documents를 chunks로 변환: {len(chunks)}개")
                    
                    st.write(f"[DEBUG]   - embeddings type: {type(embeddings)}, shape: {embeddings.shape if hasattr(embeddings, 'shape') else 'N/A'}")
                    st.write(f"[DEBUG]   - chunks type: {type(chunks)}, length: {len(chunks)}")
                    
                    if len(embeddings) == 0 or len(chunks) == 0:
                        st.write(f"[DEBUG] {pkl_path} - embeddings: {len(embeddings)}, chunks: {len(chunks)} (건너뜀)")
                        continue
                    
                    # 첫 번째 chunk 내용 확인
                    if len(chunks) > 0:
                        first_chunk = chunks[0]
                        st.write(f"[DEBUG]   - 첫 번째 chunk 구조: {type(first_chunk)}")
                        if isinstance(first_chunk, dict):
                            st.write(f"[DEBUG]   - chunk keys: {list(first_chunk.keys())}")
                            text_content = first_chunk.get('text', first_chunk.get('content', ''))[:100]
                            st.write(f"[DEBUG]   - 첫 100자: {text_content}")
                        else:
                            st.write(f"[DEBUG]   - chunk 내용: {str(first_chunk)[:100]}")
                    
                    # embeddings와 chunks 길이 일치 확인
                    if len(embeddings) != len(chunks):
                        st.write(f"[DEBUG] {pkl_path} - embeddings({len(embeddings)})와 chunks({len(chunks)}) 길이 불일치")
                        min_length = min(len(embeddings), len(chunks))
                        embeddings = embeddings[:min_length]
                        chunks = chunks[:min_length]
                        st.write(f"[DEBUG] {pkl_path} - {min_length}개로 조정")
                    
                    all_similarities = []
                    keyword_matches = []  # 키워드 매칭 결과도 저장
                    
                    # 1차: 임베딩 기반 검색 (동적 쿼리 사용)
                    for query in unique_queries[:15]:  # 상위 15개 쿼리만 사용 (성능 고려)
                        try:
                            query_embedding = model.encode([query])
                            similarities = np.dot(query_embedding, embeddings.T).flatten()
                            all_similarities.extend([(i, sim) for i, sim in enumerate(similarities)])
                        except Exception as e:
                            st.write(f"[DEBUG] 임베딩 검색 실패 ({query}): {str(e)}")

                    # 2차: 단순 키워드 매칭 (백업) - 동적 쿼리 사용
                    for i, chunk in enumerate(chunks):
                        chunk_text = ""
                        if isinstance(chunk, dict):
                            chunk_text = chunk.get('text', chunk.get('content', ''))
                        else:
                            chunk_text = str(chunk)

                        # 키워드 매칭 점수 계산 (핵심 쿼리들로만)
                        keyword_score = 0
                        matched_queries = []
                        for query in unique_queries[:10]:  # 상위 10개만
                            if query.lower() in chunk_text.lower():
                                keyword_score += 1
                                matched_queries.append(query)

                        if keyword_score > 0:
                            # 키워드 매칭 점수를 유사도처럼 사용 (0.5 + 매칭수 * 0.1)
                            match_similarity = 0.5 + keyword_score * 0.1
                            keyword_matches.append((i, match_similarity))
                            st.write(f"[DEBUG] 키워드 매칭 발견: {matched_queries} - {keyword_score}개 매칭, 점수 {match_similarity:.3f}")
                    
                    # 임베딩 결과와 키워드 매칭 결과 결합
                    all_similarities.extend(keyword_matches)
                    
                    # 중복 제거하고 최고 점수로 정렬
                    idx_scores = {}
                    for idx, score in all_similarities:
                        if idx not in idx_scores or score > idx_scores[idx]:
                            idx_scores[idx] = score
                    
                    # 상위 결과 선택
                    top_items = sorted(idx_scores.items(), key=lambda x: x[1], reverse=True)[:3]
                    
                    st.write(f"[DEBUG] {pkl_path} - 검색 결과: {len(top_items)}개, chunks 길이: {len(chunks)}")
                    
                    for idx, similarity in top_items:
                        # 인덱스 범위 안전 검사
                        if idx >= len(chunks):
                            st.write(f"[DEBUG] 인덱스 {idx}가 chunks 길이 {len(chunks)}를 초과합니다.")
                            continue
                        
                        if similarity > 0.1:  # 임계값을 낮춰서 더 많은 결과 포함
                            chunk = chunks[idx]
                            chunk_text = chunk.get('text', '')
                            
                            # 🔍 문맥 기반 관련성 평가 (동적)
                            relevance_score = 0
                            matched_concepts = []

                            # 1. 기본 법적 지표
                            theory_indicators = ['원칙', '판례', '헌법재판소', '대법원', '이론', '학설', '법리', '조례', '위법', '무효', '법령', '위반']
                            base_score = sum(1 for indicator in theory_indicators if indicator in chunk_text)
                            relevance_score += base_score

                            # 2. Gemini 분석에서 추출된 핵심 개념과의 매칭
                            if context_analysis:
                                for concept_info in context_analysis.get('key_concepts', []):
                                    concept = concept_info['concept']
                                    if concept in chunk_text:
                                        relevance_score += 2  # 핵심 개념 매칭 시 높은 점수
                                        matched_concepts.append(concept)

                                # 3. 법적 근거와의 매칭
                                for legal_basis in context_analysis.get('legal_basis', []):
                                    if legal_basis in chunk_text:
                                        relevance_score += 3  # 법적 근거 매칭 시 더 높은 점수
                                        matched_concepts.append(legal_basis)

                                # 4. 문제점 키워드와의 매칭
                                for problem in context_analysis.get('problem_details', []):
                                    # 문제점에서 핵심 단어 추출하여 매칭
                                    problem_words = problem.split()[:5]  # 첫 5개 단어
                                    for word in problem_words:
                                        if len(word) > 1 and word in chunk_text:
                                            relevance_score += 1

                            # 관련성 점수 기준 (동적으로 조정)
                            min_relevance = 2 if context_analysis else 1

                            if relevance_score >= min_relevance:
                                theoretical_results.append({
                                    'topic': ', '.join(problem_keywords) if len(problem_keywords) > 1 else problem_keywords[0],
                                    'content': chunk_text,
                                    'relevance_score': float(similarity),
                                    'context_relevance': relevance_score,  # 문맥 관련성 점수
                                    'matched_concepts': matched_concepts,   # 매칭된 개념들
                                    'source': pkl_path,
                                    'query_used': unique_queries[0] if unique_queries else "기본검색"
                                })
                                st.write(f"[DEBUG] ✅ 발견: 유사도 {similarity:.3f}, 문맥관련성 {relevance_score}, 매칭개념: {matched_concepts}")
                            else:
                                st.write(f"[DEBUG] ❌ 제외: 유사도 {similarity:.3f}, 문맥관련성 {relevance_score} (기준: {min_relevance})")
                
                except Exception as e:
                    st.error(f"이론적 배경 검색 오류 ({pkl_path}): {str(e)}")
                    continue
        
        # 문맥 관련성과 유사도를 종합하여 정렬 (문맥 관련성에 더 높은 가중치)
        theoretical_results.sort(key=lambda x: (
            x.get('context_relevance', 0) * 0.7 + x['relevance_score'] * 0.3
        ), reverse=True)
        
        # 중복 제거 (유사한 내용 필터링)
        filtered_results = []
        seen_content = set()
        
        for result in theoretical_results:
            content_hash = result['content'][:100]  # 첫 100자로 중복 판별
            if content_hash not in seen_content:
                filtered_results.append(result)
                seen_content.add(content_hash)
                
                if len(filtered_results) >= max_results:
                    break
        
        st.write(f"[DEBUG] 이론적 배경 검색 완료: {len(filtered_results)}개 결과")
        return filtered_results
        
    except Exception as e:
        st.error(f"이론적 배경 검색 오류: {str(e)}")
        return []

def apply_violation_cases_to_ordinance(violation_cases: List[Dict], ordinance_text: str, pkl_paths: List[str]) -> List[Dict]:
    """위법 판례를 조례안에 직접 적용"""
    if not violation_cases:
        return []
    
    try:
        st.write(f"[DEBUG] 위법 판례 적용 시작: {len(violation_cases)}개 판례")
        
        # 조례 조문 추출
        ordinance_articles = extract_ordinance_articles(ordinance_text)
        st.write(f"[DEBUG] 조례 조문 추출: {len(ordinance_articles)}개")
        
        if not ordinance_articles:
            return []
        
        # 종합 위법성 검색 수행
        comprehensive_results = search_comprehensive_violation_cases(ordinance_articles, pkl_paths)
        
        return comprehensive_results
        
    except Exception as e:
        st.error(f"위법 판례 적용 오류: {str(e)}")
        return []

def format_comprehensive_analysis_result(results: List[Dict]) -> str:
    """종합 분석 결과 포맷팅"""
    if not results:
        return "종합 위법성 분석에서 특별한 위험이 발견되지 않았습니다."
    
    formatted_result = "🚨 **종합 위법성 분석 결과**\n\n"
    
    total_risks = sum(len(result['violation_risks']) for result in results)
    formatted_result += f"**총 {len(results)}개 조문에서 {total_risks}개의 위법 위험 발견**\n\n"
    
    for result in results:
        formatted_result += f"### {result['ordinance_article']} {result.get('ordinance_title', '')}\n"
        formatted_result += f"조례 내용: {result['ordinance_content'][:150]}...\n\n"
        
        for i, risk in enumerate(result['violation_risks'][:3], 1):
            formatted_result += f"**위험 {i}: {risk['violation_type']}** (위험도: {risk['risk_score']:.2f})\n"
            formatted_result += f"- 관련 판례: {risk['case_summary']}\n"
            formatted_result += f"- 개선 권고: {risk['recommendation']}\n"
            formatted_result += f"- 판례 출처: {risk['case_source']}\n\n"
        
        if len(result['violation_risks']) > 3:
            formatted_result += f"*(외 {len(result['violation_risks']) - 3}개 추가 위험)*\n\n"
        
        formatted_result += "---\n\n"
    
    return formatted_result

# 테스트 함수
def test_comprehensive_analysis():
    """종합 분석 테스트"""
    sample_ordinance = """
    제1조(목적) 이 조례는 주차장의 설치 및 관리에 관한 사항을 규정함을 목적으로 한다.
    
    제2조(정의) 이 조례에서 사용하는 용어의 뜻은 다음과 같다.
    1. "주차장"이란 자동차를 주차시키기 위한 시설을 말한다.
    
    제3조(주차장 설치 기준) 주차장의 설치 기준은 시장이 정한다.
    """
    
    pkl_paths = [
        'enhanced_vectorstore_20250914_101739.pkl'
    ]
    
    # 조문 추출 테스트
    articles = extract_ordinance_articles(sample_ordinance)
    print(f"추출된 조문 수: {len(articles)}")
    
    # 종합 분석 테스트
    if articles:
        results = search_comprehensive_violation_cases(articles, pkl_paths)
        print(f"분석 결과: {len(results)}개 조문에서 위험 발견")
        
        # 결과 포맷팅
        formatted = format_comprehensive_analysis_result(results)
        print(formatted[:500] + "...")

def create_optimized_analysis_payload(comprehensive_results: List[Dict], law_analysis: Dict, theoretical_background: List[Dict] = None) -> Dict[str, Any]:
    """Gemini API 호출을 위한 최적화된 분석 페이로드 생성"""

    if not comprehensive_results:
        return {'error': '분석 결과가 없습니다.'}

    try:
        st.write("### 🚀 Gemini API 호출 최적화")

        # 1. 핵심 위험 사례만 선별 (상위 위험도)
        high_risk_cases = []
        for result in comprehensive_results:
            for risk in result.get('violation_risks', []):
                if risk.get('risk_score', 0) >= 0.6:  # 위험도 0.6 이상만
                    high_risk_cases.append({
                        'article': result.get('ordinance_article', ''),
                        'risk_type': risk.get('violation_type', ''),
                        'risk_score': risk.get('risk_score', 0),
                        'case_summary': risk.get('case_summary', '')[:500],  # 500자로 제한
                        'similarity': risk.get('similarity', 0)
                    })

        # 위험도 순으로 정렬하고 상위 10개만 선택
        high_risk_cases.sort(key=lambda x: x['risk_score'], reverse=True)
        selected_cases = high_risk_cases[:10]

        st.write(f"**✅ 고위험 사례 선별**: {len(high_risk_cases)}개 중 {len(selected_cases)}개 선택")

        # 2. 관련 법령 요약 (정규화된 법령만)
        relevant_laws_summary = []
        if law_analysis.get('law_details'):
            # 상위 5개 법령만 선택
            top_laws = sorted(
                law_analysis['law_details'],
                key=lambda x: x.get('similarity_score', 0),
                reverse=True
            )[:5]

            for law_detail in top_laws:
                relevant_laws_summary.append({
                    'law_name': law_detail['law_name'],
                    'law_type': law_detail.get('law_type', ''),
                    'related_articles_count': len(law_detail.get('related_articles', []))
                })

        st.write(f"**✅ 관련 법령 요약**: {len(relevant_laws_summary)}개 법령")

        # 3. 이론적 배경 요약 (있는 경우)
        theory_summary = []
        if theoretical_background:
            for theory in theoretical_background[:5]:  # 상위 5개만
                theory_summary.append({
                    'principle': theory.get('legal_principle', '')[:200],  # 200자로 제한
                    'relevance': theory.get('relevance_score', 0)
                })

        # 4. 통합 페이로드 생성
        optimized_payload = {
            'analysis_summary': {
                'total_articles_analyzed': len(comprehensive_results),
                'high_risk_cases_count': len(selected_cases),
                'relevant_laws_count': len(relevant_laws_summary),
                'law_normalization_effect': {
                    'original_count': law_analysis.get('original_count', 0),
                    'normalized_count': law_analysis.get('normalized_count', 0),
                    'reduction_rate': law_analysis.get('reduction_rate', 0)
                }
            },
            'high_risk_violations': selected_cases,
            'relevant_laws': relevant_laws_summary,
            'theoretical_background': theory_summary,
            'optimization_metrics': {
                'total_text_length': sum(len(case.get('case_summary', '')) for case in selected_cases),
                'api_calls_saved': len(high_risk_cases) - len(selected_cases),
                'token_efficiency': f"약 {(len(high_risk_cases) - len(selected_cases)) * 1000} 토큰 절약"
            }
        }

        # 5. 페이로드 크기 체크
        import json
        payload_size = len(json.dumps(optimized_payload, ensure_ascii=False))

        st.write(f"**📊 최적화 효과**:")
        st.write(f"  - 선별된 사례: {len(selected_cases)}개 (전체 {len(high_risk_cases)}개 중)")
        st.write(f"  - 페이로드 크기: {payload_size:,} bytes")
        st.write(f"  - 예상 API 호출 절약: {len(high_risk_cases) - len(selected_cases)}회")

        if law_analysis.get('reduction_rate', 0) > 0:
            st.success(f"  - 법령명 중복 제거: {law_analysis['reduction_rate']:.1f}% 절약")

        return optimized_payload

    except Exception as e:
        st.error(f"페이로드 최적화 오류: {e}")
        return {'error': str(e)}

def format_optimized_prompt_for_gemini(payload: Dict[str, Any]) -> str:
    """최적화된 Gemini 프롬프트 생성"""

    if payload.get('error'):
        return f"분석 오류: {payload['error']}"

    try:
        prompt_parts = []

        # 1. 분석 개요
        summary = payload.get('analysis_summary', {})
        prompt_parts.append(f"""
## 조례 위법성 종합 분석 결과

**분석 개요:**
- 분석 대상 조문: {summary.get('total_articles_analyzed', 0)}개
- 고위험 사례: {summary.get('high_risk_cases_count', 0)}개
- 관련 법령: {summary.get('relevant_laws_count', 0)}개

**최적화 효과:**
- 법령명 정규화: {summary.get('law_normalization_effect', {}).get('original_count', 0)}개 → {summary.get('law_normalization_effect', {}).get('normalized_count', 0)}개
- 중복 제거율: {summary.get('law_normalization_effect', {}).get('reduction_rate', 0):.1f}%
""")

        # 2. 고위험 위법 사례
        high_risk_cases = payload.get('high_risk_violations', [])
        if high_risk_cases:
            prompt_parts.append("\n## 🚨 주요 위법 위험 사례\n")
            for i, case in enumerate(high_risk_cases, 1):
                prompt_parts.append(f"""
**{i}. {case.get('article', '')} - {case.get('risk_type', '')}**
- 위험도: {case.get('risk_score', 0):.2f}
- 유사도: {case.get('similarity', 0):.2f}
- 사례 요약: {case.get('case_summary', '')[:300]}...
""")

        # 3. 관련 법령
        relevant_laws = payload.get('relevant_laws', [])
        if relevant_laws:
            prompt_parts.append("\n## 📋 관련 주요 법령\n")
            for i, law in enumerate(relevant_laws, 1):
                prompt_parts.append(f"""
**{i}. {law.get('law_name', '')}**
- 법령 유형: {law.get('law_type', '')}
- 관련 조문 수: {law.get('related_articles_count', 0)}개
""")

        # 4. 분석 요청
        prompt_parts.append("""
## 📝 분석 요청

위 정보를 바탕으로 다음 사항에 대해 종합적으로 분석해 주세요:

1. **위법성 평가**: 각 조문별 위법 위험도와 근거
2. **법령 충돌 분석**: 상위법령과의 충돌 가능성
3. **개선 방안**: 구체적인 조례 개선 권고사항
4. **법적 근거**: 관련 법령 및 판례 인용
5. **우선순위**: 수정이 필요한 조문의 우선순위

**분석 시 고려사항:**
- 법령 간 위계 관계
- 지방자치단체의 자치권 범위
- 실무적 적용 가능성
""")

        final_prompt = "".join(prompt_parts)

        # 프롬프트 길이 체크
        st.write(f"**📝 생성된 프롬프트**: {len(final_prompt):,}자")

        return final_prompt

    except Exception as e:
        return f"프롬프트 생성 오류: {e}"

def analyze_comprehensive_violations_optimized(ordinance_text: str, pkl_paths: List[str]) -> Dict[str, Any]:
    """최적화된 종합 위법성 분석 (전체 프로세스)"""

    st.write("# 🔍 최적화된 종합 위법성 분석")

    try:
        # 1. 조문 추출
        st.write("## 1단계: 조문 추출")
        articles = extract_ordinance_articles(ordinance_text)
        st.write(f"✅ {len(articles)}개 조문 추출")

        if not articles:
            return {'error': '조문을 추출할 수 없습니다.'}

        # 2. 위법 사례 검색
        st.write("## 2단계: 위법 사례 검색")
        comprehensive_results = search_comprehensive_violation_cases(articles, pkl_paths)
        st.write(f"✅ {len(comprehensive_results)}개 조문에서 위험 발견")

        if not comprehensive_results:
            return {'error': '위법 사례를 찾을 수 없습니다.'}

        # 3. 법령명 추출 및 정규화
        st.write("## 3단계: 법령명 정규화")
        law_analysis = extract_and_normalize_relevant_laws(comprehensive_results)

        # 4. 최적화된 페이로드 생성
        st.write("## 4단계: Gemini API 최적화")
        optimized_payload = create_optimized_analysis_payload(comprehensive_results, law_analysis)

        # 5. Gemini 프롬프트 생성
        gemini_prompt = format_optimized_prompt_for_gemini(optimized_payload)

        # 최종 결과 반환
        return {
            'success': True,
            'articles_count': len(articles),
            'violations_found': len(comprehensive_results),
            'law_normalization': law_analysis,
            'optimized_payload': optimized_payload,
            'gemini_prompt': gemini_prompt,
            'optimization_summary': {
                'original_violations': sum(len(r.get('violation_risks', [])) for r in comprehensive_results),
                'selected_violations': len(optimized_payload.get('high_risk_violations', [])),
                'laws_normalized': law_analysis.get('normalized_count', 0),
                'laws_original': law_analysis.get('original_count', 0),
                'reduction_rate': law_analysis.get('reduction_rate', 0)
            }
        }

    except Exception as e:
        st.error(f"최적화된 분석 오류: {e}")
        return {'error': str(e)}

if __name__ == "__main__":
    test_comprehensive_analysis()