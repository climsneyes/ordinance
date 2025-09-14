#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
개선된 벡터스토어 생성 스크립트
- 더 긴 청크 사이즈 (의미 단위 보존)
- 여러 PDF 파일 지원
- 리랭커 기능 추가
- 개선된 텍스트 전처리
"""

import os
import pickle
import numpy as np
import streamlit as st
from typing import List, Dict, Any, Tuple
import time
from datetime import datetime
import re

# PDF 처리용
import PyPDF2
import fitz  # PyMuPDF

# 임베딩 및 리랭킹용
from sentence_transformers import SentenceTransformer, CrossEncoder
import torch

def extract_text_from_pdf_enhanced(pdf_path: str) -> str:
    """향상된 PDF 텍스트 추출"""
    try:
        doc = fitz.open(pdf_path)
        text = ""

        for page_num in range(len(doc)):
            page = doc[page_num]

            # 텍스트 추출
            page_text = page.get_text()

            # 페이지 정보 추가 (검색에 도움)
            text += f"\n=== {os.path.basename(pdf_path)} - 페이지 {page_num + 1} ===\n"
            text += page_text
            text += "\n"

        doc.close()
        print(f"[INFO] PDF 추출 완료: {pdf_path} ({len(text):,}자)")
        return text

    except Exception as e:
        print(f"[ERROR] PDF 추출 실패 ({pdf_path}): {str(e)}")
        return ""

def enhanced_text_cleaning(text: str) -> str:
    """향상된 텍스트 정제"""

    # 1. 불필요한 문자 제거
    text = re.sub(r'[·…]{3,}', ' ', text)  # 점선 제거
    text = re.sub(r'\.{3,}', ' ', text)    # 점점점 제거
    text = re.sub(r'_+', ' ', text)        # 언더스코어 반복 제거
    text = re.sub(r'-{3,}', ' ', text)     # 대시 반복 제거

    # 2. 페이지 번호 등 불필요한 정보 제거
    text = re.sub(r'\b\d+\s*페이지?\b', '', text)
    text = re.sub(r'\b\d+\s*쪽?\b', '', text)
    text = re.sub(r'\bPage\s+\d+\b', '', text, flags=re.IGNORECASE)

    # 3. 목차 패턴 제거
    text = re.sub(r'^[IVX]+\.?\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\.?\s*$', '', text, flags=re.MULTILINE)

    # 4. 과도한 공백 정리
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # 3개 이상 개행을 2개로

    return text.strip()

def smart_chunking(text: str, target_size: int = 1000, overlap: int = 100) -> List[Dict[str, Any]]:
    """의미 단위 기반 스마트 청킹"""

    # 1. 섹션별 분할 (===로 구분된 페이지들)
    sections = text.split('===')

    chunks = []
    chunk_id = 0

    for section_idx, section in enumerate(sections):
        if not section.strip():
            continue

        # 페이지 정보 추출
        page_info = ""
        lines = section.split('\n')
        if len(lines) > 0 and ('페이지' in lines[0] or 'Page' in lines[0]):
            page_info = lines[0].strip()
            section_content = '\n'.join(lines[1:]).strip()
        else:
            section_content = section.strip()

        if not section_content:
            continue

        # 2. 문단별 분할 (이중 개행 기준)
        paragraphs = section_content.split('\n\n')

        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 현재 청크에 추가했을 때 크기 확인
            potential_chunk = (current_chunk + '\n\n' + para).strip()

            if len(potential_chunk) <= target_size:
                # 타겟 사이즈 이하면 추가
                current_chunk = potential_chunk
            else:
                # 타겟 사이즈 초과하면 현재 청크 저장하고 새 청크 시작
                if current_chunk.strip():
                    chunks.append({
                        'id': chunk_id,
                        'text': current_chunk.strip(),
                        'page_info': page_info,
                        'section_idx': section_idx,
                        'length': len(current_chunk.strip()),
                        'metadata': {
                            'chunk_id': chunk_id,
                            'page_info': page_info,
                            'section_idx': section_idx,
                            'created_at': datetime.now().isoformat(),
                            'chunk_type': 'smart_paragraph'
                        }
                    })
                    chunk_id += 1

                # 오버랩 처리: 이전 청크의 끝부분을 새 청크 시작에 포함
                if overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                    current_chunk = overlap_text + '\n\n' + para
                else:
                    current_chunk = para

        # 남은 청크 저장
        if current_chunk.strip():
            chunks.append({
                'id': chunk_id,
                'text': current_chunk.strip(),
                'page_info': page_info,
                'section_idx': section_idx,
                'length': len(current_chunk.strip()),
                'metadata': {
                    'chunk_id': chunk_id,
                    'page_info': page_info,
                    'section_idx': section_idx,
                    'created_at': datetime.now().isoformat(),
                    'chunk_type': 'smart_paragraph'
                }
            })
            chunk_id += 1

    print(f"[INFO] 스마트 청킹 완료: {len(chunks)}개 청크 생성")
    return chunks

def create_embeddings_with_reranker(chunks: List[Dict],
                                   embedding_model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2',
                                   reranker_model_name: str = 'cross-encoder/ms-marco-MiniLM-L-12-v2',
                                   batch_size: int = 16) -> Tuple[np.ndarray, CrossEncoder]:
    """임베딩 생성 + 리랭커 모델 로드"""

    try:
        # GPU 사용 가능시 사용
        device = 'cuda' if torch.cuda.is_available() else 'cpu'

        # 1. 임베딩 모델 로드
        embedding_model = SentenceTransformer(embedding_model_name, device=device)
        print(f"[INFO] 임베딩 모델 로드 완료: {embedding_model_name} (device: {device})")

        # 2. 리랭커 모델 로드
        try:
            reranker_model = CrossEncoder(reranker_model_name, device=device)
            print(f"[INFO] 리랭커 모델 로드 완료: {reranker_model_name}")
        except Exception as e:
            print(f"[WARNING] 리랭커 모델 로드 실패, 다른 모델 시도: {str(e)}")
            # 대안 모델들
            fallback_models = [
                'cross-encoder/ms-marco-MiniLM-L-6-v2',
                'cross-encoder/ms-marco-TinyBERT-L-2-v2'
            ]
            reranker_model = None
            for fallback in fallback_models:
                try:
                    reranker_model = CrossEncoder(fallback, device=device)
                    print(f"[INFO] 대안 리랭커 모델 로드 완료: {fallback}")
                    break
                except:
                    continue

        texts = [chunk['text'] for chunk in chunks]
        all_embeddings = []

        # 3. 배치별 임베딩 생성
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            print(f"[INFO] 임베딩 배치 {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size} 처리 중... ({len(batch_texts)}개)")

            # 메모리 정리
            if i > 0:
                torch.cuda.empty_cache() if torch.cuda.is_available() else None

            try:
                batch_embeddings = embedding_model.encode(
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
                        emb = embedding_model.encode([text], convert_to_numpy=True)[0]
                        all_embeddings.append(emb)
                    except:
                        # 더미 임베딩 (문제가 있는 텍스트용)
                        emb = np.zeros(embedding_model.get_sentence_embedding_dimension())
                        all_embeddings.append(emb)

            time.sleep(0.1)  # 메모리 안정화

        embeddings_array = np.array(all_embeddings)
        print(f"[INFO] 임베딩 생성 완료: {embeddings_array.shape}")

        return embeddings_array, reranker_model

    except Exception as e:
        print(f"[ERROR] 임베딩 생성 실패: {str(e)}")
        return np.array([]), None

def process_multiple_pdfs(pdf_paths: List[str],
                         output_path: str = None) -> str:
    """여러 PDF 파일을 처리하여 통합 벡터스토어 생성"""

    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"enhanced_vectorstore_{timestamp}.pkl"

    print(f"[INFO] 통합 벡터스토어 생성 시작")
    print(f"[INFO] 처리할 PDF 파일 수: {len(pdf_paths)}")
    print(f"[INFO] 출력 경로: {output_path}")

    # 1. 모든 PDF에서 텍스트 추출
    print("\n[STEP 1] PDF 텍스트 추출...")
    all_text = ""
    source_info = []

    for pdf_path in pdf_paths:
        if not os.path.exists(pdf_path):
            print(f"[WARNING] 파일을 찾을 수 없음: {pdf_path}")
            continue

        text = extract_text_from_pdf_enhanced(pdf_path)
        if text:
            all_text += f"\n\n### SOURCE: {os.path.basename(pdf_path)} ###\n"
            all_text += text
            source_info.append({
                'path': pdf_path,
                'filename': os.path.basename(pdf_path),
                'text_length': len(text)
            })

    if not all_text:
        raise ValueError("모든 PDF에서 텍스트 추출에 실패했습니다.")

    # 2. 텍스트 정제
    print("\n[STEP 2] 텍스트 정제...")
    cleaned_text = enhanced_text_cleaning(all_text)

    # 3. 스마트 청킹
    print("\n[STEP 3] 스마트 청킹...")
    chunks = smart_chunking(cleaned_text, target_size=1200, overlap=150)  # 더 긴 청크

    if not chunks:
        raise ValueError("유효한 청크를 생성할 수 없습니다.")

    # 4. 임베딩 및 리랭커 생성
    print("\n[STEP 4] 임베딩 및 리랭커 생성...")
    embeddings, reranker = create_embeddings_with_reranker(chunks, batch_size=12)

    if len(embeddings) == 0:
        raise ValueError("임베딩 생성에 실패했습니다.")

    # 5. 벡터스토어 저장
    print("\n[STEP 5] 벡터스토어 저장...")

    vectorstore_data = {
        # 기본 데이터
        'documents': [chunk['text'] for chunk in chunks],
        'embeddings': embeddings,
        'metadatas': [chunk['metadata'] for chunk in chunks],
        'chunks': chunks,  # 상세 정보 포함

        # 메타 정보
        'source_files': source_info,
        'created_at': datetime.now().isoformat(),
        'model_name': 'paraphrase-multilingual-MiniLM-L12-v2',
        'embedding_dimension': embeddings.shape[1] if len(embeddings) > 0 else 0,
        'total_chunks': len(chunks),
        'total_documents': len(chunks),
        'chunk_strategy': 'smart_paragraph',
        'target_chunk_size': 1200,
        'overlap_size': 150,

        # 리랭커 정보 (모델 객체는 저장하지 않음)
        'has_reranker': reranker is not None,
        'reranker_model_name': reranker.model.name_or_path if reranker else None,

        # 품질 통계
        'avg_chunk_length': np.mean([len(chunk['text']) for chunk in chunks]),
        'min_chunk_length': min([len(chunk['text']) for chunk in chunks]),
        'max_chunk_length': max([len(chunk['text']) for chunk in chunks])
    }

    with open(output_path, 'wb') as f:
        pickle.dump(vectorstore_data, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"\n[SUCCESS] 통합 벡터스토어 저장 완료: {output_path}")
    print(f"[INFO] 총 {len(chunks)}개 청크, {embeddings.shape[1]}차원 임베딩")
    print(f"[INFO] 평균 청크 길이: {vectorstore_data['avg_chunk_length']:.0f}자")
    print(f"[INFO] 리랭커 포함: {'예' if reranker else '아니오'}")

    return output_path

def inspect_enhanced_vectorstore(pkl_path: str):
    """향상된 벡터스토어 내용 확인"""
    try:
        with open(pkl_path, 'rb') as f:
            data = pickle.load(f)

        print(f"\n=== 향상된 벡터스토어 정보 ===")
        print(f"파일: {pkl_path}")
        print(f"생성일: {data.get('created_at', 'N/A')}")
        print(f"청킹 전략: {data.get('chunk_strategy', 'N/A')}")
        print(f"타겟 청크 크기: {data.get('target_chunk_size', 'N/A')}자")
        print(f"오버랩 크기: {data.get('overlap_size', 'N/A')}자")
        print(f"리랭커 포함: {data.get('has_reranker', False)}")

        # 소스 파일 정보
        source_files = data.get('source_files', [])
        if source_files:
            print(f"\n=== 소스 파일 정보 ===")
            for src in source_files:
                print(f"• {src['filename']}: {src['text_length']:,}자")

        # 품질 통계
        print(f"\n=== 품질 통계 ===")
        print(f"총 청크 수: {data.get('total_chunks', 'N/A')}")
        print(f"평균 청크 길이: {data.get('avg_chunk_length', 0):.0f}자")
        print(f"최소 청크 길이: {data.get('min_chunk_length', 'N/A')}자")
        print(f"최대 청크 길이: {data.get('max_chunk_length', 'N/A')}자")

        # 샘플 내용 확인
        documents = data.get('documents', [])
        print(f"\n=== 샘플 내용 (상위 3개) ===")
        for i, doc in enumerate(documents[:3]):
            print(f"[{i+1}] 길이: {len(doc)}자")
            print(f"{doc[:200]}...")
            print("---")

        return True

    except Exception as e:
        print(f"[ERROR] 벡터스토어 확인 실패: {str(e)}")
        return False

if __name__ == "__main__":
    # 처리할 PDF 파일들
    pdf_files = [
        r"c:\jo(9.11.)\3. 지방자치단체의 재의·제소 조례 모음집(Ⅸ) (1).pdf",
        r"c:\jo(9.11.)\2022년_자치법규입안길라잡이.pdf"
    ]

    try:
        # 향상된 통합 벡터스토어 생성
        output_path = process_multiple_pdfs(pdf_files)

        # 생성된 벡터스토어 확인
        print("\n" + "="*60)
        inspect_enhanced_vectorstore(output_path)

    except Exception as e:
        print(f"[ERROR] 전체 프로세스 실패: {str(e)}")