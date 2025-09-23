# Phase 3: RAG 기반 지자체 정보 시스템 설계서

## 🎯 목적 및 범위

### 핵심 목적
사용자의 위치(시군구) 정보를 기반으로 **RAG(Retrieval-Augmented Generation) 검색을 통해 정확하고 최신의 지자체별 대형폐기물 배출 정보**를 실시간으로 제공

### 비즈니스 가치
- **정보 정확도 혁신**: 실시간 공식 자료 기반 정보 제공
- **지역 맞춤형 서비스**: 사용자 위치별 맞춤 안내 (수수료, 배출일자)
- **서비스 차별화**: 단순 검색이 아닌 지능형 정보 조회
- **유지보수 효율화**: 자동 문서 인덱싱으로 정보 업데이트 부담 감소

### 구현 범위
- ✅ ChromaDB 기반 벡터 검색 엔진
- ✅ 지자체 문서 자동 인덱싱 시스템
- ✅ 수수료 정보 실시간 조회
- ✅ 동별 배출일자 정보 제공
- ✅ 컨텍스트 기반 응답 생성
- ✅ 검색 품질 최적화

## 🔗 기존 시스템 연계점

### 주요 의존성 (최소화)
```python
# 기존 시스템 활용
- DistrictService: 행정구역 코드 매핑
- OpenAIService: 응답 생성 (선택적)
- 기본 웹 크롤링 인프라

# 새로운 의존성
- ChromaDB: 벡터 검색
- SentenceTransformers: 한국어 임베딩
```

### 완전 독립 실행 가능
```python
# 다른 Phase 없이도 완전한 가치 제공
- 기존 VisionService 결과와 연동
- 단독으로도 지자체 정보 조회 서비스 가능
```

## 🏗️ 시스템 아키텍처

### 컴포넌트 구조
```
src/
├── domains/
│   └── district/
│       └── services/
│           ├── rag_search_service.py        # RAG 검색 엔진
│           ├── document_indexer_service.py  # 문서 인덱싱 관리
│           ├── district_rag_service.py      # 지자체 RAG 통합
│           └── fee_schedule_service.py      # 수수료 정보 관리
└── pages/
    └── district_info_search.py              # 지자체 정보 검색 페이지 (선택적)
```

### RAG 시스템 플로우
```
사용자 쿼리
    ↓
Query Enhancement (쿼리 확장 및 개선)
    ↓
ChromaDB Vector Search (벡터 유사도 검색)
    ↓
Context Window Building (관련 문서 조합)
    ↓
Response Generation (LLM 응답 생성)
    ↓
Quality Verification (응답 품질 검증)
    ↓
최종 답변 제공
```

### 데이터 플로우
```
지자체 웹사이트
    ↓
Document Crawler (문서 수집)
    ↓
Document Processor (전처리 및 청킹)
    ↓
Embedding Generation (임베딩 생성)
    ↓
ChromaDB Storage (벡터 저장)
    ↓
검색 준비 완료
```

## 📋 세부 기능 설계

### 1. RAGSearchService (핵심 검색 엔진)

