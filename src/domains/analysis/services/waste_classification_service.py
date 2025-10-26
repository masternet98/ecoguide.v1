"""
폐기물 분류 서비스

waste_types.json 파일을 기반으로 계층적 폐기물 분류 시스템을 제공합니다.
AI 분석 결과를 JSON 구조에 매핑하고 사용자 수정을 지원합니다.
개선된 프롬프트의 JSON 출력을 파싱하고 검증하는 기능을 제공합니다.
"""
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from src.app.core.base_service import BaseService
from src.app.core.config import Config

logger = logging.getLogger(__name__)


@dataclass
class WasteAnalysisResult:
    """개선된 프롬프트의 분석 결과 데이터 클래스"""
    object_name: str
    category: str
    subcategory: str
    size: str
    material: str
    condition: str
    disposal_difficulty: str
    estimated_dimensions: str
    incheon_seogu_notes: str
    confidence: float
    raw_text: str = ""  # 원본 텍스트 보존

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "object_name": self.object_name,
            "category": self.category,
            "subcategory": self.subcategory,
            "size": self.size,
            "material": self.material,
            "condition": self.condition,
            "disposal_difficulty": self.disposal_difficulty,
            "estimated_dimensions": self.estimated_dimensions,
            "incheon_seogu_notes": self.incheon_seogu_notes,
            "confidence": self.confidence,
            "raw_text": self.raw_text
        }


