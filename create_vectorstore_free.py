"""
무료 sentence-transformers를 사용한 벡터스토어 생성 도구
- jachi_case_free_vectorstore.pkl (자치법규 사례집)
- lawcase_free_vectorstore.pkl (재의·제소 조례 모음집)
"""

import os
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
import pandas as pd
import time

def chunk_text(text, chunk_size=1000, overlap=200):
    """텍스트를 청크로 분할"""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        
        # 문장 단위로 끝나도록 조정
        if end < text_length:
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            last_break = max(last_period, last_newline)
            if last_break > start + chunk_size * 0.7:
                end = start + last_break + 1
                chunk = text[start:end]
        
        if chunk.strip():
            chunks.append({
                'text': chunk.strip(),
                'start': start,
                'end': end
            })
        
        start = end - overlap if end < text_length else end
    
    return chunks

def create_free_vectorstore(documents, output_path, model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'):
    """무료 sentence-transformers로 벡터스토어 생성"""
    print(f"모델 로딩: {model_name}")
    model = SentenceTransformer(model_name)
    
    all_chunks = []
    all_embeddings = []
    
    for i, doc in enumerate(documents):
        print(f"문서 {i+1}/{len(documents)} 처리 중...")
        
        # 텍스트 청킹
        chunks = chunk_text(doc['content'])
        print(f"  - {len(chunks)}개 청크 생성")
        
        # 각 청크에 메타데이터 추가
        for chunk in chunks:
            chunk_with_meta = {
                'text': chunk['text'],
                'source': doc.get('source', f'document_{i+1}'),
                'title': doc.get('title', f'문서 {i+1}'),
                'page': doc.get('page', 1),
                'chunk_id': len(all_chunks)
            }
            all_chunks.append(chunk_with_meta)
        
        # 임베딩 생성
        chunk_texts = [chunk['text'] for chunk in chunks]
        embeddings = model.encode(chunk_texts, show_progress_bar=True)
        all_embeddings.extend(embeddings)
        
        print(f"  - {len(embeddings)}개 임베딩 생성 완료")
    
    # 벡터스토어 저장
    vectorstore = {
        'chunks': all_chunks,
        'embeddings': np.array(all_embeddings),
        'model_name': model_name,
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open(output_path, 'wb') as f:
        pickle.dump(vectorstore, f)
    
    print(f"벡터스토어 저장 완료: {output_path}")
    print(f"총 {len(all_chunks)}개 청크, {len(all_embeddings)}개 임베딩")
    
    return vectorstore

def create_jachi_case_vectorstore():
    """자치법규 사례집 벡터스토어 생성"""
    # 예시 데이터 - 실제로는 PDF나 텍스트 파일에서 로드
    sample_documents = [
        {
            'content': '''자치법규 사례집 - 기관위임사무

1. 기관위임사무의 개념
지방자치단체의 장이 국가 또는 상급 지방자치단체의 사무를 위임받아 처리하는 사무를 말한다.

2. 기관위임사무 조례 제정 시 주의사항
- 상위법령에서 구체적으로 위임한 사항에 한하여 조례 제정 가능
- 위임의 범위를 벗어나는 내용 규정 불가
- 주민의 권리 제한이나 의무 부과는 법률의 근거 필요

3. 판례 사례
대법원 2018. 3. 29. 선고 2017추5432 판결
"기관위임사무에 관한 조례는 법령에서 구체적으로 위임한 사항에 한하여 제정할 수 있고, 
위임의 범위를 벗어나는 사항을 규정할 수 없다."''',
            'source': 'jachi_case_book.pdf',
            'title': '기관위임사무 사례',
            'page': 1
        },
        {
            'content': '''자치법규 사례집 - 상위법령 위배

1. 상위법령 위배의 유형
- 법률 직접 위배: 법률에서 금지한 사항을 허용하는 경우
- 법률 취지 위배: 법률의 목적이나 취지에 반하는 내용 규정
- 시행령·시행규칙 위배: 하위법령과 상충하는 내용 규정

2. 위법 사례
가. 건축법 위배 사례
- 건축법에서 금지한 용도를 조례로 허용한 경우
- 건축기준을 법령보다 완화한 경우

나. 도로교통법 위배 사례  
- 주차금지구역을 조례로 해제한 경우
- 속도제한을 법령보다 완화한 경우

3. 개선방안
- 상위법령 검토 철저
- 법제처 심사 사전 요청
- 전문가 자문 활용''',
            'source': 'jachi_case_book.pdf',
            'title': '상위법령 위배 사례',
            'page': 2
        }
    ]
    
    create_free_vectorstore(
        documents=sample_documents,
        output_path='jachi_case_free_vectorstore.pkl'
    )

def create_lawcase_vectorstore():
    """재의·제소 조례 모음집 벡터스토어 생성"""
    sample_documents = [
        {
            'content': '''재의요구 및 제소 조례 모음집

1. 재의요구 사례
가. 사안: ○○시 주차장 설치 조례
- 문제점: 상위법령 위배 (주차장법 시행령 기준 미달)
- 재의요구 사유: 법령 위배로 인한 무효
- 결과: 조례 수정 후 재의결

나. 사안: △△군 건축 조례
- 문제점: 기관위임사무 범위 초과
- 재의요구 사유: 권한 일탈
- 결과: 해당 조항 삭제

2. 제소 사례
가. 대법원 2019. 5. 30. 선고 2018추99999 판결
- 사안: 환경보전 조례의 영업제한 조항
- 쟁점: 법률유보 원칙 위배 여부
- 판시사항: "주민의 기본권을 제한하는 조례는 법률의 위임이 있어야 한다"
- 결과: 조례 무효

나. 대법원 2020. 1. 15. 선고 2019추12345 판결  
- 사안: 택시 운영 조례
- 쟁점: 기관위임사무 범위 초과
- 판시사항: "기관위임사무 조례는 위임 범위 내에서만 제정 가능"
- 결과: 일부 조항 무효''',
            'source': 'lawcase_book.pdf',
            'title': '재의·제소 사례',
            'page': 1
        },
        {
            'content': '''권한배분 위배 사례

1. 국가사무와 지방사무 구분 위배
가. 위배 사례
- 국가가 담당해야 할 사무를 지방자치단체에 부과
- 지방자치단체 고유사무를 국가가 직접 처리하도록 규정

나. 판례
헌법재판소 2015. 7. 30. 2013헌라1 결정
"지방자치단체의 자치사무와 국가의 위임사무를 명확히 구분하여야 한다"

2. 법률유보 위배 사례
가. 기본권 제한 조례
- 영업의 자유 제한: 법률 근거 없는 영업시간 제한
- 재산권 제한: 법률 근거 없는 부담금 부과
- 거주이전의 자유 제한: 법률 근거 없는 거주지역 제한

나. 개선방안
- 법률에서 구체적 위임 확인
- 기본권 제한 최소화 원칙 준수
- 비례원칙 적용''',
            'source': 'lawcase_book.pdf',
            'title': '권한배분·법률유보 위배',
            'page': 2
        }
    ]
    
    create_free_vectorstore(
        documents=sample_documents,
        output_path='lawcase_free_vectorstore.pkl'
    )

def main():
    """메인 함수"""
    print("무료 벡터스토어 생성 시작...")
    
    print("\n1. 자치법규 사례집 벡터스토어 생성")
    create_jachi_case_vectorstore()
    
    print("\n2. 재의·제소 조례 모음집 벡터스토어 생성")  
    create_lawcase_vectorstore()
    
    print("\n모든 벡터스토어 생성 완료!")

if __name__ == "__main__":
    main()