```python
# src/domains/district/services/rag_search_service.py
from src.app.core.base_service import BaseService
import chromadb
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Optional, Any
import re

class RAGSearchService(BaseService):
    """RAG 기반 지자체 정보 검색 서비스"""

    def __init__(self, config):
        super().__init__(config)

        # ChromaDB 클라이언트 초기화
        self.chroma_client = chromadb.PersistentClient(
            path=config.get('chromadb_path', './data/chromadb')
        )

        # 한국어 임베딩 모델 초기화
        self.embedding_model = SentenceTransformer('jhgan/ko-sroberta-multitask')

        # 컬렉션 초기화
        self.collection = self._get_or_create_collection('district_documents')

        self.logger.info("RAGSearchService initialized with ChromaDB")

    def _get_or_create_collection(self, name: str):
        """ChromaDB 컬렉션 가져오기 또는 생성"""
        try:
            return self.chroma_client.get_collection(name)
        except:
            return self.chroma_client.create_collection(
                name=name,
                metadata={"description": "District waste management documents"}
            )

    def search_district_info(self,
                           query: str,
                           district_code: str,
                           item_category: str = None,
                           top_k: int = 5) -> Dict[str, Any]:
        """지자체 정보 검색 (메인 인터페이스)"""

        try:
            # 1. 쿼리 전처리 및 확장
            enhanced_query = self._enhance_query(query, district_code, item_category)

            # 2. 벡터 검색 실행
            search_results = self._vector_search(enhanced_query, district_code, top_k)

            # 3. 검색 결과 후처리
            processed_results = self._process_search_results(search_results)

            # 4. 컨텍스트 윈도우 구성
            context_window = self._build_context_window(processed_results)

            # 5. 신뢰도 계산
            confidence_score = self._calculate_search_confidence(processed_results)

            return {
                'success': True,
                'query': query,
                'enhanced_query': enhanced_query,
                'context_window': context_window,
                'retrieved_documents': processed_results,
                'confidence_score': confidence_score,
                'search_metadata': {
                    'district_code': district_code,
                    'item_category': item_category,
                    'total_results': len(search_results),
                    'search_time': None  # 구현 시 추가
                }
            }

        except Exception as e:
            self.logger.error(f"Search failed for query '{query}': {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query
            }

    def _enhance_query(self, query: str, district_code: str, item_category: str = None) -> str:
        """쿼리 향상 및 확장"""

        enhanced_parts = [query]

        # 지자체 정보 추가
        if district_code:
            district_name = self._get_district_name(district_code)
            if district_name:
                enhanced_parts.append(district_name)

        # 아이템 카테고리 추가
        if item_category:
            enhanced_parts.append(item_category)
            # 유사 카테고리 추가
            similar_categories = self._get_similar_categories(item_category)
            enhanced_parts.extend(similar_categories[:2])  # 최대 2개

        # 도메인 특화 키워드 추가
        domain_keywords = self._get_domain_keywords(query)
        enhanced_parts.extend(domain_keywords)

        enhanced_query = ' '.join(enhanced_parts)

        self.logger.debug(f"Query enhanced: '{query}' → '{enhanced_query}'")
        return enhanced_query

    def _vector_search(self, query: str, district_code: str, top_k: int) -> List[Dict]:
        """ChromaDB 벡터 검색"""

        # 검색 필터 구성
        where_filter = {"district_code": district_code} if district_code else None

        # 벡터 검색 실행
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter,
            include=['documents', 'metadatas', 'distances']
        )

        # 결과 정규화
        search_results = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                search_results.append({
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i],
                    'similarity': 1 - results['distances'][0][i]  # 유사도 계산
                })

        return search_results

    def _process_search_results(self, raw_results: List[Dict]) -> List[Dict]:
        """검색 결과 후처리 및 품질 개선"""

        processed = []

        for result in raw_results:
            # 중복 제거
            if self._is_duplicate_content(result['content'], processed):
                continue

            # 관련도 검증
            if result['similarity'] < 0.3:  # 임계값 이하 제외
                continue

            # 메타데이터 보강
            enhanced_metadata = self._enhance_metadata(result['metadata'])

            processed_result = {
                'content': result['content'],
                'metadata': enhanced_metadata,
                'similarity': result['similarity'],
                'relevance_score': self._calculate_relevance_score(result),
                'source_info': {
                    'url': enhanced_metadata.get('source_url', ''),
                    'last_updated': enhanced_metadata.get('last_updated', ''),
                    'document_type': enhanced_metadata.get('document_type', 'general')
                }
            }

            processed.append(processed_result)

        # 관련도 점수로 재정렬
        processed.sort(key=lambda x: x['relevance_score'], reverse=True)

        return processed

    def _build_context_window(self, results: List[Dict]) -> str:
        """컨텍스트 윈도우 구성"""

        if not results:
            return "관련 정보를 찾을 수 없습니다."

        context_parts = []
        total_length = 0
        max_context_length = 2000  # 토큰 제한

        for result in results:
            content = result['content']
            source_info = f"[출처: {result['source_info']['url']}]" if result['source_info']['url'] else ""

            formatted_content = f"{content}\n{source_info}\n"

            if total_length + len(formatted_content) > max_context_length:
                break

            context_parts.append(formatted_content)
            total_length += len(formatted_content)

        return "\n---\n".join(context_parts)

    def _calculate_search_confidence(self, results: List[Dict]) -> float:
        """검색 신뢰도 계산"""

        if not results:
            return 0.0

        # 최고 유사도 점수
        max_similarity = max(r['similarity'] for r in results)

        # 결과 개수 점수
        count_score = min(len(results) / 3, 1.0)  # 3개 이상이면 최대점

        # 소스 다양성 점수
        unique_sources = len(set(r['source_info']['url'] for r in results))
        diversity_score = min(unique_sources / 2, 1.0)  # 2개 이상 소스면 최대점

        # 가중 평균
        confidence = (max_similarity * 0.5 + count_score * 0.3 + diversity_score * 0.2)

        return round(confidence, 3)

    def _get_similar_categories(self, category: str) -> List[str]:
        """유사 카테고리 반환"""

        category_groups = {
            '의자': ['chair', '좌석', '의자류'],
            '테이블': ['table', '탁자', '책상', '테이블류'],
            '소파': ['sofa', '쇼파', '소파류', '의자'],
            '침대': ['bed', '매트리스', '침구류'],
            '냉장고': ['refrigerator', '냉동고', '가전제품'],
            '세탁기': ['washing machine', '세탁기계', '가전제품'],
            '에어컨': ['air conditioner', 'AC', '가전제품']
        }

        return category_groups.get(category, [])

    def _get_domain_keywords(self, query: str) -> List[str]:
        """도메인 특화 키워드 추출"""

        keywords = []

        # 수수료 관련
        if any(word in query for word in ['수수료', '요금', '비용', '가격']):
            keywords.extend(['수수료', '요금표', '비용'])

        # 배출일자 관련
        if any(word in query for word in ['배출', '버리는', '언제', '요일', '일정']):
            keywords.extend(['배출일자', '수거일', '요일'])

        # 신청 관련
        if any(word in query for word in ['신청', '접수', '예약']):
            keywords.extend(['신청방법', '접수', '예약'])

        return keywords
```