class WasteClassificationService(BaseService):
    """폐기물 분류 관리 서비스"""

    def __init__(self, config: Config):
        super().__init__(config)
        self.waste_types_file = Path("uploads/waste_types/waste_types.json")
        self.waste_types_data = self._load_waste_types()

        # 유효성 검증을 위한 데이터 정의
        self.valid_sizes = {"소형", "중형", "대형"}
        self.valid_conditions = {"신품", "양호", "사용감있음", "손상됨", "부분파손"}
        self.valid_difficulties = {"쉬움", "보통", "어려움"}

    def get_service_name(self) -> str:
        """서비스 이름을 반환합니다."""
        return "WasteClassificationService"

    def get_service_version(self) -> str:
        """서비스 버전을 반환합니다."""
        return "1.0.0"

    def get_service_description(self) -> str:
        """서비스 설명을 반환합니다."""
        return "waste_types.json 기반 계층적 폐기물 분류 관리 서비스"

    def _load_waste_types(self) -> Dict[str, Any]:
        """waste_types JSON 파일을 로드합니다."""
        try:
            if not self.waste_types_file.exists():
                logger.error(f"Waste types file not found: {self.waste_types_file}")
                return {}

            with open(self.waste_types_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Waste types loaded: {len(data)} categories")
                return data

        except Exception as e:
            logger.error(f"Error loading waste types: {e}")
            return {}

    def get_all_categories(self) -> Dict[str, Any]:
        """모든 폐기물 카테고리를 반환합니다."""
        return self.waste_types_data

    def get_main_categories(self) -> List[str]:
        """주분류 목록을 반환합니다."""
        return list(self.waste_types_data.keys())

    def get_subcategories(self, main_category: str) -> List[Dict[str, Any]]:
        """특정 주분류의 세분류 목록을 반환합니다."""
        if main_category not in self.waste_types_data:
            return []

        return self.waste_types_data[main_category].get('세분류', [])

    def find_best_match(self, object_name: str) -> Tuple[Optional[str], Optional[str], float]:
        """
        객체명으로 최적의 분류를 찾습니다.

        Returns:
            Tuple[주분류, 세분류명, 매칭점수]
        """
        if not object_name:
            return None, None, 0.0

        object_name_lower = object_name.lower()
        best_main = None
        best_sub = None
        best_score = 0.0

        for main_category, category_data in self.waste_types_data.items():
            subcategories = category_data.get('세분류', [])

            for subcategory in subcategories:
                sub_name = subcategory.get('명칭', '')
                examples = subcategory.get('예시', [])

                # 세분류명과 직접 매칭
                if object_name_lower in sub_name.lower():
                    score = len(object_name_lower) / len(sub_name)
                    if score > best_score:
                        best_main = main_category
                        best_sub = sub_name
                        best_score = score

                # 예시와 매칭
                for example in examples:
                    if object_name_lower in example.lower() or example.lower() in object_name_lower:
                        score = min(len(object_name_lower), len(example)) / max(len(object_name_lower), len(example))
                        if score > best_score:
                            best_main = main_category
                            best_sub = sub_name
                            best_score = score

        return best_main, best_sub, best_score

    def validate_classification(self, main_category: str, sub_category: str) -> bool:
        """분류가 유효한지 검증합니다."""
        if main_category not in self.waste_types_data:
            return False

        subcategories = self.get_subcategories(main_category)
        sub_names = [sub.get('명칭', '') for sub in subcategories]

        return sub_category in sub_names

    def get_classification_info(self, main_category: str, sub_category: str = None) -> Dict[str, Any]:
        """분류 상세 정보를 반환합니다."""
        if main_category not in self.waste_types_data:
            return {}

        result = {
            'main_category': main_category,
            'description': self.waste_types_data[main_category].get('설명', ''),
            'subcategories': self.get_subcategories(main_category)
        }

        if sub_category:
            # 특정 세분류 정보 추가
            subcategories = self.get_subcategories(main_category)
            for sub in subcategories:
                if sub.get('명칭') == sub_category:
                    result['selected_subcategory'] = sub
                    break

        return result

    def suggest_corrections(self, current_main: str, current_sub: str, object_name: str) -> List[Dict[str, Any]]:
        """현재 분류에 대한 수정 제안을 생성합니다."""
        suggestions = []

        # AI 추천 분류
        best_main, best_sub, score = self.find_best_match(object_name)
        if best_main and score > 0.3 and (best_main != current_main or best_sub != current_sub):
            suggestions.append({
                'type': 'ai_suggestion',
                'main_category': best_main,
                'sub_category': best_sub,
                'confidence': score,
                'reason': f'"{object_name}"과 유사한 예시가 있습니다'
            })

        # 동일 주분류 내 다른 세분류 제안
        if current_main in self.waste_types_data:
            subcategories = self.get_subcategories(current_main)
            for sub in subcategories[:3]:  # 상위 3개만
                sub_name = sub.get('명칭', '')
                if sub_name != current_sub:
                    suggestions.append({
                        'type': 'alternative',
                        'main_category': current_main,
                        'sub_category': sub_name,
                        'examples': sub.get('예시', [])[:2],  # 예시 2개만
                        'reason': f'{current_main} 분류 내 다른 옵션'
                    })

        return suggestions

    def update_waste_types(self, new_data: Dict[str, Any]) -> bool:
        """폐기물 분류 데이터를 업데이트합니다."""
        try:
            # 백업 생성
            backup_file = self.waste_types_file.with_suffix('.backup.json')
            if self.waste_types_file.exists():
                import shutil
                shutil.copy2(self.waste_types_file, backup_file)

            # 새 데이터 저장
            with open(self.waste_types_file, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)

            # 메모리 업데이트
            self.waste_types_data = new_data
            logger.info("Waste types data updated successfully")
            return True

        except Exception as e:
            logger.error(f"Error updating waste types: {e}")
            return False

    def add_example(self, main_category: str, sub_category: str, new_example: str) -> bool:
        """특정 세분류에 예시를 추가합니다."""
        try:
            if main_category not in self.waste_types_data:
                return False

            subcategories = self.waste_types_data[main_category]['세분류']
            for sub in subcategories:
                if sub.get('명칭') == sub_category:
                    if new_example not in sub.get('예시', []):
                        sub.setdefault('예시', []).append(new_example)
                        return self.update_waste_types(self.waste_types_data)

            return False

        except Exception as e:
            logger.error(f"Error adding example: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """폐기물 분류 통계를 반환합니다."""
        stats = {
            'main_categories_count': len(self.waste_types_data),
            'total_subcategories': 0,
            'total_examples': 0,
            'categories_detail': []
        }

        for main_cat, data in self.waste_types_data.items():
            subcategories = data.get('세분류', [])
            sub_count = len(subcategories)
            example_count = sum(len(sub.get('예시', [])) for sub in subcategories)

            stats['total_subcategories'] += sub_count
            stats['total_examples'] += example_count

            stats['categories_detail'].append({
                'main_category': main_cat,
                'subcategories_count': sub_count,
                'examples_count': example_count,
                'description': data.get('설명', '')
            })

        return stats

    # ===== 개선된 프롬프트 JSON 파싱 메서드들 =====

    def parse_enhanced_analysis_result(self, raw_response: str) -> Tuple[Optional[WasteAnalysisResult], Dict[str, Any]]:
        """
        개선된 프롬프트의 AI 분석 결과를 파싱하여 구조화된 데이터로 변환합니다.

        Args:
            raw_response: AI 모델의 원시 응답

        Returns:
            Tuple[WasteAnalysisResult, Dict]: (파싱된 결과, 메타데이터)
        """
        try:
            # JSON 추출 시도
            json_data = self._extract_json_from_text(raw_response)
            if not json_data:
                logger.warning("JSON 데이터를 찾을 수 없습니다.")
                return None, {"error": "JSON 형식을 찾을 수 없음", "raw_text": raw_response}

            # 필수 필드 검증
            missing_fields = self._validate_required_fields(json_data)
            if missing_fields:
                logger.warning(f"필수 필드 누락: {missing_fields}")
                return None, {"error": f"필수 필드 누락: {missing_fields}", "raw_json": json_data}

            # 데이터 검증 및 정규화
            validated_data = self._validate_and_normalize_data(json_data)

            # 결과 객체 생성
            result = WasteAnalysisResult(
                object_name=validated_data["object_name"],
                category=validated_data["category"],
                subcategory=validated_data["subcategory"],
                size=validated_data["size"],
                material=validated_data["material"],
                condition=validated_data["condition"],
                disposal_difficulty=validated_data["disposal_difficulty"],
                estimated_dimensions=validated_data["estimated_dimensions"],
                incheon_seogu_notes=validated_data["incheon_seogu_notes"],
                confidence=validated_data["confidence"],
                raw_text=raw_response
            )

            # 메타데이터 생성
            metadata = {
                "parsing_success": True,
                "validation_warnings": validated_data.get("warnings", []),
                "confidence_level": self._get_confidence_level(result.confidence),
                "category_valid": result.category in self.get_main_categories()
            }

            logger.info(f"분석 결과 파싱 성공: {result.object_name} ({result.category})")
            return result, metadata

        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
            return None, {"error": f"JSON 파싱 오류: {e}", "raw_text": raw_response}
        except Exception as e:
            logger.error(f"분석 결과 파싱 중 오류: {e}")
            return None, {"error": f"파싱 오류: {e}", "raw_text": raw_response}

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """텍스트에서 JSON 데이터를 추출합니다."""
        # JSON 코드 블록 패턴 매칭
        json_pattern = r'```json\s*(.*?)\s*```'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # 중괄호로 둘러싸인 JSON 패턴 찾기
            brace_pattern = r'\{.*\}'
            match = re.search(brace_pattern, text, re.DOTALL)
            if match:
                json_str = match.group(0)
            else:
                return None

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 일반적인 JSON 오류 수정 시도
            cleaned_json = self._clean_json_string(json_str)
            try:
                return json.loads(cleaned_json)
            except json.JSONDecodeError:
                return None

    def _clean_json_string(self, json_str: str) -> str:
        """일반적인 JSON 오류를 수정합니다."""
        # 후행 쉼표 제거
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)

        # 잘못된 따옴표 수정
        json_str = json_str.replace('"', '"').replace('"', '"')
        json_str = json_str.replace(''', "'").replace(''', "'")

        return json_str

    def _validate_required_fields(self, json_data: Dict[str, Any]) -> List[str]:
        """필수 필드가 있는지 검증합니다."""
        required_fields = [
            "object_name", "category", "subcategory", "size",
            "material", "condition", "disposal_difficulty",
            "estimated_dimensions", "incheon_seogu_notes", "confidence"
        ]

        missing = [field for field in required_fields if field not in json_data]
        return missing

    def _validate_and_normalize_data(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """데이터를 검증하고 정규화합니다."""
        validated = json_data.copy()
        warnings = []
        valid_categories = self.get_main_categories()

        # 카테고리 검증
        if validated["category"] not in valid_categories:
            warnings.append(f"알 수 없는 카테고리: {validated['category']}")
            # waste_types.json에서 가장 가까운 카테고리 찾기 시도
            best_match, _, score = self.find_best_match(validated.get("object_name", ""))
            if best_match and score > 0.3:
                validated["category"] = best_match
            else:
                validated["category"] = "기타"  # 기본값

        # 크기 검증
        if validated["size"] not in self.valid_sizes:
            warnings.append(f"알 수 없는 크기: {validated['size']}")
            validated["size"] = "중형"  # 기본값

        # 상태 검증
        if validated["condition"] not in self.valid_conditions:
            warnings.append(f"알 수 없는 상태: {validated['condition']}")
            validated["condition"] = "사용감있음"  # 기본값

        # 배출 난이도 검증
        if validated["disposal_difficulty"] not in self.valid_difficulties:
            warnings.append(f"알 수 없는 배출 난이도: {validated['disposal_difficulty']}")
            validated["disposal_difficulty"] = "보통"  # 기본값

        # 신뢰도 검증
        try:
            confidence = float(validated["confidence"])
            if not (0.0 <= confidence <= 1.0):
                warnings.append(f"신뢰도가 범위를 벗어남: {confidence}")
                confidence = max(0.0, min(1.0, confidence))  # 0-1 범위로 제한
            validated["confidence"] = confidence
        except (ValueError, TypeError):
            warnings.append(f"신뢰도 값 오류: {validated['confidence']}")
            validated["confidence"] = 0.5  # 기본값

        # 문자열 필드 정리
        for field in ["object_name", "subcategory", "material", "estimated_dimensions", "incheon_seogu_notes"]:
            if isinstance(validated.get(field), str):
                validated[field] = validated[field].strip()
            else:
                validated[field] = str(validated.get(field, "")).strip()

        if warnings:
            validated["warnings"] = warnings

        return validated

    def _get_confidence_level(self, confidence: float) -> str:
        """신뢰도 수치를 레벨로 변환합니다."""
        if confidence >= 0.8:
            return "높음"
        elif confidence >= 0.6:
            return "보통"
        elif confidence >= 0.4:
            return "낮음"
        else:
            return "매우 낮음"

    def format_result_for_display(self, result: WasteAnalysisResult) -> Dict[str, Any]:
        """사용자 표시용으로 결과를 포맷팅합니다."""
        return {
            "분석_결과": {
                "물체명": result.object_name,
                "대분류": result.category,
                "세분류": result.subcategory,
                "크기": result.size,
                "재질": result.material,
                "상태": result.condition
            },
            "배출_정보": {
                "배출_난이도": result.disposal_difficulty,
                "예상_크기": result.estimated_dimensions,
                "인천서구_안내": result.incheon_seogu_notes
            },
            "분석_신뢰도": f"{result.confidence:.1%} ({self._get_confidence_level(result.confidence)})"
        }