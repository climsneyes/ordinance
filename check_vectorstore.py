"""
벡터스토어 확인 및 테스트 도구
생성된 PKL 파일의 내용과 구조를 확인합니다.
"""

import pickle
import numpy as np
import os
from sentence_transformers import SentenceTransformer
import time

def load_and_inspect_vectorstore(pkl_path):
    """벡터스토어 로드 및 구조 확인"""
    if not os.path.exists(pkl_path):
        print(f"❌ 파일이 존재하지 않습니다: {pkl_path}")
        return None
    
    print(f"\n📁 벡터스토어 분석: {pkl_path}")
    print(f"📊 파일 크기: {os.path.getsize(pkl_path) / (1024*1024):.1f} MB")
    
    try:
        with open(pkl_path, 'rb') as f:
            vectorstore = pickle.load(f)
        
        print(f"✅ 로드 성공!")
        
        # 기본 정보
        print(f"\n📋 기본 정보:")
        print(f"  - 생성일시: {vectorstore.get('created_at', 'Unknown')}")
        print(f"  - 모델명: {vectorstore.get('model_name', 'Unknown')}")
        print(f"  - 청크 수: {len(vectorstore.get('chunks', []))}")
        
        # 임베딩 정보
        embeddings = vectorstore.get('embeddings', np.array([]))
        if len(embeddings) > 0:
            print(f"  - 임베딩 차원: {embeddings.shape[1]}")
            print(f"  - 임베딩 형태: {embeddings.shape}")
            print(f"  - 데이터 타입: {embeddings.dtype}")
        else:
            print(f"  - 임베딩: 없음")
        
        # 설정 정보
        config = vectorstore.get('creation_config', {})
        if config:
            print(f"\n⚙️ 생성 설정:")
            for key, value in config.items():
                print(f"  - {key}: {value}")
        
        # 청크 샘플 확인
        chunks = vectorstore.get('chunks', [])
        if chunks:
            print(f"\n📝 청크 샘플 (처음 3개):")
            for i, chunk in enumerate(chunks[:3]):
                print(f"\n  [{i+1}] 소스: {chunk.get('source', 'Unknown')}")
                print(f"      제목: {chunk.get('title', 'Unknown')}")
                print(f"      텍스트: {chunk.get('text', '')[:150]}...")
                print(f"      길이: {len(chunk.get('text', ''))} 문자")
        
        return vectorstore
        
    except Exception as e:
        print(f"❌ 로드 실패: {str(e)}")
        return None

def test_search_functionality(vectorstore, query="기관위임사무"):
    """검색 기능 테스트"""
    if not vectorstore:
        return
    
    print(f"\n🔍 검색 테스트: '{query}'")
    
    try:
        # 모델 로드
        model_name = vectorstore.get('model_name', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        print(f"모델 로딩: {model_name}")
        model = SentenceTransformer(model_name)
        
        # 쿼리 임베딩
        query_embedding = model.encode([query])
        
        # 유사도 계산
        embeddings = vectorstore.get('embeddings', np.array([]))
        if len(embeddings) == 0:
            print("❌ 임베딩이 없습니다")
            return
        
        similarities = np.dot(query_embedding, embeddings.T).flatten()
        top_indices = np.argsort(similarities)[::-1][:5]
        
        print(f"📋 상위 5개 결과:")
        chunks = vectorstore.get('chunks', [])
        
        for i, idx in enumerate(top_indices):
            similarity = similarities[idx]
            chunk = chunks[idx]
            
            print(f"\n  [{i+1}] 유사도: {similarity:.4f}")
            print(f"      소스: {chunk.get('source', 'Unknown')}")
            print(f"      제목: {chunk.get('title', 'Unknown')}")
            print(f"      텍스트: {chunk.get('text', '')[:200]}...")
            
    except Exception as e:
        print(f"❌ 검색 테스트 실패: {str(e)}")

def compare_vectorstores(pkl_paths):
    """여러 벡터스토어 비교"""
    print(f"\n📊 벡터스토어 비교 분석")
    print("=" * 60)
    
    stores = {}
    for path in pkl_paths:
        if os.path.exists(path):
            stores[path] = load_and_inspect_vectorstore(path)
    
    if len(stores) < 2:
        print("비교할 벡터스토어가 충분하지 않습니다.")
        return
    
    # 비교 표 생성
    print(f"\n📋 요약 비교:")
    print(f"{'파일명':<30} {'크기(MB)':<10} {'청크수':<8} {'임베딩차원':<10}")
    print("-" * 60)
    
    for path, store in stores.items():
        filename = os.path.basename(path)
        size_mb = os.path.getsize(path) / (1024*1024)
        chunks_count = len(store.get('chunks', [])) if store else 0
        embeddings = store.get('embeddings', np.array([])) if store else np.array([])
        embedding_dim = embeddings.shape[1] if len(embeddings) > 0 else 0
        
        print(f"{filename:<30} {size_mb:<10.1f} {chunks_count:<8} {embedding_dim:<10}")

def analyze_chunk_distribution(vectorstore):
    """청크 분포 분석"""
    if not vectorstore:
        return
    
    chunks = vectorstore.get('chunks', [])
    if not chunks:
        return
    
    print(f"\n📈 청크 분포 분석:")
    
    # 길이 분포
    lengths = [len(chunk.get('text', '')) for chunk in chunks]
    print(f"  - 평균 길이: {np.mean(lengths):.0f} 문자")
    print(f"  - 최소 길이: {min(lengths)} 문자")
    print(f"  - 최대 길이: {max(lengths)} 문자")
    print(f"  - 중간값: {np.median(lengths):.0f} 문자")
    
    # 소스별 분포
    sources = {}
    for chunk in chunks:
        source = chunk.get('source', 'Unknown')
        sources[source] = sources.get(source, 0) + 1
    
    print(f"\n  📚 소스별 청크 수:")
    for source, count in sources.items():
        print(f"    - {source}: {count}개")

def main():
    """메인 함수"""
    print("🔍 벡터스토어 검사 도구")
    print("=" * 50)
    
    # 확인할 PKL 파일들
    pkl_files = [
        'jachi_case_free_vectorstore.pkl',
        'lawcase_free_vectorstore.pkl'
    ]
    
    # 각 파일 개별 분석
    stores = {}
    for pkl_file in pkl_files:
        store = load_and_inspect_vectorstore(pkl_file)
        if store:
            stores[pkl_file] = store
            analyze_chunk_distribution(store)
    
    # 비교 분석
    if len(stores) > 1:
        compare_vectorstores(pkl_files)
    
    # 검색 테스트
    for pkl_file, store in stores.items():
        print(f"\n" + "="*60)
        print(f"🔍 {pkl_file} 검색 테스트")
        test_search_functionality(store, "기관위임사무")
        test_search_functionality(store, "상위법령 위배")
    
    print(f"\n✅ 벡터스토어 검사 완료!")

if __name__ == "__main__":
    main()