### 2. DocumentIndexerService (문서 인덱싱 관리)

```python
# src/domains/district/services/document_indexer_service.py
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict
import hashlib
import time

class DocumentIndexerService(BaseService):
    """지자체 문서 수집 및 인덱싱 서비스"""

    def __init__(self, config):
        super().__init__(config)
        self.rag_service = None  # lazy loading

    def index_district_documents(self, district_code: str, urls: List[str]) -> Dict[str, Any]:
        """지자체 문서 인덱싱 (메인 인터페이스)"""

        indexing_result = {
            'district_code': district_code,
            'total_urls': len(urls),
            'successful_indexes': 0,
            'failed_indexes': 0,
            'indexed_documents': [],
            'errors': []
        }

        for url in urls:
            try:
                # 1. 문서 다운로드
                content = self._download_document(url)
                if not content:
                    indexing_result['errors'].append(f"Failed to download: {url}")
                    indexing_result['failed_indexes'] += 1
                    continue

                # 2. 문서 전처리
                processed_chunks = self._process_document(content, url, district_code)
                if not processed_chunks:
                    indexing_result['errors'].append(f"No valid content: {url}")
                    indexing_result['failed_indexes'] += 1
                    continue

                # 3. ChromaDB에 저장
                storage_result = self._store_in_chromadb(processed_chunks)
                if storage_result['success']:
                    indexing_result['successful_indexes'] += 1
                    indexing_result['indexed_documents'].append({
                        'url': url,
                        'chunks_count': len(processed_chunks),
                        'document_id': storage_result['document_id']
                    })
                else:
                    indexing_result['failed_indexes'] += 1
                    indexing_result['errors'].append(f"Storage failed for {url}: {storage_result['error']}")

                # 요청 간격 (서버 부하 방지)
                time.sleep(1)

            except Exception as e:
                indexing_result['failed_indexes'] += 1
                indexing_result['errors'].append(f"Error processing {url}: {str(e)}")

        return indexing_result

    def _download_document(self, url: str) -> str:
        """웹 문서 다운로드"""

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # 인코딩 처리
            if response.encoding:
                response.encoding = 'utf-8'

            return response.text

        except Exception as e:
            self.logger.error(f"Failed to download {url}: {e}")
            return ""

    def _process_document(self, html_content: str, url: str, district_code: str) -> List[Dict]:
        """HTML 문서 전처리 및 청킹"""

        # 1. HTML 파싱 및 텍스트 추출
        soup = BeautifulSoup(html_content, 'html.parser')

        # 불필요한 태그 제거
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()

        # 메인 컨텐츠 추출
        main_content = self._extract_main_content(soup)
        if not main_content:
            return []

        # 2. 텍스트 정제
        cleaned_text = self._clean_text(main_content)
        if len(cleaned_text) < 100:  # 너무 짧은 문서 제외
            return []

        # 3. 의미 단위 청킹
        chunks = self._semantic_chunking(cleaned_text, max_chunk_size=500)

        # 4. 각 청크에 메타데이터 추가
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 50:  # 너무 짧은 청크 제외
                continue

            chunk_data = {
                'content': chunk,
                'metadata': {
                    'district_code': district_code,
                    'source_url': url,
                    'chunk_index': i,
                    'document_type': self._classify_document_type(chunk, url),
                    'last_updated': self._extract_last_updated(soup),
                    'content_hash': hashlib.md5(chunk.encode()).hexdigest()
                },
                'id': f"{district_code}_{hashlib.md5(url.encode()).hexdigest()[:8]}_{i}"
            }

            processed_chunks.append(chunk_data)

        return processed_chunks

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """메인 컨텐츠 추출"""

        # 우선순위별로 컨텐츠 영역 찾기
        content_selectors = [
            'main',
            '.content',
            '.main-content',
            '#content',
            '#main',
            'article',
            '.post-content',
            '.entry-content'
        ]

        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                return content_area.get_text(strip=True)

        # 특정 영역을 찾지 못한 경우 body 전체 사용
        body = soup.find('body')
        return body.get_text(strip=True) if body else soup.get_text(strip=True)

    def _clean_text(self, text: str) -> str:
        """텍스트 정제"""

        # 연속된 공백 제거
        text = re.sub(r'\s+', ' ', text)

        # 특수문자 정리
        text = re.sub(r'[^\w\s가-힣.,!?():-]', ' ', text)

        # 연속된 구두점 정리
        text = re.sub(r'([.!?]){2,}', r'\1', text)

        return text.strip()

    def _semantic_chunking(self, text: str, max_chunk_size: int) -> List[str]:
        """의미 단위 기반 청킹"""

        # 문장 단위 분할
        sentences = re.split(r'[.!?]\s+', text)

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_length = len(sentence)

            # 청크 크기 초과 시 새 청크 시작
            if current_length + sentence_length > max_chunk_size and current_chunk:
                chunks.append('. '.join(current_chunk) + '.')
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length

        # 마지막 청크 추가
        if current_chunk:
            chunks.append('. '.join(current_chunk) + '.')

        return chunks

    def _classify_document_type(self, content: str, url: str) -> str:
        """문서 타입 분류"""

        # URL 기반 분류
        if 'fee' in url or '수수료' in url:
            return 'fee_schedule'
        elif 'schedule' in url or '일정' in url or '요일' in url:
            return 'pickup_schedule'
        elif 'guide' in url or '안내' in url:
            return 'guide'

        # 내용 기반 분류
        if any(keyword in content for keyword in ['수수료', '요금', '비용']):
            return 'fee_schedule'
        elif any(keyword in content for keyword in ['배출일', '수거일', '요일']):
            return 'pickup_schedule'
        elif any(keyword in content for keyword in ['신청', '접수', '방법']):
            return 'application_guide'

        return 'general'

    def _store_in_chromadb(self, chunks: List[Dict]) -> Dict[str, Any]:
        """ChromaDB에 청크 저장"""

        if not self.rag_service:
            self.rag_service = self.get_service('rag_search_service')

        try:
            # 임베딩 생성
            contents = [chunk['content'] for chunk in chunks]
            embeddings = self.rag_service.embedding_model.encode(contents).tolist()

            # ChromaDB에 저장
            ids = [chunk['id'] for chunk in chunks]
            metadatas = [chunk['metadata'] for chunk in chunks]

            self.rag_service.collection.add(
                ids=ids,
                documents=contents,
                metadatas=metadatas,
                embeddings=embeddings
            )

            return {
                'success': True,
                'document_id': chunks[0]['id'].split('_')[1],  # 문서 ID 추출
                'chunks_stored': len(chunks)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def update_district_index(self, district_code: str) -> Dict[str, Any]:
        """특정 지자체 인덱스 업데이트"""

        # 지자체별 URL 목록 가져오기
        urls = self._get_district_urls(district_code)

        if not urls:
            return {
                'success': False,
                'error': f'No URLs found for district {district_code}'
            }

        # 기존 데이터 삭제 (선택적)
        self._remove_existing_documents(district_code)

        # 새로운 문서 인덱싱
        result = self.index_district_documents(district_code, urls)

        return result

    def _get_district_urls(self, district_code: str) -> List[str]:
        """지자체별 URL 목록 조회"""

        # 실제 구현에서는 데이터베이스나 설정 파일에서 읽어옴
        district_urls = {
            '11110': [  # 종로구
                'https://jongno.go.kr/waste-info',
                'https://jongno.go.kr/large-waste-fee'
            ],
            '11140': [  # 중구
                'https://junggu.seoul.kr/waste-guide',
                'https://junggu.seoul.kr/fee-schedule'
            ]
            # 추가 지자체...
        }

        return district_urls.get(district_code, [])
```

