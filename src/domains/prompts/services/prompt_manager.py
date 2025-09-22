"""
프롬프트 CRUD 및 데이터 관리를 담당하는 모듈입니다.

프롬프트의 생성, 수정, 삭제, 조회와 데이터 저장/로딩, 백업 관리를 담당합니다.
"""
import json
import os
import shutil
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
import uuid

from src.app.core.prompt_types import (
    PromptTemplate, FeaturePromptMapping, PromptUsageStats,
    PromptCategory, PromptStatus, PromptConfig
)


class PromptManager:
    """
    프롬프트 CRUD 및 데이터 관리를 담당하는 클래스입니다.
    """

    def __init__(self, config: PromptConfig, logger=None):
        """
        프롬프트 매니저를 초기화합니다.

        Args:
            config: 프롬프트 설정
            logger: 로거 인스턴스
        """
        self.config = config
        self.logger = logger
        self._cache: Dict[str, PromptTemplate] = {}
        self._mappings: List[FeaturePromptMapping] = []
        self._stats: Dict[str, PromptUsageStats] = {}

        # 저장소 디렉토리 생성
        self._ensure_storage_directories()

        # 데이터 로드
        self._load_all_data()

    def _ensure_storage_directories(self):
        """필요한 저장소 디렉토리들을 생성합니다."""
        storage_path = Path(self.config.storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)

        # 하위 디렉토리들 생성
        (storage_path / "templates").mkdir(exist_ok=True)
        (storage_path / "mappings").mkdir(exist_ok=True)
        (storage_path / "stats").mkdir(exist_ok=True)
        (storage_path / "backups").mkdir(exist_ok=True)

    def _load_all_data(self):
        """모든 프롬프트 데이터를 로드합니다."""
        try:
            self._load_templates()
            self._load_mappings()
            self._load_stats()
            if self.logger:
                self.logger.info("프롬프트 데이터 로드 완료")
        except Exception as e:
            if self.logger:
                self.logger.error(f"프롬프트 데이터 로드 실패: {e}")

    def _load_templates(self):
        """프롬프트 템플릿들을 로드합니다."""
        templates_dir = Path(self.config.storage_path) / "templates"

        for template_file in templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 날짜 문자열을 datetime 객체로 변환
                if 'created_at' in data:
                    data['created_at'] = datetime.fromisoformat(data['created_at'])
                if 'updated_at' in data:
                    data['updated_at'] = datetime.fromisoformat(data['updated_at'])

                # 열거형 변환
                if 'category' in data:
                    data['category'] = PromptCategory(data['category'])
                if 'status' in data:
                    data['status'] = PromptStatus(data['status'])

                template = PromptTemplate(**data)
                self._cache[template.id] = template

            except Exception as e:
                if self.logger:
                    self.logger.error(f"템플릿 로드 실패 {template_file}: {e}")

    def _load_mappings(self):
        """기능-프롬프트 매핑을 로드합니다."""
        mappings_file = Path(self.config.storage_path) / "mappings" / "feature_mappings.json"

        if mappings_file.exists():
            try:
                with open(mappings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self._mappings = []
                for mapping_data in data:
                    if 'created_at' in mapping_data:
                        mapping_data['created_at'] = datetime.fromisoformat(mapping_data['created_at'])

                    mapping = FeaturePromptMapping(**mapping_data)
                    self._mappings.append(mapping)

            except Exception as e:
                if self.logger:
                    self.logger.error(f"매핑 로드 실패: {e}")

    def _load_stats(self):
        """사용 통계를 로드합니다."""
        stats_file = Path(self.config.storage_path) / "stats" / "usage_stats.json"

        if stats_file.exists():
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self._stats = {}
                for prompt_id, stats_data in data.items():
                    if 'last_used' in stats_data and stats_data['last_used']:
                        stats_data['last_used'] = datetime.fromisoformat(stats_data['last_used'])

                    stats = PromptUsageStats(**stats_data)
                    self._stats[prompt_id] = stats

            except Exception as e:
                if self.logger:
                    self.logger.error(f"통계 로드 실패: {e}")

    def create_prompt(self,
                     name: str,
                     description: str,
                     category: PromptCategory,
                     template: str,
                     created_by: str = "admin",
                     tags: List[str] = None,
                     metadata: Dict[str, Any] = None) -> PromptTemplate:
        """
        새로운 프롬프트를 생성합니다.

        Args:
            name: 프롬프트 이름
            description: 프롬프트 설명
            category: 카테고리
            template: 프롬프트 템플릿 내용
            created_by: 생성자
            tags: 태그 목록
            metadata: 메타데이터

        Returns:
            생성된 프롬프트 템플릿
        """
        prompt_id = str(uuid.uuid4())

        # 변수 추출 (renderer에서 처리하지만 여기서는 기본 구현)
        import re
        pattern = r'\{([^}]+)\}'
        variables = list(set(re.findall(pattern, template)))

        prompt_template = PromptTemplate(
            id=prompt_id,
            name=name,
            description=description,
            category=category,
            template=template,
            variables=variables,
            created_by=created_by,
            tags=tags or [],
            metadata=metadata or {}
        )

        # 캐시에 추가
        self._cache[prompt_id] = prompt_template

        # 파일에 저장
        self._save_template(prompt_template)

        # 백업 (설정에 따라)
        if self.config.auto_backup_on_change:
            self._backup_data()

        if self.logger:
            self.logger.info(f"프롬프트 생성 완료: {name} ({prompt_id})")
        return prompt_template

    def update_prompt(self, prompt_id: str, **kwargs) -> Optional[PromptTemplate]:
        """
        기존 프롬프트를 수정합니다.

        Args:
            prompt_id: 프롬프트 ID
            **kwargs: 수정할 필드들

        Returns:
            수정된 프롬프트 템플릿 또는 None
        """
        if prompt_id not in self._cache:
            if self.logger:
                self.logger.warning(f"존재하지 않는 프롬프트 ID: {prompt_id}")
            return None

        template = self._cache[prompt_id]

        # 수정 가능한 필드들 업데이트
        updatable_fields = ['name', 'description', 'template', 'status', 'tags', 'metadata']

        for field, value in kwargs.items():
            if field in updatable_fields:
                setattr(template, field, value)

        # 템플릿이 변경된 경우 변수 재추출
        if 'template' in kwargs:
            import re
            pattern = r'\{([^}]+)\}'
            template.variables = list(set(re.findall(pattern, kwargs['template'])))

        # 수정 시간 업데이트
        template.updated_at = datetime.now()

        # 파일에 저장
        self._save_template(template)

        # 백업 (설정에 따라)
        if self.config.auto_backup_on_change:
            self._backup_data()

        if self.logger:
            self.logger.info(f"프롬프트 수정 완료: {template.name} ({prompt_id})")
        return template

    def delete_prompt(self, prompt_id: str) -> bool:
        """
        프롬프트를 삭제합니다.

        Args:
            prompt_id: 프롬프트 ID

        Returns:
            삭제 성공 여부
        """
        if prompt_id not in self._cache:
            if self.logger:
                self.logger.warning(f"존재하지 않는 프롬프트 ID: {prompt_id}")
            return False

        template = self._cache[prompt_id]

        # 캐시에서 제거
        del self._cache[prompt_id]

        # 파일 삭제
        template_file = Path(self.config.storage_path) / "templates" / f"{prompt_id}.json"
        if template_file.exists():
            template_file.unlink()

        # 관련 매핑 제거
        self._mappings = [m for m in self._mappings if m.prompt_id != prompt_id]
        self._save_mappings()

        # 통계 제거
        if prompt_id in self._stats:
            del self._stats[prompt_id]
            self._save_stats()

        # 백업 (설정에 따라)
        if self.config.auto_backup_on_change:
            self._backup_data()

        if self.logger:
            self.logger.info(f"프롬프트 삭제 완료: {template.name} ({prompt_id})")
        return True

    def get_prompt(self, prompt_id: str) -> Optional[PromptTemplate]:
        """
        프롬프트를 조회합니다.

        Args:
            prompt_id: 프롬프트 ID

        Returns:
            프롬프트 템플릿 또는 None
        """
        return self._cache.get(prompt_id)

    def list_prompts(self,
                    category: Optional[PromptCategory] = None,
                    status: Optional[PromptStatus] = None,
                    tags: Optional[List[str]] = None) -> List[PromptTemplate]:
        """
        프롬프트 목록을 조회합니다.

        Args:
            category: 필터링할 카테고리
            status: 필터링할 상태
            tags: 필터링할 태그들

        Returns:
            프롬프트 템플릿 목록
        """
        prompts = list(self._cache.values())

        # 필터링
        if category:
            prompts = [p for p in prompts if p.category == category]

        if status:
            prompts = [p for p in prompts if p.status == status]

        if tags:
            prompts = [p for p in prompts if any(tag in p.tags for tag in tags)]

        # 이름으로 정렬
        return sorted(prompts, key=lambda p: p.name)

    def search_prompts(self, query: str) -> List[PromptTemplate]:
        """
        프롬프트를 검색합니다.

        Args:
            query: 검색 쿼리

        Returns:
            검색 결과 프롬프트 목록
        """
        query_lower = query.lower()
        results = []

        for template in self._cache.values():
            # 이름, 설명, 태그에서 검색
            if (query_lower in template.name.lower() or
                query_lower in template.description.lower() or
                any(query_lower in tag.lower() for tag in template.tags)):
                results.append(template)

        return sorted(results, key=lambda p: p.name)

    def map_feature_to_prompt(self,
                             feature_id: str,
                             prompt_id: str,
                             is_default: bool = False,
                             priority: int = 0,
                             conditions: Dict[str, Any] = None) -> bool:
        """
        기능과 프롬프트를 매핑합니다.

        Args:
            feature_id: 기능 ID
            prompt_id: 프롬프트 ID
            is_default: 기본 프롬프트 여부
            priority: 우선순위
            conditions: 적용 조건

        Returns:
            매핑 성공 여부
        """
        if prompt_id not in self._cache:
            if self.logger:
                self.logger.warning(f"존재하지 않는 프롬프트 ID: {prompt_id}")
            return False

        # 기존 매핑 제거 (동일한 feature_id와 prompt_id)
        self._mappings = [m for m in self._mappings
                         if not (m.feature_id == feature_id and m.prompt_id == prompt_id)]

        # 새 매핑 추가
        mapping = FeaturePromptMapping(
            feature_id=feature_id,
            prompt_id=prompt_id,
            is_default=is_default,
            priority=priority,
            conditions=conditions or {}
        )

        self._mappings.append(mapping)
        self._save_mappings()

        if self.logger:
            self.logger.info(f"기능-프롬프트 매핑 완료: {feature_id} -> {prompt_id}")
        return True

    def unmap_feature_from_prompt(self, feature_id: str, prompt_id: str) -> bool:
        """
        기능과 프롬프트 매핑을 제거합니다.

        Args:
            feature_id: 기능 ID
            prompt_id: 프롬프트 ID

        Returns:
            매핑 제거 성공 여부
        """
        initial_count = len(self._mappings)

        # 매핑 제거
        self._mappings = [m for m in self._mappings
                         if not (m.feature_id == feature_id and m.prompt_id == prompt_id)]

        removed_count = initial_count - len(self._mappings)

        if removed_count > 0:
            self._save_mappings()
            if self.logger:
                self.logger.info(f"기능-프롬프트 매핑 제거 완료: {feature_id} -> {prompt_id}")
            return True
        else:
            if self.logger:
                self.logger.warning(f"제거할 매핑을 찾을 수 없음: {feature_id} -> {prompt_id}")
            return False

    def get_prompts_for_feature(self, feature_id: str) -> List[PromptTemplate]:
        """
        특정 기능에 매핑된 프롬프트들을 조회합니다.

        Args:
            feature_id: 기능 ID

        Returns:
            프롬프트 템플릿 목록 (우선순위 순)
        """
        # 해당 기능의 매핑들 찾기
        feature_mappings = [m for m in self._mappings if m.feature_id == feature_id]

        # 우선순위로 정렬
        feature_mappings.sort(key=lambda m: m.priority)

        # 프롬프트 템플릿들 반환
        prompts = []
        for mapping in feature_mappings:
            template = self.get_prompt(mapping.prompt_id)
            if template and template.status == PromptStatus.ACTIVE:
                prompts.append(template)

        return prompts

    def get_default_prompt_for_feature(self, feature_id: str) -> Optional[PromptTemplate]:
        """
        특정 기능의 기본 프롬프트를 조회합니다.

        Args:
            feature_id: 기능 ID

        Returns:
            기본 프롬프트 템플릿 또는 None
        """
        # 기본 프롬프트 매핑 찾기
        default_mappings = [m for m in self._mappings
                           if m.feature_id == feature_id and m.is_default]

        if not default_mappings:
            # 기본 프롬프트가 없으면 우선순위가 가장 높은 것 반환
            prompts = self.get_prompts_for_feature(feature_id)
            return prompts[0] if prompts else None

        # 기본 프롬프트 중 우선순위가 가장 높은 것
        default_mappings.sort(key=lambda m: m.priority)

        return self.get_prompt(default_mappings[0].prompt_id)

    def get_usage_stats(self, prompt_id: str) -> Optional[PromptUsageStats]:
        """
        프롬프트 사용 통계를 조회합니다.

        Args:
            prompt_id: 프롬프트 ID

        Returns:
            사용 통계 또는 None
        """
        return self._stats.get(prompt_id)

    def update_usage_stats(self, prompt_id: str):
        """프롬프트 사용 통계를 업데이트합니다."""
        if not self.config.usage_tracking_enabled:
            return

        if prompt_id not in self._stats:
            self._stats[prompt_id] = PromptUsageStats(prompt_id=prompt_id)

        stats = self._stats[prompt_id]
        stats.usage_count += 1
        stats.last_used = datetime.now()

        # 통계 저장
        self._save_stats()

    def export_prompts(self, category: Optional[PromptCategory] = None) -> Dict[str, Any]:
        """
        프롬프트를 내보냅니다.

        Args:
            category: 내보낼 카테고리 (None이면 전체)

        Returns:
            내보내기 데이터
        """
        prompts = self.list_prompts(category=category)

        export_data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'version': '1.0',
                'total_count': len(prompts),
                'category_filter': category.value if category else None
            },
            'prompts': [],
            'mappings': []
        }

        # 프롬프트 데이터
        for prompt in prompts:
            export_data['prompts'].append({
                'id': prompt.id,
                'name': prompt.name,
                'description': prompt.description,
                'category': prompt.category.value,
                'template': prompt.template,
                'variables': prompt.variables,
                'status': prompt.status.value,
                'created_at': prompt.created_at.isoformat(),
                'updated_at': prompt.updated_at.isoformat(),
                'created_by': prompt.created_by,
                'version': prompt.version,
                'tags': prompt.tags,
                'metadata': prompt.metadata
            })

        # 관련 매핑 데이터
        prompt_ids = {p.id for p in prompts}
        related_mappings = [m for m in self._mappings if m.prompt_id in prompt_ids]

        for mapping in related_mappings:
            export_data['mappings'].append({
                'feature_id': mapping.feature_id,
                'prompt_id': mapping.prompt_id,
                'is_default': mapping.is_default,
                'priority': mapping.priority,
                'conditions': mapping.conditions,
                'created_at': mapping.created_at.isoformat()
            })

        return export_data

    def import_prompts(self, import_data: Dict[str, Any], overwrite: bool = False) -> Dict[str, Any]:
        """
        프롬프트를 가져옵니다.

        Args:
            import_data: 가져올 데이터
            overwrite: 기존 프롬프트 덮어쓰기 여부

        Returns:
            가져오기 결과
        """
        result = {
            'success': True,
            'imported_count': 0,
            'skipped_count': 0,
            'error_count': 0,
            'errors': []
        }

        try:
            # 데이터 구조 검증
            if 'prompts' not in import_data:
                result['success'] = False
                result['errors'].append("유효하지 않은 가져오기 데이터입니다.")
                return result

            # 프롬프트 가져오기
            for prompt_data in import_data.get('prompts', []):
                try:
                    prompt_id = prompt_data.get('id')

                    # 기존 프롬프트 확인
                    if prompt_id in self._cache:
                        if not overwrite:
                            result['skipped_count'] += 1
                            continue
                        else:
                            # 기존 프롬프트 삭제
                            self.delete_prompt(prompt_id)

                    # 새 프롬프트 생성
                    new_prompt = PromptTemplate(
                        id=prompt_id,
                        name=prompt_data['name'],
                        description=prompt_data['description'],
                        category=PromptCategory(prompt_data['category']),
                        template=prompt_data['template'],
                        variables=prompt_data.get('variables', []),
                        status=PromptStatus(prompt_data.get('status', 'active')),
                        created_at=datetime.fromisoformat(prompt_data.get('created_at', datetime.now().isoformat())),
                        updated_at=datetime.fromisoformat(prompt_data.get('updated_at', datetime.now().isoformat())),
                        created_by=prompt_data.get('created_by', 'imported'),
                        version=prompt_data.get('version', '1.0'),
                        tags=prompt_data.get('tags', []),
                        metadata=prompt_data.get('metadata', {})
                    )

                    # 캐시에 추가 및 저장
                    self._cache[prompt_id] = new_prompt
                    self._save_template(new_prompt)

                    result['imported_count'] += 1

                except Exception as e:
                    result['error_count'] += 1
                    result['errors'].append(f"프롬프트 '{prompt_data.get('name', 'Unknown')}' 가져오기 실패: {e}")

            # 매핑 가져오기
            for mapping_data in import_data.get('mappings', []):
                try:
                    feature_id = mapping_data['feature_id']
                    prompt_id = mapping_data['prompt_id']

                    # 프롬프트가 존재하는지 확인
                    if prompt_id in self._cache:
                        self.map_feature_to_prompt(
                            feature_id=feature_id,
                            prompt_id=prompt_id,
                            is_default=mapping_data.get('is_default', False),
                            priority=mapping_data.get('priority', 0),
                            conditions=mapping_data.get('conditions', {})
                        )

                except Exception as e:
                    result['errors'].append(f"매핑 가져오기 실패: {e}")

            # 백업 생성
            if result['imported_count'] > 0 and self.config.auto_backup_on_change:
                self._backup_data()

        except Exception as e:
            result['success'] = False
            result['errors'].append(f"가져오기 중 오류 발생: {e}")

        return result

    def _save_template(self, template: PromptTemplate):
        """프롬프트 템플릿을 파일에 저장합니다."""
        template_file = Path(self.config.storage_path) / "templates" / f"{template.id}.json"

        # 데이터 직렬화
        data = {
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'category': template.category.value,
            'template': template.template,
            'variables': template.variables,
            'status': template.status.value,
            'created_at': template.created_at.isoformat(),
            'updated_at': template.updated_at.isoformat(),
            'created_by': template.created_by,
            'version': template.version,
            'tags': template.tags,
            'metadata': template.metadata
        }

        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_mappings(self):
        """기능-프롬프트 매핑을 파일에 저장합니다."""
        mappings_file = Path(self.config.storage_path) / "mappings" / "feature_mappings.json"

        data = []
        for mapping in self._mappings:
            data.append({
                'feature_id': mapping.feature_id,
                'prompt_id': mapping.prompt_id,
                'is_default': mapping.is_default,
                'priority': mapping.priority,
                'conditions': mapping.conditions,
                'created_at': mapping.created_at.isoformat()
            })

        with open(mappings_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_stats(self):
        """사용 통계를 파일에 저장합니다."""
        stats_file = Path(self.config.storage_path) / "stats" / "usage_stats.json"

        data = {}
        for prompt_id, stats in self._stats.items():
            data[prompt_id] = {
                'prompt_id': stats.prompt_id,
                'usage_count': stats.usage_count,
                'last_used': stats.last_used.isoformat() if stats.last_used else None,
                'success_rate': stats.success_rate,
                'average_response_time': stats.average_response_time,
                'user_ratings': stats.user_ratings
            }

        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _backup_data(self):
        """데이터를 백업합니다."""
        if not self.config.backup_enabled:
            return

        try:
            backup_dir = Path(self.config.storage_path) / "backups"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"backup_{timestamp}"

            # 전체 데이터 디렉토리를 백업
            storage_path = Path(self.config.storage_path)
            shutil.copytree(storage_path, backup_path, ignore=shutil.ignore_patterns("backups"))

            # 오래된 백업 정리
            self._cleanup_old_backups()

            if self.logger:
                self.logger.info(f"데이터 백업 완료: {backup_path}")

        except Exception as e:
            if self.logger:
                self.logger.error(f"백업 실패: {e}")

    def _cleanup_old_backups(self):
        """오래된 백업을 정리합니다."""
        backup_dir = Path(self.config.storage_path) / "backups"

        if not backup_dir.exists():
            return

        # 백업 디렉토리들을 생성 시간 순으로 정렬
        backup_dirs = [d for d in backup_dir.iterdir() if d.is_dir()]
        backup_dirs.sort(key=lambda d: d.stat().st_ctime, reverse=True)

        # 최대 버전 수를 초과하는 백업들 삭제
        if len(backup_dirs) > self.config.max_versions:
            for old_backup in backup_dirs[self.config.max_versions:]:
                shutil.rmtree(old_backup)
                if self.logger:
                    self.logger.info(f"오래된 백업 삭제: {old_backup}")


__all__ = [
    'PromptManager',
]