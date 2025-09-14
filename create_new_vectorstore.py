#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
새로운 벡터스토어 생성 스크립트
메모리 효율적인 임베딩으로 PDF를 벡터스토어로 변환
"""

import os
import pickle
import numpy as np
import streamlit as st
from typing import List, Dict, Any
import time
from datetime import datetime

# PDF 처리용
import PyPDF2
import fitz  # PyMuPDF

# 임베딩용
from sentence_transformers import SentenceTransformer
import torch

def extract_text_from_pdf(pdf_path: str) -> str:
    """PDF에서 텍스트 추출 (PyMuPDF 사용 - 한글 지원 우수)"""
    try:
        doc = fitz.open(pdf_path)
        text = ""

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            text += f"\n--- 페이지 {page_num + 1} ---\n"
            text += page_text

        doc.close()
        print(f"[INFO] PDF 추출 완료: {len(text)}자")
        return text

    except Exception as e:
        print(f"[ERROR] PDF 추출 실패: {str(e)}")

        # 백업: PyPDF2 사용
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""

                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    text += f"\n--- 페이지 {page_num + 1} ---\n"
                    text += page_text

            print(f"[INFO] 백업 방법으로 PDF 추출 완료: {len(text)}자")
            return text

        except Exception as e2:
            print(f"[ERROR] 백업 PDF 추출도 실패: {str(e2)}")
            return ""

def clean_and_chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, Any]]:
    """텍스트 정제 및 청킹"""
    import re

    # 1. 기본 정제
    text = re.sub(r'\s+', ' ', text)  # 여러 공백을 하나로
    text = re.sub(r'[·…]{3,}', ' ', text)  # 점선 제거
    text = re.sub(r'\.{3,}', ' ', text)  # 점점점 제거

    # 2. 페이지 구분자 기준으로 나누기
    pages = text.split('--- 페이지')

    chunks = []
    chunk_id = 0

    for page_idx, page_content in enumerate(pages):
        if not page_content.strip():
            continue

        # 페이지를 문장 단위로 분할
        sentences = re.split(r'[.!?]\s+', page_content)

        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # 청크 크기 체크
            if len(current_chunk) + len(sentence) <= chunk_size:
                current_chunk += sentence + ". "
            else:
                # 현재 청크 저장
                if len(current_chunk.strip()) > 50:  # 너무 짧은 청크 제외
                    chunks.append({
                        'id': chunk_id,
                        'text': current_chunk.strip(),
                        'page': page_idx,
                        'length': len(current_chunk.strip()),
                        'metadata': {
                            'page_number': page_idx,
                            'chunk_id': chunk_id,
                            'created_at': datetime.now().isoformat()
                        }
                    })
                    chunk_id += 1

                # 새 청크 시작 (오버랩 고려)
                current_chunk = sentence + ". "

        # 마지막 청크 처리
        if len(current_chunk.strip()) > 50:
            chunks.append({
                'id': chunk_id,
                'text': current_chunk.strip(),
                'page': page_idx,
                'length': len(current_chunk.strip()),
                'metadata': {
                    'page_number': page_idx,
                    'chunk_id': chunk_id,
                    'created_at': datetime.now().isoformat()
                }
            })
            chunk_id += 1

    print(f"[INFO] 청킹 완료: {len(chunks)}개 청크 생성")
    return chunks

def create_embeddings_batch(chunks: List[Dict], model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2', batch_size: int = 32) -> np.ndarray:
    """메모리 효율적인 배치 임베딩 생성"""

    try:
        # GPU 사용 가능시 사용, 아니면 CPU
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model = SentenceTransformer(model_name, device=device)
        print(f"[INFO] 모델 로드 완료: {model_name} (device: {device})")

        texts = [chunk['text'] for chunk in chunks]
        all_embeddings = []

        # 배치별 처리
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            print(f"[INFO] 배치 {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size} 처리 중... ({len(batch_texts)}개)")

            # 메모리 정리
            if i > 0:
                torch.cuda.empty_cache() if torch.cuda.is_available() else None

            try:
                batch_embeddings = model.encode(
                    batch_texts,
                    batch_size=min(batch_size, len(batch_texts)),
                    show_progress_bar=True,
                    convert_to_numpy=True,
                    normalize_embeddings=True  # 코사인 유사도 최적화
                )
                all_embeddings.extend(batch_embeddings)

            except Exception as e:
                print(f"[ERROR] 배치 처리 실패: {str(e)}")
                # 개별 처리로 폴백
                for text in batch_texts:
                    try:
                        emb = model.encode([text], convert_to_numpy=True)[0]
                        all_embeddings.append(emb)
                    except:
                        # 더미 임베딩 (문제가 있는 텍스트용)
                        emb = np.zeros(model.get_sentence_embedding_dimension())
                        all_embeddings.append(emb)

            time.sleep(0.1)  # 메모리 안정화

        embeddings_array = np.array(all_embeddings)
        print(f"[INFO] 임베딩 생성 완료: {embeddings_array.shape}")

        return embeddings_array

    except Exception as e:
        print(f"[ERROR] 임베딩 생성 실패: {str(e)}")
        return np.array([])

def create_new_vectorstore(pdf_path: str, output_path: str = None) -> str:
    """새로운 벡터스토어 생성"""

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    if not output_path:
        output_path = pdf_path.replace('.pdf', '_new_vectorstore.pkl')

    print(f"[INFO] 벡터스토어 생성 시작: {pdf_path}")
    print(f"[INFO] 출력 경로: {output_path}")

    # 1. PDF 텍스트 추출
    print("[STEP 1] PDF 텍스트 추출...")
    text = extract_text_from_pdf(pdf_path)
    if not text:
        raise ValueError("PDF에서 텍스트를 추출할 수 없습니다.")

    # 2. 텍스트 정제 및 청킹
    print("[STEP 2] 텍스트 청킹...")
    chunks = clean_and_chunk_text(text, chunk_size=500, overlap=50)
    if not chunks:
        raise ValueError("유효한 청크를 생성할 수 없습니다.")

    # 3. 임베딩 생성
    print("[STEP 3] 임베딩 생성...")
    embeddings = create_embeddings_batch(chunks, batch_size=16)  # 메모리 고려해서 작은 배치

    if len(embeddings) == 0:
        raise ValueError("임베딩 생성에 실패했습니다.")

    # 4. 벡터스토어 저장
    print("[STEP 4] 벡터스토어 저장...")

    vectorstore_data = {
        'documents': [chunk['text'] for chunk in chunks],
        'embeddings': embeddings,
        'metadatas': [chunk['metadata'] for chunk in chunks],
        'chunks': chunks,  # 상세 정보 포함
        'pdf_path': pdf_path,
        'created_at': datetime.now().isoformat(),
        'model_name': 'paraphrase-multilingual-MiniLM-L12-v2',
        'embedding_dimension': embeddings.shape[1] if len(embeddings) > 0 else 0,
        'total_chunks': len(chunks),
        'total_documents': len(chunks)
    }

    with open(output_path, 'wb') as f:
        pickle.dump(vectorstore_data, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"[SUCCESS] 벡터스토어 저장 완료: {output_path}")
    print(f"[INFO] 총 {len(chunks)}개 청크, {embeddings.shape[1]}차원 임베딩")

    return output_path

def inspect_vectorstore(pkl_path: str):
    """벡터스토어 내용 확인"""
    try:
        with open(pkl_path, 'rb') as f:
            data = pickle.load(f)

        print(f"\n=== 벡터스토어 정보 ===")
        print(f"파일: {pkl_path}")
        print(f"생성일: {data.get('created_at', 'N/A')}")
        print(f"모델: {data.get('model_name', 'N/A')}")
        print(f"임베딩 차원: {data.get('embedding_dimension', 'N/A')}")
        print(f"총 청크 수: {data.get('total_chunks', len(data.get('documents', [])))}")

        # 샘플 내용 확인
        documents = data.get('documents', [])
        print(f"\n=== 샘플 내용 (상위 3개) ===")
        for i, doc in enumerate(documents[:3]):
            print(f"[{i+1}] {doc[:100]}...")
            print("---")

        # 임베딩 정보
        embeddings = data.get('embeddings', np.array([]))
        if len(embeddings) > 0:
            print(f"\n=== 임베딩 정보 ===")
            print(f"Shape: {embeddings.shape}")
            print(f"타입: {type(embeddings)}")
            print(f"첫 번째 임베딩 샘플: {embeddings[0][:5]}...")

        return True

    except Exception as e:
        print(f"[ERROR] 벡터스토어 확인 실패: {str(e)}")
        return False

if __name__ == "__main__":
    # PDF 경로
    pdf_path = r"c:\jo(9.11.)\3. 지방자치단체의 재의·제소 조례 모음집(Ⅸ) (1).pdf"

    try:
        # 새 벡터스토어 생성
        output_path = create_new_vectorstore(pdf_path)

        # 생성된 벡터스토어 확인
        print("\n" + "="*50)
        inspect_vectorstore(output_path)

    except Exception as e:
        print(f"[ERROR] 전체 프로세스 실패: {str(e)}")