### 3. DistrictRAGService (통합 서비스)

```python
# src/domains/district/services/district_rag_service.py
class DistrictRAGService(BaseService):
    """지자체 RAG 통합 서비스 (메인 인터페이스)"""

    def __init__(self, config):
        super().__init__(config)
        self.rag_search = None  # lazy loading
        self.openai_service = None  # lazy loading

    def get_district_guidance(self,
                            user_query: str,
                            district_code: str,
                            item_info: Dict = None,
                            context: Dict = None) -> Dict[str, Any]:
        """지자체별 맞춤 안내 생성 (메인 API)"""

        try:
            # 1. RAG 검색 실행
            search_result = self._get_rag_search_service().search_district_info(
                query=user_query,
                district_code=district_code,
                item_category=item_info.get('category') if item_info else None
            )

            if not search_result['success']:
                return self._create_fallback_response(user_query, district_code)

            # 2. 컨텍스트 기반 응답 생성
            if self._should_use_llm(search_result['confidence_score']):
                response = self._generate_llm_response(
                    user_query, search_result, item_info, context
                )
            else:
                response = self._generate_template_response(search_result)

            # 3. 응답 품질 검증
            validated_response = self._validate_response_quality(response, search_result)

            return {
                'success': True,
                'response': validated_response['text'],
                'confidence': search_result['confidence_score'],
                'sources': self._format_sources(search_result['retrieved_documents']),
                'metadata': {
                    'district_code': district_code,
                    'search_confidence': search_result['confidence_score'],
                    'response_type': validated_response['type'],
                    'sources_count': len(search_result['retrieved_documents'])
                }
            }

        except Exception as e:
            self.logger.error(f"District guidance generation failed: {e}")
            return self._create_error_response(str(e))

    def _generate_llm_response(self,
                             query: str,
                             search_result: Dict,
                             item_info: Dict,
                             context: Dict) -> Dict[str, Any]:
        """LLM 기반 응답 생성"""

        # 프롬프트 구성
        system_prompt = """당신은 대형폐기물 배출 안내 전문가입니다.
제공된 공식 자료를 바탕으로 정확하고 실용적인 안내를 제공해주세요.

규칙:
1. 공식 자료에 없는 정보는 추측하지 마세요
2. 수수료와 배출일자는 정확히 안내해주세요
3. 불확실한 경우 관련 기관 문의를 안내해주세요
4. 친근하고 이해하기 쉽게 설명해주세요"""

        user_prompt = f"""
질문: {query}

공식 자료:
{search_result['context_window']}

물건 정보: {item_info.get('category', '정보 없음')} (크기: {item_info.get('size', '정보 없음')})

위 정보를 바탕으로 사용자에게 도움이 되는 안내를 제공해주세요.
"""

        # OpenAI API 호출
        openai_service = self._get_openai_service()
        llm_response = openai_service.generate_response(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=800,
            temperature=0.3
        )

        return {
            'text': llm_response,
            'type': 'llm_generated',
            'prompt_used': user_prompt
        }

    def _generate_template_response(self, search_result: Dict) -> Dict[str, Any]:
        """템플릿 기반 응답 생성 (LLM 미사용)"""

        # 검색 결과에서 핵심 정보 추출
        key_info = self._extract_key_information(search_result['retrieved_documents'])

        # 템플릿 기반 응답 구성
        response_parts = []

        if key_info['fees']:
            response_parts.append(f"💰 수수료: {key_info['fees']}")

        if key_info['schedule']:
            response_parts.append(f"📅 배출일자: {key_info['schedule']}")

        if key_info['application']:
            response_parts.append(f"📋 신청방법: {key_info['application']}")

        if key_info['contact']:
            response_parts.append(f"📞 문의처: {key_info['contact']}")

        if not response_parts:
            response_text = "죄송합니다. 해당 지역의 구체적인 정보를 찾을 수 없습니다. 관할 구청에 직접 문의해주시기 바랍니다."
        else:
            response_text = "\n\n".join(response_parts)

        return {
            'text': response_text,
            'type': 'template_based',
            'extracted_info': key_info
        }

    def _extract_key_information(self, documents: List[Dict]) -> Dict[str, str]:
        """문서에서 핵심 정보 추출"""

        key_info = {
            'fees': '',
            'schedule': '',
            'application': '',
            'contact': ''
        }

        for doc in documents:
            content = doc['content']

            # 수수료 정보 추출
            fee_match = re.search(r'수수료[:\s]*([0-9,]+원)', content)
            if fee_match and not key_info['fees']:
                key_info['fees'] = fee_match.group(1)

            # 배출일자 정보 추출
            schedule_patterns = [
                r'(월요일|화요일|수요일|목요일|금요일|토요일|일요일)',
                r'매주\s*([월화수목금토일])',
                r'([월화수목금토일]요일)'
            ]
            for pattern in schedule_patterns:
                schedule_match = re.search(pattern, content)
                if schedule_match and not key_info['schedule']:
                    key_info['schedule'] = schedule_match.group(0)
                    break

            # 연락처 정보 추출
            contact_match = re.search(r'(\d{2,3}-\d{3,4}-\d{4})', content)
            if contact_match and not key_info['contact']:
                key_info['contact'] = contact_match.group(1)

        return key_info

    def batch_update_all_districts(self) -> Dict[str, Any]:
        """전체 지자체 인덱스 일괄 업데이트"""

        # 등록된 모든 지자체 코드 가져오기
        district_codes = self._get_registered_districts()

        results = {
            'total_districts': len(district_codes),
            'successful_updates': 0,
            'failed_updates': 0,
            'update_details': {}
        }

        indexer_service = self.get_service('document_indexer_service')

        for district_code in district_codes:
            try:
                update_result = indexer_service.update_district_index(district_code)

                if update_result.get('successful_indexes', 0) > 0:
                    results['successful_updates'] += 1
                else:
                    results['failed_updates'] += 1

                results['update_details'][district_code] = update_result

            except Exception as e:
                results['failed_updates'] += 1
                results['update_details'][district_code] = {
                    'success': False,
                    'error': str(e)
                }

        return results
```

