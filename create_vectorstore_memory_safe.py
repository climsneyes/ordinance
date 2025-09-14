"""
메모리 안전 벡터스토어 생성 도구
대용량 문서를 안전하게 처리하기 위한 배치 처리 방식
"""

import os
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
import pandas as pd
import time
import gc
from typing import List, Dict, Any

def chunk_text_memory_safe(text: str, chunk_size: int = 800, overlap: int = 150) -> List[Dict[str, Any]]:
    """메모리 효율적인 텍스트 청킹"""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        
        # 문장 경계에서 자르기
        if end < text_length:
            # 마침표나 줄바꿈에서 자르기 시도
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            last_break = max(last_period, last_newline)
            
            # 너무 짧지 않으면 문장 경계에서 자르기
            if last_break > start + chunk_size * 0.6:
                end = start + last_break + 1
                chunk = text[start:end]
        
        chunk_text = chunk.strip()
        if chunk_text and len(chunk_text) > 50:  # 너무 짧은 청크 제외
            chunks.append({
                'text': chunk_text,
                'start_pos': start,
                'end_pos': end,
                'length': len(chunk_text)
            })
        
        start = end - overlap if end < text_length else end
    
    return chunks

def create_embeddings_batch(model: SentenceTransformer, texts: List[str], batch_size: int = 32) -> np.ndarray:
    """배치 단위로 임베딩 생성"""
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        batch_embeddings = model.encode(
            batch_texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        all_embeddings.append(batch_embeddings)
        
        # 메모리 정리
        if i % (batch_size * 4) == 0:
            gc.collect()
    
    return np.vstack(all_embeddings) if all_embeddings else np.array([])

def create_memory_safe_vectorstore(
    documents: List[Dict[str, Any]], 
    output_path: str,
    model_name: str = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
    batch_size: int = 16,
    max_chunks_per_doc: int = 200
) -> Dict[str, Any]:
    """메모리 안전 벡터스토어 생성"""
    
    print(f"메모리 안전 모드로 벡터스토어 생성: {output_path}")
    print(f"모델: {model_name}")
    print(f"배치 크기: {batch_size}")
    
    # 모델 로드
    print("모델 로딩...")
    model = SentenceTransformer(model_name)
    
    all_chunks = []
    all_embeddings = []
    
    for doc_idx, doc in enumerate(documents):
        print(f"\n문서 {doc_idx + 1}/{len(documents)} 처리 중...")
        print(f"문서 제목: {doc.get('title', 'Unknown')}")
        
        # 문서 청킹
        chunks = chunk_text_memory_safe(doc['content'])
        print(f"  - 총 {len(chunks)}개 청크 생성")
        
        # 청크 수 제한 (메모리 보호)
        if len(chunks) > max_chunks_per_doc:
            print(f"  - 청크 수를 {max_chunks_per_doc}개로 제한")
            chunks = chunks[:max_chunks_per_doc]
        
        # 청크에 메타데이터 추가
        doc_chunks = []
        for chunk_idx, chunk in enumerate(chunks):
            chunk_with_meta = {
                'text': chunk['text'],
                'source': doc.get('source', f'document_{doc_idx + 1}'),
                'title': doc.get('title', f'문서 {doc_idx + 1}'),
                'page': doc.get('page', 1),
                'doc_id': doc_idx,
                'chunk_id': len(all_chunks) + chunk_idx,
                'start_pos': chunk['start_pos'],
                'end_pos': chunk['end_pos']
            }
            doc_chunks.append(chunk_with_meta)
        
        # 배치 임베딩 생성
        chunk_texts = [chunk['text'] for chunk in doc_chunks]
        print(f"  - {len(chunk_texts)}개 청크 임베딩 생성 중...")
        
        doc_embeddings = create_embeddings_batch(model, chunk_texts, batch_size)
        
        # 결과 저장
        all_chunks.extend(doc_chunks)
        all_embeddings.append(doc_embeddings)
        
        print(f"  - 완료: {len(doc_embeddings)}개 임베딩")
        
        # 메모리 정리
        del chunk_texts, doc_chunks, chunks, doc_embeddings
        gc.collect()
    
    # 모든 임베딩 결합
    print("\n임베딩 결합 중...")
    final_embeddings = np.vstack(all_embeddings) if all_embeddings else np.array([])
    
    # 메모리 정리
    del all_embeddings
    gc.collect()
    
    # 벡터스토어 구성
    vectorstore = {
        'chunks': all_chunks,
        'embeddings': final_embeddings,
        'model_name': model_name,
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'chunk_count': len(all_chunks),
        'embedding_dimension': final_embeddings.shape[1] if len(final_embeddings) > 0 else 0,
        'creation_config': {
            'batch_size': batch_size,
            'max_chunks_per_doc': max_chunks_per_doc,
            'chunk_size': 800,
            'overlap': 150
        }
    }
    
    # 저장
    print(f"\n벡터스토어 저장 중: {output_path}")
    with open(output_path, 'wb') as f:
        pickle.dump(vectorstore, f, protocol=pickle.HIGHEST_PROTOCOL)
    
    print(f"✅ 벡터스토어 생성 완료!")
    print(f"  - 총 청크 수: {len(all_chunks):,}")
    print(f"  - 임베딩 차원: {vectorstore['embedding_dimension']}")
    print(f"  - 파일 크기: {os.path.getsize(output_path) / (1024*1024):.1f} MB")
    
    return vectorstore

def load_documents_from_txt_files(file_paths: List[str]) -> List[Dict[str, Any]]:
    """텍스트 파일들에서 문서 로드"""
    documents = []
    
    for file_path in file_paths:
        if os.path.exists(file_path):
            print(f"파일 로드 중: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                documents.append({
                    'content': content,
                    'source': os.path.basename(file_path),
                    'title': os.path.splitext(os.path.basename(file_path))[0],
                    'page': 1
                })
                print(f"  - 로드 완료: {len(content):,} 문자")
                
            except Exception as e:
                print(f"  - 로드 실패: {e}")
        else:
            print(f"파일 없음: {file_path}")
    
    return documents

