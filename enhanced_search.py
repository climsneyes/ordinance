"""
향상된 검색 모듈
벡터스토어에서 더 정교한 검색을 수행합니다.
"""

import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
import os
from typing import List, Dict, Any, Tuple

def enhanced_vector_search(
    query: str,
    pkl_paths: List[str],
    top_k: int = 5,
    similarity_threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """향상된 벡터 검색"""
    
    try:
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        query_embedding = model.encode([query])
        
        all_results = []
        
        for pkl_path in pkl_paths:
            if not os.path.exists(pkl_path):
                continue
            
            with open(pkl_path, 'rb') as f:
                vectorstore = pickle.load(f)
            
            embeddings = vectorstore.get('embeddings', np.array([]))
            chunks = vectorstore.get('chunks', [])
            
            if len(embeddings) == 0:
                continue
            
            # 유사도 계산
            similarities = np.dot(query_embedding, embeddings.T).flatten()
            
            # 임계값 이상의 결과만 선택
            valid_indices = np.where(similarities >= similarity_threshold)[0]
            
            for idx in valid_indices:
                chunk = chunks[idx]
                result = {
                    'text': chunk['text'],
                    'source': chunk.get('source', ''),
                    'similarity': float(similarities[idx]),
                    'source_store': os.path.basename(pkl_path)
                }
                all_results.append(result)
        
        # 유사도 순으로 정렬하고 상위 k개 반환
        all_results.sort(key=lambda x: x['similarity'], reverse=True)
        return all_results[:top_k]
        
    except Exception as e:
        print(f"검색 오류: {str(e)}")
        return []

def multi_query_search(
    queries: List[str],
    pkl_paths: List[str],
    top_k: int = 3
) -> Dict[str, List[Dict[str, Any]]]:
    """다중 쿼리 검색"""
    
    results = {}
    for query in queries:
        results[query] = enhanced_vector_search(query, pkl_paths, top_k)
    
    return results

def contextual_search(
    main_query: str,
    context_queries: List[str],
    pkl_paths: List[str]
) -> List[Dict[str, Any]]:
    """컨텍스트 기반 검색"""
    
    # 메인 쿼리 결과
    main_results = enhanced_vector_search(main_query, pkl_paths, top_k=10)
    
    # 컨텍스트 쿼리로 필터링
    filtered_results = []
    
    for result in main_results:
        context_score = 0
        text_lower = result['text'].lower()
        
        for context_query in context_queries:
            if context_query.lower() in text_lower:
                context_score += 1
        
        if context_score > 0:
            result['context_score'] = context_score
            filtered_results.append(result)
    
    # 컨텍스트 점수와 유사도를 결합한 점수로 정렬
    filtered_results.sort(
        key=lambda x: x['similarity'] * 0.7 + (x['context_score'] / len(context_queries)) * 0.3,
        reverse=True
    )
    
    return filtered_results

if __name__ == "__main__":
    # 테스트
    pkl_paths = [
        'jachi_case_free_vectorstore.pkl',
        'lawcase_free_vectorstore.pkl'
    ]
    
    results = enhanced_vector_search("기관위임사무", pkl_paths)
    print(f"검색 결과: {len(results)}개")
    
    for i, result in enumerate(results):
        print(f"[{i+1}] 유사도: {result['similarity']:.3f}")
        print(f"     출처: {result['source']}")
        print(f"     내용: {result['text'][:100]}...")
        print()