## 🗄️ 데이터베이스 스키마 (최소한)

### ChromaDB 보조 메타데이터만 PostgreSQL에 저장

```sql
-- RAG 문서 메타데이터 테이블 (ChromaDB 참조용)
CREATE TABLE rag_document_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- ChromaDB 참조 정보
    chroma_collection_name TEXT DEFAULT 'district_documents',
    chroma_document_id TEXT NOT NULL,

    -- 지자체 정보
    district_code TEXT NOT NULL,
    district_name TEXT,

    -- 문서 정보
    source_url TEXT NOT NULL,
    document_type TEXT, -- 'fee_schedule', 'pickup_schedule', 'guide', 'general'
    last_crawled TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content_hash TEXT, -- 변경 감지용

    -- 품질 정보
    chunk_count INTEGER DEFAULT 0,
    avg_chunk_quality FLOAT DEFAULT 0.0,

    -- 상태
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(district_code, source_url)
);

-- 검색 쿼리 로그 (성능 개선용)
CREATE TABLE rag_search_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    query_text TEXT NOT NULL,
    district_code TEXT,
    item_category TEXT,

    -- 검색 결과
    results_count INTEGER DEFAULT 0,
    confidence_score FLOAT DEFAULT 0.0,
    search_time_ms INTEGER DEFAULT 0,

    -- 사용자 피드백 (선택적)
    user_rating INTEGER, -- 1-5
    user_session_id TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_rag_metadata_district ON rag_document_metadata(district_code);
CREATE INDEX idx_rag_metadata_active ON rag_document_metadata(is_active);
CREATE INDEX idx_rag_logs_district ON rag_search_logs(district_code);
CREATE INDEX idx_rag_logs_created ON rag_search_logs(created_at);
```

