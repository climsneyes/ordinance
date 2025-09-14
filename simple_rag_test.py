"""
간단한 RAG 테스트 모듈
벡터스토어의 기본 동작을 테스트합니다.
"""

import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
import os

def simple_rag_test(query: str = "기관위임사무"):
    """간단한 RAG 테스트"""
    print(f"쿼리: {query}")
    
    pkl_files = [
        'jachi_case_free_vectorstore.pkl',
        'lawcase_free_vectorstore.pkl'
    ]
    
    try:
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        query_embedding = model.encode([query])
        
        for pkl_file in pkl_files:
            if not os.path.exists(pkl_file):
                print(f"파일 없음: {pkl_file}")
                continue
            
            print(f"\n=== {pkl_file} 테스트 ===")
            
            with open(pkl_file, 'rb') as f:
                vectorstore = pickle.load(f)
            
            embeddings = vectorstore.get('embeddings', np.array([]))
            chunks = vectorstore.get('chunks', [])
            
            print(f"청크 수: {len(chunks)}")
            print(f"임베딩 형태: {embeddings.shape}")
            
            if len(embeddings) > 0:
                similarities = np.dot(query_embedding, embeddings.T).flatten()
                top_idx = np.argmax(similarities)
                
                print(f"최고 유사도: {similarities[top_idx]:.4f}")
                print(f"결과: {chunks[top_idx]['text'][:200]}...")
    
    except Exception as e:
        print(f"오류: {str(e)}")

def test_multiple_queries():
    """여러 쿼리 테스트"""
    queries = [
        "기관위임사무",
        "상위법령 위배",
        "법률유보 위배",
        "권한배분"
    ]
    
    for query in queries:
        print(f"\n{'='*50}")
        simple_rag_test(query)

if __name__ == "__main__":
    test_multiple_queries()