"""
종합 위법성 분석 모듈
조례안과 PKL 데이터베이스의 위법 판례를 매칭하여 종합적인 위법성 분석을 수행합니다.
"""

import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
import re
import os
from typing import List, Dict, Any, Tuple
import streamlit as st

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

if __name__ == "__main__":
    test_comprehensive_analysis()