## 🚀 구현 가이드

### 1단계: ChromaDB 환경 구축 (1일)

```bash
# 1. ChromaDB 설치
pip install chromadb sentence-transformers

# 2. 데이터 디렉토리 생성
mkdir -p data/chromadb

# 3. 기본 테스트
python -c "import chromadb; print('ChromaDB 설치 성공')"
```

### 2단계: 기본 RAG 검색 구현 (2-3일)

```python
# ServiceFactory에 RAG 서비스 등록
registry.register_service(
    name='rag_search_service',
    service_class=type('RAGSearchService', (), {}),
    module_path='src.domains.district.services.rag_search_service',
    dependencies=[],
    is_optional=False,
    singleton=True
)

registry.register_service(
    name='district_rag_service',
    service_class=type('DistrictRAGService', (), {}),
    module_path='src.domains.district.services.district_rag_service',
    dependencies=['rag_search_service'],
    is_optional=False,
    singleton=True
)
```

### 3단계: 문서 인덱싱 시스템 구현 (2-3일)

```python
# 초기 데이터 인덱싱 스크립트
# scripts/initial_indexing.py

from src.domains.district.services.document_indexer_service import DocumentIndexerService

def initial_setup():
    """초기 지자체 문서 인덱싱"""

    indexer = DocumentIndexerService()

    # 주요 지자체 URL 등록 및 인덱싱
    districts = {
        '11110': ['https://jongno.go.kr/waste-info'],  # 종로구
        '11140': ['https://junggu.seoul.kr/waste-guide']  # 중구
    }

    for district_code, urls in districts.items():
        print(f"Indexing {district_code}...")
        result = indexer.index_district_documents(district_code, urls)
        print(f"Success: {result['successful_indexes']}, Failed: {result['failed_indexes']}")

if __name__ == "__main__":
    initial_setup()
```

