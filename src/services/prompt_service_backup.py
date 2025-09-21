"""
프롬프트 관리 통합 서비스 모듈입니다.

프롬프트 관리, 렌더링, 검증 모듈들을 통합하여 제공하는 메인 서비스입니다.
"""
from typing import List, Dict, Optional, Any

from src.core.prompt_types import (
    PromptTemplate, FeaturePromptMapping, PromptUsageStats,
    PromptCategory, PromptStatus, PromptConfig
)
from src.core.base_service import BaseService
from src.services.prompt_manager import PromptManager
from src.services.prompt_renderer import PromptRenderer
from src.services.prompt_validator import PromptValidator


class PromptService(BaseService):
    """
    프롬프트 관리 통합 서비스 클래스입니다.

    PromptManager, PromptRenderer, PromptValidator를 통합하여 제공합니다.
    """

    def __init__(self, config: PromptConfig):
        """
        프롬프트 서비스를 초기화합니다.

        Args:
            config: 프롬프트 설정
        """
        # BaseService는 Config 타입을 요구하므로, 임시로 config를 전달
        # 실제로는 PromptConfig만 사용함
        from src.core.config import Config
        super().__init__(config=Config())
        from src.core.logger import get_logger

        self.config = config
        self.logger = get_logger(__name__)

        # 하위 모듈들 초기화
        self.manager = PromptManager(config, self.logger)
        self.renderer = PromptRenderer(config, self.logger)
        self.validator = PromptValidator(config, self.logger)
    
    def get_service_name(self) -> str:
        """서비스 이름을 반환합니다."""
        return "prompt_service"

    def get_service_version(self) -> str:
        """서비스 버전을 반환합니다."""
        return "2.0.0"

    def get_service_description(self) -> str:
        """서비스 설명을 반환합니다."""
        return "프롬프트 관리, 렌더링, 검증 통합 서비스"

    # ===== PromptManager 위임 메서드들 =====

    def create_prompt(self,
                     name: str,
                     description: str,
                     category: PromptCategory,
                     template: str,
                     created_by: str = "admin",
                     tags: List[str] = None,
                     metadata: Dict[str, Any] = None) -> PromptTemplate:
        """새로운 프롬프트를 생성합니다."""
        return self.manager.create_prompt(
            name=name, description=description, category=category,
            template=template, created_by=created_by,
            tags=tags, metadata=metadata
        )
    
    def update_prompt(self, prompt_id: str, **kwargs) -> Optional[PromptTemplate]:
        """기존 프롬프트를 수정합니다."""
        return self.manager.update_prompt(prompt_id, **kwargs)
    
    def delete_prompt(self, prompt_id: str) -> bool:
        """프롬프트를 삭제합니다."""
        return self.manager.delete_prompt(prompt_id)
    
    def get_prompt(self, prompt_id: str) -> Optional[PromptTemplate]:
        """프롬프트를 조회합니다."""
        return self.manager.get_prompt(prompt_id)
    
    def list_prompts(self,
                    category: Optional[PromptCategory] = None,
                    status: Optional[PromptStatus] = None,
                    tags: Optional[List[str]] = None) -> List[PromptTemplate]:
        """프롬프트 목록을 조회합니다."""
        return self.manager.list_prompts(category=category, status=status, tags=tags)
    
    def render_prompt(self, prompt_id: str, variables: Dict[str, Any] = None) -> Optional[str]:
        """
        프롬프트를 변수로 렌더링합니다.
        
        Args:
            prompt_id: 프롬프트 ID
            variables: 템플릿 변수들
            
        Returns:
            렌더링된 프롬프트 문자열 또는 None
        """
        template = self.get_prompt(prompt_id)
        if not template:
            return None
        
        rendered = template.template
        
        if variables:
            for var_name, var_value in variables.items():
                placeholder = f"{{{var_name}}}"
                rendered = rendered.replace(placeholder, str(var_value))
        
        # 사용 통계 업데이트
        self._update_usage_stats(prompt_id)
        
        return rendered
    
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
            self.logger.info(f"기능-프롬프트 매핑 제거 완료: {feature_id} -> {prompt_id}")
            return True
        else:
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
    
    def _extract_variables(self, template: str) -> List[str]:
        """
        템플릿에서 변수들을 추출합니다.
        
        Args:
            template: 템플릿 문자열
            
        Returns:
            변수 이름 목록
        """
        # {variable_name} 패턴으로 변수 추출
        pattern = r'\{([^}]+)\}'
        variables = re.findall(pattern, template)
        return list(set(variables))  # 중복 제거
    
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
    
    def _update_usage_stats(self, prompt_id: str):
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
            
            self.logger.info(f"데이터 백업 완료: {backup_path}")
            
        except Exception as e:
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
                self.logger.info(f"오래된 백업 삭제: {old_backup}")
    
    def get_usage_stats(self, prompt_id: str) -> Optional[PromptUsageStats]:
        """
        프롬프트 사용 통계를 조회합니다.
        
        Args:
            prompt_id: 프롬프트 ID
            
        Returns:
            사용 통계 또는 None
        """
        return self._stats.get(prompt_id)
    
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
    
    def validate_prompt_template(self, template: str) -> Dict[str, Any]:
        """
        프롬프트 템플릿의 유효성을 검증합니다.
        
        Args:
            template: 검증할 템플릿 문자열
            
        Returns:
            검증 결과 딕셔너리
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'variables': [],
            'statistics': {}
        }
        
        if not template or not template.strip():
            result['is_valid'] = False
            result['errors'].append("템플릿이 비어있습니다.")
            return result
        
        # 변수 추출 및 검증
        variables = self._extract_variables(template)
        result['variables'] = variables
        
        # 변수 유효성 검증
        for var in variables:
            if not var.isidentifier():
                result['warnings'].append(f"변수명 '{var}'은 Python 식별자 규칙에 맞지 않습니다.")
        
        # 템플릿 통계
        result['statistics'] = {
            'character_count': len(template),
            'word_count': len(template.split()),
            'variable_count': len(variables),
            'line_count': template.count('\n') + 1
        }
        
        # 길이 검증
        if len(template) > 10000:
            result['warnings'].append("템플릿이 너무 깁니다. (10,000자 초과)")
        
        if len(template) < 10:
            result['warnings'].append("템플릿이 너무 짧습니다.")
        
        # 기본적인 구조 검증
        if '{' in template and '}' not in template:
            result['errors'].append("닫히지 않은 중괄호가 있습니다.")
            result['is_valid'] = False
        
        if '}' in template and '{' not in template:
            result['errors'].append("열리지 않은 중괄호가 있습니다.")
            result['is_valid'] = False
        
        return result
    
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
