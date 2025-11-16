"""
Gemini File Search API를 사용한 RAG 시스템
기존 pickle 기반 벡터스토어를 대체하는 모듈
"""

import os
import time
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
import streamlit as st


class GeminiFileSearchManager:
    """Gemini File Search API를 관리하는 클래스"""

    def __init__(self, api_key: str):
        """
        Args:
            api_key: Google Gemini API 키
        """
        self.client = genai.Client(api_key=api_key)
        self.store_name = None
        self.store_id = None

    def create_or_get_store(self, display_name: str = "조례-판례-법령-저장소") -> str:
        """
        검색 저장소를 생성하거나 기존 저장소를 가져옵니다.

        Args:
            display_name: 저장소 표시 이름

        Returns:
            저장소 이름 (리소스 경로)
        """
        try:
            # 기존 저장소 목록 확인
            stores = list(self.client.file_search_stores.list())

            # 같은 이름의 저장소가 있는지 확인
            for store in stores:
                if store.display_name == display_name:
                    self.store_name = store.name
                    self.store_id = store.name.split('/')[-1]
                    # print 제거 (Streamlit에서 표시)
                    return self.store_name

            # 없으면 새로 생성
            file_search_store = self.client.file_search_stores.create(
                config={'display_name': display_name}
            )
            self.store_name = file_search_store.name
            self.store_id = file_search_store.name.split('/')[-1]
            # print 제거 (Streamlit에서 표시)
            return self.store_name

        except Exception as e:
            # print 제거 (Streamlit에서 표시)
            raise

    def upload_file(self, file_path: str, display_name: Optional[str] = None) -> Dict[str, Any]:
        """
        파일을 File Search Store에 업로드합니다.

        Args:
            file_path: 업로드할 파일 경로
            display_name: 파일 표시 이름 (선택사항)

        Returns:
            업로드 작업 정보
        """
        if not self.store_name:
            raise ValueError("먼저 create_or_get_store()를 호출하여 저장소를 생성하세요.")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

        try:
            # print 제거

            # 파일 크기 확인
            file_size_mb = os.path.getsize(file_path) / 1024 / 1024
            print(f"   파일 크기: {file_size_mb:.1f} MB")

            # 한글 파일명 처리를 위한 영문 display_name 생성
            if display_name is None:
                base_name = os.path.basename(file_path)
                # 한글이 포함된 경우 간단한 영문명으로 변경
                name_mapping = {
                    "2022년_자치법규입안길라잡이.pdf": "2022_local_regulation_guide.pdf",
                    "3. 지방자치단체의 재의·제소 조례 모음집(Ⅸ) (1).pdf": "reconsideration_lawsuit_ordinance_collection.pdf",
                    "자치법규_Q&A (1).pdf": "local_regulation_qa.pdf",
                    "자치법규_쟁점_사전검토_지원_사례집 (1).pdf": "local_regulation_review_cases.pdf"
                }
                display_name = name_mapping.get(base_name, f"document_{hash(base_name) % 10000}.pdf")

            print(f"   표시 이름: {display_name}")

            # 파일을 바이트로 읽어서 업로드
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # 임시 파일명으로 업로드 (인코딩 문제 회피)
            import tempfile
            import shutil

            # 임시 디렉토리에 영문명으로 복사
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_file_path = os.path.join(temp_dir, display_name)
                shutil.copy2(file_path, temp_file_path)

                print(f"   임시 파일 생성: {temp_file_path}")

                # 임시 파일로 업로드
                operation = self.client.file_search_stores.upload_to_file_search_store(
                    file=temp_file_path,
                    file_search_store_name=self.store_name,
                    config={
                        'display_name': display_name,
                        'mime_type': 'application/pdf'
                    }
                )

            pass  # print(f"✅ 업로드 완료: {display_name}")
            return {
                'operation': operation,
                'file_path': file_path,
                'display_name': display_name
            }

        except Exception as e:
            pass  # print(f"❌ 파일 업로드 오류: {e}")
            raise

    def upload_multiple_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        여러 파일을 한번에 업로드합니다.

        Args:
            file_paths: 업로드할 파일 경로 리스트

        Returns:
            업로드 결과 리스트
        """
        results = []
        for file_path in file_paths:
            try:
                result = self.upload_file(file_path)
                results.append(result)
            except Exception as e:
                pass  # print(f"⚠️ {file_path} 업로드 실패: {e}")
                results.append({
                    'file_path': file_path,
                    'error': str(e)
                })
        return results

    def search(
        self,
        query: str,
        model: str = "gemini-2.5-flash",
        top_k: int = 5,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        File Search Store에서 검색을 수행합니다.

        Args:
            query: 검색 쿼리
            model: 사용할 Gemini 모델
            top_k: 반환할 최대 결과 수
            include_sources: 출처 정보 포함 여부

        Returns:
            검색 결과 딕셔너리
        """
        if not self.store_name:
            raise ValueError("먼저 create_or_get_store()를 호출하여 저장소를 생성하세요.")

        # 재시도 로직 (할당량 초과 시)
        max_retries = 3
        retry_delay = 10  # 초

        for attempt in range(max_retries):
            try:
                # File Search를 도구로 사용하여 검색 수행
                response = self.client.models.generate_content(
                    model=model,
                    contents=query,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(
                            fileSearch=types.FileSearch(
                                fileSearchStoreNames=[self.store_name],
                                topK=top_k
                            )
                        )],
                        temperature=0.1,  # 더 정확한 검색을 위해 낮은 온도 사용
                        max_output_tokens=8192,  # 출력 토큰 수 증가 (더 긴 응답)
                    )
                )

                # 성공하면 루프 탈출
                break

            except Exception as e:
                error_str = str(e)
                # 할당량 초과 오류인 경우
                if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                    if attempt < max_retries - 1:
                        pass  # print(f"⚠️  할당량 초과. {retry_delay}초 후 재시도... (시도 {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    else:
                        pass  # print(f"❌ 할당량 초과. 나중에 다시 시도하거나 다른 모델을 사용하세요.")
                        raise
                else:
                    # 다른 오류는 즉시 raise
                    raise

        try:
            result = {
                'query': query,
                'answer': response.text if response.text else "",
                'sources': []
            }

            # 출처 정보 추출
            if include_sources and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                    grounding = candidate.grounding_metadata

                    # 검색 지원 정보 추출
                    if hasattr(grounding, 'search_entry_point'):
                        search_queries = grounding.search_entry_point
                        result['search_queries'] = search_queries

                    # 인용 정보 추출
                    if hasattr(grounding, 'grounding_chunks'):
                        for chunk in grounding.grounding_chunks[:top_k]:
                            source_info = {
                                'text': chunk.text if hasattr(chunk, 'text') else "",
                            }

                            # 문서 정보 추출
                            if hasattr(chunk, 'retrieved_context'):
                                context = chunk.retrieved_context
                                if hasattr(context, 'uri'):
                                    source_info['uri'] = context.uri
                                if hasattr(context, 'title'):
                                    source_info['title'] = context.title

                            result['sources'].append(source_info)

            return result

        except Exception as e:
            pass  # print(f"❌ 검색 오류: {e}")
            raise

    def search_with_metadata_filter(
        self,
        query: str,
        metadata_filter: Dict[str, str],
        model: str = "gemini-2.5-flash"
    ) -> Dict[str, Any]:
        """
        메타데이터 필터를 적용한 검색을 수행합니다.

        Args:
            query: 검색 쿼리
            metadata_filter: 메타데이터 필터 (예: {'type': '판례'})
            model: 사용할 Gemini 모델

        Returns:
            검색 결과 딕셔너리
        """
        # 메타데이터 필터를 쿼리에 통합
        filter_text = " ".join([f"{k}:{v}" for k, v in metadata_filter.items()])
        enhanced_query = f"{filter_text} {query}"

        return self.search(enhanced_query, model=model)

    def list_files_in_store(self) -> List[Dict[str, Any]]:
        """
        저장소에 있는 파일 목록을 가져옵니다.

        Returns:
            파일 정보 리스트
        """
        if not self.store_name:
            raise ValueError("먼저 create_or_get_store()를 호출하여 저장소를 생성하세요.")

        try:
            # 저장소 정보 가져오기
            store = self.client.file_search_stores.get(name=self.store_name)

            # 파일 목록 정보 (API에 따라 다를 수 있음)
            files = []
            if hasattr(store, 'files'):
                for file in store.files:
                    file_info = {
                        'name': file.name if hasattr(file, 'name') else 'Unknown',
                        'display_name': file.display_name if hasattr(file, 'display_name') else 'Unknown',
                    }
                    files.append(file_info)

            return files

        except Exception as e:
            pass  # print(f"❌ 파일 목록 조회 오류: {e}")
            return []

    def delete_store(self) -> bool:
        """
        현재 저장소를 삭제합니다.

        Returns:
            삭제 성공 여부
        """
        if not self.store_name:
            print("삭제할 저장소가 없습니다.")
            return False

        try:
            self.client.file_search_stores.delete(name=self.store_name)
            pass  # print(f"✅ 저장소 삭제 완료: {self.store_name}")
            self.store_name = None
            self.store_id = None
            return True

        except Exception as e:
            pass  # print(f"❌ 저장소 삭제 오류: {e}")
            return False