### 4단계: 기존 시스템 통합 (2-3일)

```python
# 기존 이미지 분석 플로우에 RAG 검색 추가
# 분석 완료 후

if vision_result and vision_result.success:
    # 기존 결과 표시...

    # RAG 기반 지자체 정보 추가
    user_location = st.session_state.get('user_location')
    if user_location:
        district_code = get_district_code(user_location)

        if district_code:
            rag_service = get_service('district_rag_service')

            guidance_query = f"{vision_result.category} 대형폐기물 배출 방법"

            guidance_result = rag_service.get_district_guidance(
                user_query=guidance_query,
                district_code=district_code,
                item_info={
                    'category': vision_result.category,
                    'size': f"{vision_result.width_cm}x{vision_result.height_cm}cm"
                }
            )

            if guidance_result['success']:
                st.divider()
                st.subheader("🏛️ 지자체별 배출 안내")
                st.write(guidance_result['response'])

                # 신뢰도 표시
                if guidance_result['confidence'] > 0.7:
                    st.success(f"✅ 신뢰도: {guidance_result['confidence']:.1%}")
                else:
                    st.warning(f"⚠️ 신뢰도: {guidance_result['confidence']:.1%} (추가 확인 권장)")

                # 출처 정보
                with st.expander("📋 정보 출처"):
                    for source in guidance_result['sources']:
                        st.write(f"- {source['url']}")
```