def create_enhanced_sample_documents():
    """향상된 샘플 문서 생성"""
    
    jachi_case_content = """자치법규 사례집 - 종합판

제1장 기관위임사무

1. 기관위임사무의 법적 성격
기관위임사무는 국가 또는 상급 지방자치단체가 하급 지방자치단체의 장에게 위임한 사무로서, 
위임기관의 지휘·감독을 받아 처리하는 사무를 말한다.

1-1. 기관위임사무 조례의 한계
- 위임받은 범위 내에서만 조례 제정 가능
- 주민의 권리 제한이나 의무 부과는 법률의 근거 필요
- 상위기관의 지침에 따라 처리

1-2. 주요 판례
대법원 2018. 3. 29. 선고 2017추5432 판결
"기관위임사무에 관한 조례는 법령에서 구체적으로 위임한 사항에 한하여 제정할 수 있고, 
위임의 범위를 벗어나는 사항을 규정할 수 없다."

대법원 2019. 7. 11. 선고 2018추7890 판결
"기관위임사무 조례라 하더라도 주민의 기본권을 제한하는 경우에는 
법률의 위임이 있어야 하고, 그 위임은 구체적이고 명확해야 한다."

제2장 상위법령 위배

2. 상위법령 위배의 유형과 사례

2-1. 직접 위배 사례
가. 건축법 위배 사례
사안: ○○시 건축 조례
내용: 건축법에서 금지한 용도를 조례로 허용
결과: 조례 무효

나. 도로교통법 위배 사례
사안: △△구 주차 조례  
내용: 주차금지구역을 조례로 해제
결과: 해당 조항 무효

2-2. 취지 위배 사례
가. 환경법 취지 위배
사안: ◇◇시 환경보전 조례
내용: 환경보전 목적에 반하는 개발 허용 규정
결과: 조례 개정 요구

제3장 법률유보 위배

3. 법률유보 원칙 위배 사례

3-1. 영업의 자유 제한
사안: ☆☆군 상가 영업시간 제한 조례
문제점: 법률 근거 없는 영업시간 제한
판례: 헌법재판소 2020. 5. 28. 2019헌마456 결정
결과: 위헌 결정

3-2. 재산권 제한
사안: ◎◎시 개발부담금 조례
문제점: 법률 근거 없는 부담금 부과
결과: 조례 무효

제4장 권한배분 위배

4. 국가사무와 지방사무 구분 위배

4-1. 국가사무 침해 사례
사안: ●●도 외국인 정책 조례
문제점: 국가 고유사무인 출입국 관리에 관한 규정
결과: 해당 조항 삭제

4-2. 자치사무 침해 대응 사례
사안: 중앙정부의 지방사무 간섭
대응: 지방자치단체의 이의제기 및 법적 대응
결과: 자치권 확보

제5장 개선방안

5. 조례 제정 시 점검사항
- 상위법령과의 충돌 여부 검토
- 기본권 제한 시 법률 근거 확인  
- 기관위임사무 범위 준수
- 전문가 자문 및 법제처 심사 활용

5-1. 사전 검토 체크리스트
□ 법령 위임 근거 확인
□ 기본권 제한 최소화
□ 비례원칙 준수
□ 명확성 원칙 준수
□ 평등원칙 준수"""

    lawcase_content = """재의요구 및 제소 조례 모음집

제1편 재의요구 사례

제1장 재의요구 제도 개관

1. 재의요구의 법적 근거
지방자치법 제171조에 따라 시도지사는 시군구의 조례나 규칙이 법령에 위반되거나 
국가 또는 다른 지방자치단체의 사무에 관한 것일 때 재의를 요구할 수 있다.

1-1. 재의요구 사유
- 법령 위반
- 국가사무 침해
- 다른 지방자치단체 사무 침해
- 공익 저해

제2장 구체적 재의요구 사례

2. 법령 위반 재의요구 사례

2-1. 상위법령 직접 위배
사안: ○○시 주차장 설치 조례
재의요구 사유: 주차장법 시행령 기준 미달 규정
재의요구 기관: △△도지사
결과: 조례 수정 후 재의결
개정 내용: 주차장법 시행령 기준에 맞춘 주차구획 규격 조정

2-2. 기관위임사무 범위 초과
사안: ◇◇군 건축 조례
재의요구 사유: 건축법에서 위임하지 않은 사항 규정
재의요구 기관: ☆☆도지사  
결과: 해당 조항 삭제
삭제 조항: 건축허가 절차 중 법령에 없는 추가 서류 요구 조항

2-3. 법률유보 위배
사안: ●●구 소음방지 조례
재의요구 사유: 법률 근거 없는 과태료 부과 규정
재의요구 기관: ■■시장
결과: 과태료 조항 삭제

제3장 권한 일탈 재의요구

3. 국가사무 침해 사례

3-1. 출입국 관리 사무 침해
사안: ▲▲시 외국인 거주 제한 조례
재의요구 사유: 국가 고유사무인 출입국 관리 침해
결과: 조례 전부 폐지

3-2. 교육 사무 침해
사안: ◎◎구 학교급식 조례
재의요구 사유: 교육청 소관 사무 침해
결과: 교육청과의 협의 조항 추가

제2편 제소 사례

제1장 제소 제도 개관

1. 조례 무효 확인 소송
지방자치법 제172조에 따라 시도지사, 중앙행정기관의 장, 이해관계인이 
법원에 조례의 무효 확인을 구할 수 있다.

제2장 주요 제소 판례

2. 법률유보 위배 제소 사례

2-1. 영업제한 조례 무효 판결
대법원 2019. 5. 30. 선고 2018추99999 판결
사안: ○○시 환경보전 조례의 영업제한 조항
쟁점: 법률유보 원칙 위배 여부
판시사항: "주민의 기본권을 제한하는 조례는 법률의 위임이 있어야 하고, 
그 위임은 구체적이고 명확해야 한다"
결과: 조례 무효

2-2. 부담금 부과 조례 무효 판결  
대법원 2020. 1. 15. 선고 2019추12345 판결
사안: △△구 개발비용 부담 조례
쟁점: 법률 근거 없는 부담금 부과
판시사항: "조례에 의한 부담금 부과는 법률의 위임이 있는 경우에만 가능하다"
결과: 조례 무효

3. 기관위임사무 범위 초과 제소 사례

3-1. 택시 운영 조례 무효 판결
대법원 2020. 7. 9. 선고 2019추67890 판결
사안: ◇◇시 택시 운영 조례
쟁점: 기관위임사무 범위 초과 여부
판시사항: "기관위임사무 조례는 위임받은 범위 내에서만 제정할 수 있고, 
위임 범위를 벗어나는 사항을 규정할 수 없다"
결과: 일부 조항 무효

3-2. 건축허가 조례 무효 판결
대법원 2021. 3. 25. 선고 2020추13579 판결
사안: ☆☆군 건축허가 간소화 조례
쟁점: 건축법 위임 범위 초과
판시사항: "건축허가에 관한 조례는 건축법에서 위임한 사항에 한하여 제정할 수 있다"
결과: 조례 무효

제3장 권한배분 위배 제소

4. 국가사무와 지방사무 구분 위배

4-1. 헌법재판소 권한쟁의 사례
헌법재판소 2015. 7. 30. 2013헌라1 결정
사안: 중앙정부와 지방자치단체 간 사무배분 분쟁
쟁점: 자치사무와 위임사무 구분
판시사항: "지방자치단체의 자치사무와 국가의 위임사무를 명확히 구분하여야 하고, 
국가는 지방자치단체의 자치사무에 부당하게 간섭할 수 없다"
결과: 국가의 간섭 부당 결정

제4장 예방 및 대응방안

5. 조례 제정 시 사전 검토사항

5-1. 법령 검토 체크리스트
□ 헌법 적합성 검토
□ 법률 위반 여부 확인  
□ 시행령·시행규칙 충돌 검토
□ 다른 조례와의 정합성 검토
□ 기관위임사무 범위 확인

5-2. 기본권 제한 검토사항
□ 법률유보 원칙 준수
□ 과잉금지 원칙 적용
□ 평등원칙 준수
□ 적법절차 원칙 준수
□ 신뢰보호 원칙 고려

5-3. 전문가 자문 활용
- 법제처 사전 심사 요청
- 대학 법학과 교수 자문
- 변호사 자문
- 행정학 전문가 자문

6. 제소 대응방안

6-1. 소송 대응 전략
- 적극적 반박 준비
- 전문가 증인 확보
- 비교법적 검토
- 정책적 필요성 입증

6-2. 조례 개정 검토
- 법원 판결 취지 반영
- 유사 조례 일괄 정비
- 예방적 개정 추진"""

    return [
        {
            'content': jachi_case_content,
            'source': 'jachi_case_comprehensive.pdf',
            'title': '자치법규 사례집 종합판',
            'page': 1
        },
        {
            'content': lawcase_content,
            'source': 'lawcase_comprehensive.pdf', 
            'title': '재의요구 및 제소 조례 종합 모음집',
            'page': 1
        }
    ]

