#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
벡터스토어 내용 뷰어
PKL 파일의 내용을 쉽게 확인할 수 있는 도구
"""

import pickle
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime
import re

def load_vectorstore_data(pkl_path):
    """벡터스토어 데이터 로드"""
    try:
        with open(pkl_path, 'rb') as f:
            data = pickle.load(f)
        return data
    except Exception as e:
        st.error(f"벡터스토어 로드 실패: {str(e)}")
        return None

def clean_text_for_display(text):
    """표시용 텍스트 정리"""
    # 너무 긴 공백 제거
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def main():
    st.set_page_config(
        page_title="벡터스토어 뷰어",
        page_icon="📚",
        layout="wide"
    )

    st.title("📚 벡터스토어 내용 뷰어")
    st.markdown("---")

    # 파일 경로
    pkl_path = r"c:\jo(9.11.)\enhanced_vectorstore_20250914_101739.pkl"

    # 데이터 로드
    with st.spinner("벡터스토어 로드 중..."):
        data = load_vectorstore_data(pkl_path)

    if data is None:
        st.stop()

    # 기본 정보 표시
    st.header("📊 기본 정보")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("총 문서 수", len(data.get('documents', [])))

    with col2:
        st.metric("임베딩 차원", data.get('embedding_dimension', 'N/A'))

    with col3:
        st.metric("모델", data.get('model_name', 'N/A'))

    with col4:
        created_at = data.get('created_at', 'N/A')
        if created_at != 'N/A':
            try:
                dt = datetime.fromisoformat(created_at)
                created_at = dt.strftime('%Y-%m-%d %H:%M')
            except:
                pass
        st.metric("생성일", created_at)

    st.markdown("---")

    # 탭으로 기능 분리
    tab1, tab2, tab3, tab4 = st.tabs(["📄 문서 목록", "🔍 검색", "📊 통계", "🔧 디버그"])

    with tab1:
        st.header("📄 문서 목록")

        documents = data.get('documents', [])
        metadatas = data.get('metadatas', [])
        chunks = data.get('chunks', [])

        if not documents:
            st.warning("문서가 없습니다.")
            return

        # 페이지네이션
        items_per_page = st.selectbox("페이지당 항목 수", [10, 25, 50, 100], index=1)
        total_pages = (len(documents) + items_per_page - 1) // items_per_page

        if total_pages > 1:
            page = st.number_input("페이지", min_value=1, max_value=total_pages, value=1) - 1
        else:
            page = 0

        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(documents))

        st.info(f"전체 {len(documents)}개 중 {start_idx + 1}-{end_idx}번째 표시")

        # 문서 목록 표시
        for i in range(start_idx, end_idx):
            with st.expander(f"📄 문서 {i + 1}", expanded=False):
                doc_text = clean_text_for_display(documents[i])

                # 메타데이터 정보
                if i < len(metadatas) and metadatas[i]:
                    metadata = metadatas[i]
                    col1, col2 = st.columns([1, 3])

                    with col1:
                        st.markdown("**📝 메타데이터:**")
                        for key, value in metadata.items():
                            st.markdown(f"• {key}: {value}")

                    with col2:
                        st.markdown("**📄 내용:**")
                        st.text_area("", doc_text, height=200, key=f"doc_{i}", disabled=True)
                else:
                    st.markdown("**📄 내용:**")
                    st.text_area("", doc_text, height=200, key=f"doc_{i}", disabled=True)

    with tab2:
        st.header("🔍 내용 검색")

        search_query = st.text_input("검색어 입력")
        search_type = st.selectbox("검색 방식", ["단어 포함", "정규식"])

        if search_query:
            documents = data.get('documents', [])
            results = []

            with st.spinner("검색 중..."):
                for i, doc in enumerate(documents):
                    try:
                        if search_type == "단어 포함":
                            if search_query.lower() in doc.lower():
                                # 검색어 주변 텍스트 추출
                                idx = doc.lower().find(search_query.lower())
                                start = max(0, idx - 100)
                                end = min(len(doc), idx + len(search_query) + 100)
                                context = doc[start:end]
                                results.append((i, context, doc))

                        elif search_type == "정규식":
                            if re.search(search_query, doc, re.IGNORECASE):
                                match = re.search(search_query, doc, re.IGNORECASE)
                                start = max(0, match.start() - 100)
                                end = min(len(doc), match.end() + 100)
                                context = doc[start:end]
                                results.append((i, context, doc))

                    except Exception as e:
                        continue

            if results:
                st.success(f"🎯 {len(results)}개 결과 발견")

                for i, (doc_idx, context, full_doc) in enumerate(results):
                    with st.expander(f"검색 결과 {i + 1} (문서 {doc_idx + 1})", expanded=False):
                        # 검색어 하이라이트
                        if search_type == "단어 포함":
                            highlighted = context.replace(
                                search_query,
                                f"**🔍{search_query}🔍**"
                            )
                        else:
                            highlighted = context

                        st.markdown("**🔍 검색 결과 (주변 텍스트):**")
                        st.markdown(highlighted)

                        if st.button(f"전체 내용 보기", key=f"full_{i}"):
                            st.markdown("**📄 전체 문서:**")
                            st.text_area("", full_doc, height=400, key=f"full_doc_{i}", disabled=True)
            else:
                st.warning("검색 결과가 없습니다.")

    with tab3:
        st.header("📊 통계 정보")

        documents = data.get('documents', [])
        embeddings = data.get('embeddings', np.array([]))

        if documents:
            # 문서 길이 통계
            doc_lengths = [len(doc) for doc in documents]

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📏 문서 길이 통계")
                df_lengths = pd.DataFrame({
                    '통계': ['최소 길이', '최대 길이', '평균 길이', '중간값'],
                    '문자 수': [
                        min(doc_lengths),
                        max(doc_lengths),
                        int(np.mean(doc_lengths)),
                        int(np.median(doc_lengths))
                    ]
                })
                st.dataframe(df_lengths, use_container_width=True)

            with col2:
                st.subheader("📊 길이 분포")
                # 히스토그램 데이터
                bins = [0, 100, 300, 500, 1000, max(doc_lengths)]
                bin_labels = ['0-100', '100-300', '300-500', '500-1000', '1000+']
                counts = []

                for i in range(len(bins) - 1):
                    count = sum(1 for length in doc_lengths if bins[i] <= length < bins[i+1])
                    counts.append(count)

                df_dist = pd.DataFrame({
                    '길이 범위': bin_labels,
                    '문서 수': counts
                })
                st.dataframe(df_dist, use_container_width=True)

        # 키워드 분석
        if documents:
            st.subheader("🔍 주요 키워드 분석")

            # 간단한 키워드 추출
            all_text = ' '.join(documents[:100])  # 처음 100개만 분석

            keywords = ['조례', '법률', '규정', '위반', '위법', '허가', '승인', '사무', '권한',
                       '기관위임', '재의', '제소', '의결', '대법원', '판례', '헌법', '시장', '군수']

            keyword_counts = {}
            for keyword in keywords:
                count = all_text.lower().count(keyword.lower())
                if count > 0:
                    keyword_counts[keyword] = count

            if keyword_counts:
                df_keywords = pd.DataFrame(list(keyword_counts.items()),
                                         columns=['키워드', '빈도'])
                df_keywords = df_keywords.sort_values('빈도', ascending=False)
                st.dataframe(df_keywords, use_container_width=True)

    with tab4:
        st.header("🔧 디버그 정보")

        st.subheader("📋 데이터 구조")
        st.code(f"키 목록: {list(data.keys())}")

        for key, value in data.items():
            if key in ['documents', 'embeddings', 'chunks']:
                st.code(f"{key}: {type(value)} (길이: {len(value)})")
            else:
                st.code(f"{key}: {type(value)} = {value}")

        # 임베딩 정보
        embeddings = data.get('embeddings', np.array([]))
        if len(embeddings) > 0:
            st.subheader("🧮 임베딩 정보")
            st.code(f"Shape: {embeddings.shape}")
            st.code(f"데이터 타입: {embeddings.dtype}")
            st.code(f"첫 번째 임베딩 샘플 (처음 10개 값): {embeddings[0][:10]}")

        # 원시 데이터 샘플
        st.subheader("🔍 원시 데이터 샘플")

        if st.button("첫 번째 문서 원시 데이터 보기"):
            if data.get('documents'):
                st.code(repr(data['documents'][0]))

        if st.button("전체 데이터 구조 보기"):
            st.json({k: str(type(v)) for k, v in data.items()})

if __name__ == "__main__":
    main()