### 5단계: 품질 최적화 (지속적)

```python
# 검색 품질 모니터링 및 개선
def monitor_search_quality():
    """검색 품질 모니터링"""

    # 낮은 신뢰도 쿼리 분석
    low_confidence_queries = get_low_confidence_searches()

    # 자주 검색되는 미해결 질문 분석
    frequent_failed_queries = get_frequent_failed_queries()

    # 개선 제안 생성
    improvement_suggestions = generate_improvement_suggestions(
        low_confidence_queries, frequent_failed_queries
    )

    return improvement_suggestions
```

## 📊 성공 지표 및 모니터링

### 핵심 KPI
1. **검색 정확도**: RAG 검색 신뢰도 > 85%
2. **응답 시간**: 평균 검색 응답 시간 < 3초
3. **정보 최신성**: 지자체 정보 업데이트 주기 < 1주
4. **사용자 만족도**: RAG 응답 만족도 > 4.0/5.0

### 모니터링 대시보드
- 실시간 검색 성능 지표
- 지자체별 문서 인덱싱 상태
- 검색 쿼리 패턴 분석
- 낮은 신뢰도 검색 리스트

## 🔮 다음 Phase 연계점

### Phase 1 (피드백) 연계
```python
# 사용자 피드백을 RAG 품질 개선에 활용
- RAG 응답 정확성 평가 → 검색 알고리즘 개선
- 자주 틀리는 정보 → 추가 문서 수집 대상
- 사용자 만족도 → RAG 시스템 성능 지표
```

### Phase 4 (프롬프트 최적화) 연계
```python
# RAG 결과를 프롬프트 최적화에 활용
- 고품질 RAG 컨텍스트 → 더 정확한 프롬프트
- 지자체별 특성 → 지역 맞춤형 프롬프트
- 검색 신뢰도 → 프롬프트 조건부 활용
```

## 💡 구현 팁

1. **점진적 확장**: 주요 지자체(서울, 부산 등)부터 시작하여 점차 확대
2. **캐싱 전략**: 자주 검색되는 쿼리는 결과 캐싱으로 성능 최적화
3. **폴백 메커니즘**: RAG 실패 시 기본 정보 제공 체계 구축
4. **자동 업데이트**: 주기적으로 지자체 웹사이트 변경 감지 및 재인덱싱

이 Phase 3은 **완전히 독립적으로 구현하여 즉시 서비스 품질을 혁신**할 수 있으며, 다른 Phase들과 연계할 때 더욱 강력한 시너지를 발휘합니다.