def search_relevant_guidelines_gemini(
    query: str,
    api_key: str,
    store_manager: Optional[GeminiFileSearchManager] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Gemini File Search를 사용하여 관련 가이드라인을 검색합니다.
    기존 search_relevant_guidelines() 함수를 대체합니다.

    Args:
        query: 검색 쿼리
        api_key: Gemini API 키
        store_manager: GeminiFileSearchManager 인스턴스 (없으면 새로 생성)
        top_k: 반환할 최대 결과 수

    Returns:
        검색 결과 리스트 (기존 형식과 호환)
    """
    try:
        # Store Manager 생성 또는 사용
        if store_manager is None:
            store_manager = GeminiFileSearchManager(api_key)
            store_manager.create_or_get_store()

        # 시맨틱 검색 최적화: 의미와 맥락을 이해할 수 있는 자연어 질문으로 변환
        # Gemini File Search는 키워드 매칭이 아닌 의미 기반 검색을 수행
        import re

        # 법령명 추출 (맥락 제공용)
        law_pattern = r'([가-힣]+(?:법|조례|규칙|령))'
        laws_found = re.findall(law_pattern, query)

        # 자연어 질문 형태로 검색 쿼리 생성
        # 시맨틱 검색은 정보 요구를 명확하게 표현한 자연어 질문에서 최상의 성능 발휘
        if laws_found:
            # 법령명이 포함된 경우: 구체적인 맥락을 제공하는 질문
            primary_law = laws_found[0]
            if '위법' in query or '위반' in query:
                search_query = f"{primary_law}과 관련된 조례가 위법하다고 판단되어 재의 또는 제소된 사례와 판례를 찾아주세요. 어떤 조항이 문제가 되었고 상위법령에 어떻게 위배되었는지 설명된 자료를 찾아주세요."
            elif '판례' in query or '사례' in query:
                search_query = f"{primary_law}에 관련된 조례 제정 및 운영 사례, 판례, 법적 해석 자료를 찾아주세요."
            elif '기준' in query or '원칙' in query:
                search_query = f"{primary_law}과 관련된 조례 제정 및 심사 기준, 법적 원칙, 가이드라인을 찾아주세요."
            else:
                search_query = f"{primary_law}과 관련된 참고 자료, 판례, 해석 사례를 찾아주세요."
        else:
            # 법령명이 없는 경우: 일반적인 정보 요구로 표현
            if '위법' in query or '위반' in query:
                search_query = "조례가 상위법령에 위배되어 재의 또는 제소된 사례와 판례를 찾아주세요. 위법 판단 근거와 관련 조항을 포함한 자료를 찾아주세요."
            elif '판례' in query or '사례' in query:
                search_query = "조례 제정 및 운영과 관련된 판례와 사례를 찾아주세요."
            else:
                # 원본 쿼리가 이미 자연어 질문이면 그대로 사용
                search_query = query if len(query) > 20 else "조례 제정 및 심사와 관련된 법적 기준과 참고 자료를 찾아주세요."

        result = store_manager.search(search_query, top_k=top_k)

        # answer 필드에 검색 결과가 있음
        answer = result.get('answer', '')
        sources = result.get('sources', [])

        # 기존 형식과 호환되도록 변환
        # answer를 주요 텍스트로 사용하고, sources는 출처 정보로 활용
        formatted_results = []

        # 첫 번째 결과: answer 전체 내용
        if answer:
            source_files = [s.get('title', '') for s in sources if s.get('title')]
            formatted_results.append({
                'text': answer,
                'title': 'Gemini File Search',
                'source_store': 'Gemini File Search (통합 저장소)',
                'uri': '',
                'similarity': 0.95,
                'metadata': {
                    'source': 'gemini_file_search',
                    'source_files': source_files,
                    'model': 'gemini-2.5-flash'
                }
            })

        return formatted_results

    except Exception as e:
        pass  # print(f"❌ Gemini File Search 오류: {e}")
        return []


def search_violation_cases_gemini(
    ordinance_articles: List[str],
    api_key: str,
    store_manager: Optional[GeminiFileSearchManager] = None,
    max_results: int = 12
) -> List[Dict[str, Any]]:
    """
    조례 조항에 대한 위법성 판례를 Gemini File Search로 검색합니다.

    Args:
        ordinance_articles: 조례 조항 텍스트 리스트
        api_key: Gemini API 키
        store_manager: GeminiFileSearchManager 인스턴스
        max_results: 최대 결과 수

    Returns:
        판례 검색 결과 리스트
    """
    try:
        if store_manager is None:
            store_manager = GeminiFileSearchManager(api_key)
            store_manager.create_or_get_store()

        # 시맨틱 검색 쿼리 생성: 의미와 맥락을 담은 자연어 질문 형태
        # Gemini File Search는 정보 요구를 명확하게 표현한 질문에서 최상의 성능 발휘
        import re

        # 조례명 추출 (맥락 제공용)
        ordinance_name = ""
        if ordinance_articles:
            first_article = ordinance_articles[0]
            # "○○시 ○○ 조례" 패턴 찾기
            name_pattern = re.compile(r'([\w가-힣]+(?:시|도|군|구)\s+[\w가-힣\s]+조례)')
            match = name_pattern.search(first_article)
            if match:
                ordinance_name = match.group(1)

        # 주요 상위법령 추출 (맥락 제공용)
        referenced_laws = set()
        common_laws = ['지방자치법', '행정절차법', '도로교통법', '건축법', '환경법', '식품위생법',
                      '주차장법', '하수도법', '폐기물관리법', '소방기본법', '청소년보호법']
        for article in ordinance_articles[:10]:  # 상위 10개 조항 분석
            for law in common_laws:
                if law in article:
                    referenced_laws.add(law)

        # 조항 주제 추출 (제목에서)
        article_topics = []
        for article in ordinance_articles[:10]:
            # 제○조(제목) 형태에서 제목 추출
            if '조(' in article and ')' in article:
                title_match = re.search(r'조\(([^)]+)\)', article)
                if title_match:
                    topic = title_match.group(1)
                    # 일반적이지 않은 주제만 추가 (목적, 정의 등 제외)
                    if topic not in ['목적', '정의', '적용범위']:
                        article_topics.append(topic)

        # 자연어 질문 형태의 검색 쿼리 생성
        # 시맨틱 검색은 의미와 맥락을 이해하므로 구체적이고 명확한 질문이 효과적
        query_parts = []

        # 기본 질문 프레임
        base_question = "조례가 상위법령에 위배되어 위법하다고 판단되거나 재의·제소된 구체적인 사례와 판례를 찾아주세요."

        # 조례명이 있으면 구체적으로 언급
        if ordinance_name:
            query_parts.append(f"'{ordinance_name}'과 유사한 내용의 조례 중에서")

        # 참조된 상위법령이 있으면 언급
        if referenced_laws:
            laws_str = ', '.join(list(referenced_laws)[:3])  # 최대 3개
            query_parts.append(f"{laws_str}과 관련하여")

        # 주요 주제가 있으면 언급
        if article_topics:
            topics_str = ', '.join(article_topics[:3])  # 최대 3개
            query_parts.append(f"{topics_str}에 관한 규정에서")

        # 최종 쿼리 조합
        if query_parts:
            combined_query = ' '.join(query_parts) + ' ' + base_question
        else:
            combined_query = base_question

        # 추가 맥락 제공 (어떤 정보가 필요한지 명확히 설명)
        combined_query += "\n\n특히 다음 정보를 포함한 자료를 찾아주세요:"
        combined_query += "\n- 어떤 조항이 문제가 되었는지"
        combined_query += "\n- 어떤 상위법령(법률, 시행령 등)에 어떻게 위배되었는지"
        combined_query += "\n- 위법 판단의 근거와 이유"
        combined_query += "\n- 재의 또는 제소 결과"

        # 검색 수행
        result = store_manager.search(combined_query, top_k=max_results)

        # answer 필드에 검색 결과가 있음
        answer = result.get('answer', '')

        # sources 정보도 함께 활용
        sources = result.get('sources', [])
        source_titles = [s.get('title', '') for s in sources if s.get('title')]

        # 결과 반환 - Streamlit 앱이 기대하는 형식으로 변환
        formatted_results = [{
            'violation_type': '위법성 판례 및 제소 사례',
            'content': answer,
            'similarity': 0.95,
            'topic': '위법성 판례 및 제소 사례 (Gemini File Search)',
            'relevance_score': 0.95,
            'context_relevance': 0.90,
            'matched_concepts': ['위법', '제소', '판례'] if '위법' in answer else [],
            'summary': answer[:200] + '...' if len(answer) > 200 else answer,
            'metadata': {
                'source': 'gemini_file_search',
                'source_files': source_titles,
                'query': combined_query
            }
        }]

        return formatted_results

    except Exception as e:
        pass  # print(f"❌ 판례 검색 오류: {e}")
        return []


@st.cache_resource
def get_gemini_store_manager(api_key: str) -> GeminiFileSearchManager:
    """
    Streamlit 세션에서 재사용할 수 있도록 Store Manager를 캐싱합니다.

    Args:
        api_key: Gemini API 키

    Returns:
        GeminiFileSearchManager 인스턴스
    """
    manager = GeminiFileSearchManager(api_key)
    manager.create_or_get_store()
    return manager