def main():
    """메인 실행 함수"""
    print("=== 메모리 안전 벡터스토어 생성 도구 ===\n")
    
    # 샘플 문서 생성
    print("샘플 문서 준비 중...")
    documents = create_enhanced_sample_documents()
    
    # 자치법규 사례집 벡터스토어 생성
    print("\n1. 자치법규 사례집 벡터스토어 생성")
    jachi_docs = [doc for doc in documents if 'jachi_case' in doc['source']]
    create_memory_safe_vectorstore(
        documents=jachi_docs,
        output_path='jachi_case_free_vectorstore.pkl',
        batch_size=8,  # 메모리 안전을 위해 작은 배치
        max_chunks_per_doc=150
    )
    
    # 재의제소 조례 모음집 벡터스토어 생성
    print("\n2. 재의·제소 조례 모음집 벡터스토어 생성")
    lawcase_docs = [doc for doc in documents if 'lawcase' in doc['source']]
    create_memory_safe_vectorstore(
        documents=lawcase_docs,
        output_path='lawcase_free_vectorstore.pkl', 
        batch_size=8,
        max_chunks_per_doc=150
    )
    
    print("\n🎉 모든 벡터스토어 생성 완료!")
    
    # 생성된 파일 정보 출력
    for filename in ['jachi_case_free_vectorstore.pkl', 'lawcase_free_vectorstore.pkl']:
        if os.path.exists(filename):
            size_mb = os.path.getsize(filename) / (1024 * 1024)
            print(f"  - {filename}: {size_mb:.1f} MB")

if __name__ == "__main__":
    main()