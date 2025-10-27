"""
라벨링 서비스 - 이미지 분석 결과를 학습 데이터로 저장하고 관리합니다.

이미지 파일을 저장하고 분류, 크기 정보를 JSON 라벨로 저장하여
향후 이미지 분석 모델 학습에 활용하기 위한 서비스입니다.
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from src.app.core.base_service import BaseService
from src.app.core.config import Config

logger = logging.getLogger(__name__)


class LabelingService(BaseService):
    """
    이미지 분석 결과를 라벨링 데이터로 저장하는 서비스입니다.

    역할:
    1. 이미지를 /uploads/user_images/ 에 저장
    2. 분류 및 크기 정보를 JSON으로 /uploads/labels/ 에 저장
    3. 라벨링 데이터 인덱스 관리
    4. 분류별 라벨링 데이터 조회
    """

    def __init__(self, config: Config):
        super().__init__(config)
        # uploads 디렉토리의 상대 경로 설정
        # 현재 파일 기준으로 프로젝트 루트를 계산
        # src/domains/analysis/services/labeling_service.py -> 4단계 상위가 프로젝트 루트
        current_file = Path(__file__).resolve()
        project_root = current_file.parents[4]  # src/domains/analysis/services/labeling_service.py의 4단계 상위

        self.base_path = project_root / 'uploads'
        self.images_dir = self.base_path / 'user_images'
        self.labels_dir = self.base_path / 'labels'
        self.index_file = self.base_path / 'labels' / '_index.json'

        # 디렉토리 생성
        self._ensure_directories()

        # 라벨 인덱스 로드
        self.label_index = self._load_index()

    def get_service_name(self) -> str:
        """서비스 이름을 반환합니다."""
        return "LabelingService"

    def get_service_version(self) -> str:
        """서비스 버전을 반환합니다."""
        return "1.0.0"

    def get_service_description(self) -> str:
        """서비스 설명을 반환합니다."""
        return "이미지 분석 결과를 라벨링 학습 데이터로 저장 및 관리하는 서비스"

    def _ensure_directories(self) -> None:
        """필요한 디렉토리를 생성합니다."""
        try:
            self.images_dir.mkdir(parents=True, exist_ok=True)
            self.labels_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Labeling directories ensured: {self.images_dir}, {self.labels_dir}")
        except Exception as e:
            logger.error(f"Failed to create labeling directories: {e}")
            raise

    def _load_index(self) -> Dict[str, Any]:
        """라벨 인덱스를 로드합니다."""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load index file: {e}")

        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "total_labels": 0,
            "labels_by_category": {},
            "labels": []
        }

    def _save_index(self) -> None:
        """라벨 인덱스를 저장합니다."""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.label_index, f, indent=2, ensure_ascii=False)
            logger.info(f"Index saved with {self.label_index['total_labels']} labels")
        except Exception as e:
            logger.error(f"Failed to save index file: {e}")

    def save_label(
        self,
        image_bytes: bytes,
        analysis_result: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        이미지와 라벨 메타데이터를 저장합니다.

        Args:
            image_bytes: 이미지 바이트 데이터
            analysis_result: 분석 결과 (분류, 크기 등)
            user_feedback: 사용자 피드백 (선택사항)

        Returns:
            저장 결과 (성공 여부, file_id 등)
        """
        try:
            # 1. 고유 ID 생성
            file_id = str(uuid.uuid4())

            # 2. 이미지 저장
            image_path = self._save_image(file_id, image_bytes)

            # 3. 라벨 메타데이터 생성
            label_data = self._create_label_metadata(
                file_id=file_id,
                image_path=str(image_path),
                analysis_result=analysis_result,
                user_feedback=user_feedback
            )

            # 4. 라벨 파일 저장
            label_file_path = self._save_label_file(file_id, label_data)

            # 5. 인덱스 업데이트
            self._update_index(label_data)

            logger.info(f"Label saved successfully: {file_id}")

            return {
                'success': True,
                'file_id': file_id,
                'image_path': str(image_path),
                'label_path': str(label_file_path),
                'message': f'라벨링 데이터가 저장되었습니다. (ID: {file_id})'
            }

        except Exception as e:
            logger.error(f"Failed to save label: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': '라벨링 데이터 저장 중 오류가 발생했습니다.'
            }

    def _save_image(self, file_id: str, image_bytes: bytes) -> Path:
        """이미지 파일을 저장합니다."""
        image_path = self.images_dir / f"{file_id}.jpg"
        with open(image_path, 'wb') as f:
            f.write(image_bytes)
        logger.debug(f"Image saved: {image_path}")
        return image_path

    def _create_label_metadata(
        self,
        file_id: str,
        image_path: str,
        analysis_result: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """라벨 메타데이터를 생성합니다."""

        dimensions = analysis_result.get('dimensions', {})

        # AI 추론 결과 추출
        ai_inference = self._extract_ai_inference(analysis_result)

        label_data = {
            "file_id": file_id,
            "image_path": image_path,
            "timestamp": datetime.now().isoformat(),
            "classification": {
                "primary_category": analysis_result.get('primary_category', 'MISC'),
                "primary_category_name": self._get_category_name(
                    analysis_result.get('primary_category', 'MISC')
                ),
                "secondary_category": analysis_result.get('secondary_category', 'MISC_UNCLASS'),
                "secondary_category_name": analysis_result.get('object_name', '알 수 없음'),
                "object_name": analysis_result.get('object_name', '알 수 없음'),
                "is_object_name_corrected": analysis_result.get('is_object_name_corrected', False)
            },
            "dimensions": {
                "w_cm": dimensions.get('w_cm') or dimensions.get('width_cm'),
                "h_cm": dimensions.get('h_cm') or dimensions.get('height_cm'),
                "d_cm": dimensions.get('d_cm') or dimensions.get('depth_cm')
            },
            "confidence": analysis_result.get('confidence', 0.0),
            "reasoning": analysis_result.get('reasoning', ''),
            "ai_inference": ai_inference,  # AI 추론 결과 추가
            "user_feedback": user_feedback or {},
            "metadata": {
                "labeling_quality": self._calculate_labeling_quality(analysis_result, user_feedback),
                "ai_inference_quality": self._calculate_ai_inference_quality(ai_inference)
            }
        }

        return label_data

    def _extract_ai_inference(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """AI 추론 결과를 추출합니다."""
        raw_response = analysis_result.get('raw_response', {})

        return {
            "object_name": analysis_result.get('object_name', '알 수 없음'),
            "primary_category": analysis_result.get('primary_category', 'MISC'),
            "secondary_category": analysis_result.get('secondary_category', 'MISC_UNCLASS'),
            "confidence": analysis_result.get('confidence', 0.0),
            "reasoning": analysis_result.get('reasoning', ''),
            "dimensions": analysis_result.get('dimensions', {}),
            "raw_response": raw_response,
            "inference_timestamp": datetime.now().isoformat()
        }

    def _calculate_ai_inference_quality(self, ai_inference: Dict[str, Any]) -> float:
        """AI 추론 결과의 품질 점수를 계산합니다 (0.0 ~ 1.0)."""
        score = 0.0

        # 신뢰도 (0.5점)
        confidence = ai_inference.get('confidence', 0.0)
        score += min(confidence, 1.0) * 0.5

        # 크기 정보 (0.3점)
        dimensions = ai_inference.get('dimensions', {})
        if any(dimensions.get(k) for k in ['w_cm', 'h_cm', 'd_cm', 'width_cm', 'height_cm', 'depth_cm']):
            score += 0.3

        # 추론 정보 (0.2점)
        if ai_inference.get('reasoning'):
            score += 0.2

        return min(score, 1.0)

    def _get_category_name(self, category_code: str) -> str:
        """카테고리 코드를 한글 이름으로 변환합니다."""
        category_names = {
            'FURN': '가구',
            'APPL': '가전',
            'HLTH': '건강/의료용품',
            'LIFE': '생활/주방용품',
            'SPOR': '스포츠/레저',
            'MUSC': '악기',
            'HOBB': '조경/장식',
            'MISC': '기타'
        }
        return category_names.get(category_code, category_code)

    def _calculate_labeling_quality(
        self,
        analysis_result: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]] = None
    ) -> float:
        """라벨링 품질 점수를 계산합니다 (0.0 ~ 1.0)."""
        score = 0.0

        # 신뢰도 (0.4점)
        confidence = analysis_result.get('confidence', 0.0)
        score += min(confidence, 1.0) * 0.4

        # 크기 정보 (0.3점)
        dimensions = analysis_result.get('dimensions', {})
        if any(dimensions.get(k) for k in ['w_cm', 'h_cm', 'd_cm', 'width_cm', 'height_cm', 'depth_cm']):
            score += 0.3

        # 사용자 피드백 (0.3점)
        if user_feedback and user_feedback.get('notes'):
            score += 0.3

        return min(score, 1.0)

    def _save_label_file(self, file_id: str, label_data: Dict[str, Any]) -> Path:
        """라벨 JSON 파일을 저장합니다."""
        label_path = self.labels_dir / f"{file_id}.json"
        with open(label_path, 'w', encoding='utf-8') as f:
            json.dump(label_data, f, indent=2, ensure_ascii=False)
        logger.debug(f"Label file saved: {label_path}")
        return label_path

    def _update_index(self, label_data: Dict[str, Any]) -> None:
        """라벨 인덱스를 업데이트합니다."""
        # 라벨 추가
        self.label_index['labels'].append({
            'file_id': label_data['file_id'],
            'timestamp': label_data['timestamp'],
            'primary_category': label_data['classification']['primary_category'],
            'secondary_category': label_data['classification']['secondary_category'],
            'object_name': label_data['classification']['object_name'],
            'confidence': label_data['confidence'],
            'labeling_quality': label_data['metadata']['labeling_quality']
        })

        # 카테고리별 인덱스 업데이트
        primary = label_data['classification']['primary_category']
        if primary not in self.label_index['labels_by_category']:
            self.label_index['labels_by_category'][primary] = {
                'count': 0,
                'subcategories': {}
            }

        secondary = label_data['classification']['secondary_category']
        if secondary not in self.label_index['labels_by_category'][primary]['subcategories']:
            self.label_index['labels_by_category'][primary]['subcategories'][secondary] = 0

        self.label_index['labels_by_category'][primary]['count'] += 1
        self.label_index['labels_by_category'][primary]['subcategories'][secondary] += 1
        self.label_index['total_labels'] += 1

        # 인덱스 저장
        self._save_index()

    def get_labels_by_primary_category(self, primary_category: str) -> List[Dict[str, Any]]:
        """주 카테고리별 라벨링 데이터를 조회합니다."""
        labels = []
        try:
            for label in self.label_index['labels']:
                if label['primary_category'] == primary_category:
                    # 라벨 파일 로드
                    label_file = self.labels_dir / f"{label['file_id']}.json"
                    if label_file.exists():
                        with open(label_file, 'r', encoding='utf-8') as f:
                            label_data = json.load(f)
                            labels.append(label_data)
        except Exception as e:
            logger.error(f"Failed to get labels by primary category: {e}")

        return labels

    def get_labels_by_secondary_category(
        self,
        primary_category: str,
        secondary_category: str
    ) -> List[Dict[str, Any]]:
        """주 카테고리와 세부 카테고리별 라벨링 데이터를 조회합니다."""
        labels = []
        try:
            for label in self.label_index['labels']:
                if (label['primary_category'] == primary_category and
                    label['secondary_category'] == secondary_category):
                    # 라벨 파일 로드
                    label_file = self.labels_dir / f"{label['file_id']}.json"
                    if label_file.exists():
                        with open(label_file, 'r', encoding='utf-8') as f:
                            label_data = json.load(f)
                            labels.append(label_data)
        except Exception as e:
            logger.error(f"Failed to get labels by secondary category: {e}")

        return labels

    def get_category_statistics(self) -> Dict[str, Any]:
        """카테고리별 라벨링 통계를 조회합니다."""
        return {
            'total_labels': self.label_index['total_labels'],
            'by_primary_category': self.label_index['labels_by_category'],
            'created_at': self.label_index.get('created_at'),
            'last_updated': datetime.now().isoformat()
        }

    def get_label_details(self, file_id: str) -> Optional[Dict[str, Any]]:
        """특정 라벨의 상세 정보를 조회합니다."""
        try:
            label_file = self.labels_dir / f"{file_id}.json"
            if label_file.exists():
                with open(label_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to get label details: {e}")

        return None

    def get_image_path(self, file_id: str) -> Optional[Path]:
        """라벨의 이미지 경로를 조회합니다."""
        image_path = self.images_dir / f"{file_id}.jpg"
        return image_path if image_path.exists() else None

    def delete_label(self, file_id: str) -> Dict[str, Any]:
        """
        특정 라벨과 이미지를 삭제합니다.

        Args:
            file_id: 삭제할 라벨의 파일 ID

        Returns:
            삭제 결과 (성공 여부 등)
        """
        try:
            # 1. 이미지 파일 삭제
            image_path = self.images_dir / f"{file_id}.jpg"
            if image_path.exists():
                image_path.unlink()
                logger.info(f"Image deleted: {image_path}")

            # 2. 라벨 파일 삭제
            label_path = self.labels_dir / f"{file_id}.json"
            if label_path.exists():
                label_path.unlink()
                logger.info(f"Label file deleted: {label_path}")

            # 3. 인덱스에서 제거
            self._remove_from_index(file_id)

            logger.info(f"Label deleted successfully: {file_id}")

            return {
                'success': True,
                'file_id': file_id,
                'message': f'라벨링 데이터가 삭제되었습니다. (ID: {file_id})'
            }

        except Exception as e:
            logger.error(f"Failed to delete label: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': '라벨링 데이터 삭제 중 오류가 발생했습니다.'
            }

    def delete_labels_by_primary_category(self, primary_category: str) -> Dict[str, Any]:
        """
        주 카테고리의 모든 라벨링 데이터를 삭제합니다.

        Args:
            primary_category: 삭제할 주 카테고리

        Returns:
            삭제 결과 (성공 여부, 삭제된 개수 등)
        """
        try:
            deleted_count = 0
            file_ids_to_delete = [
                label['file_id'] for label in self.label_index['labels']
                if label['primary_category'] == primary_category
            ]

            for file_id in file_ids_to_delete:
                result = self.delete_label(file_id)
                if result['success']:
                    deleted_count += 1

            logger.info(f"Deleted {deleted_count} labels from category: {primary_category}")

            return {
                'success': True,
                'deleted_count': deleted_count,
                'message': f'{primary_category} 분류의 {deleted_count}개 라벨링 데이터가 삭제되었습니다.'
            }

        except Exception as e:
            logger.error(f"Failed to delete labels by category: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': '카테고리 라벨링 데이터 삭제 중 오류가 발생했습니다.'
            }

    def delete_labels_by_secondary_category(
        self,
        primary_category: str,
        secondary_category: str
    ) -> Dict[str, Any]:
        """
        주 카테고리와 세부 카테고리의 모든 라벨링 데이터를 삭제합니다.

        Args:
            primary_category: 삭제할 주 카테고리
            secondary_category: 삭제할 세부 카테고리

        Returns:
            삭제 결과 (성공 여부, 삭제된 개수 등)
        """
        try:
            deleted_count = 0
            file_ids_to_delete = [
                label['file_id'] for label in self.label_index['labels']
                if (label['primary_category'] == primary_category and
                    label['secondary_category'] == secondary_category)
            ]

            for file_id in file_ids_to_delete:
                result = self.delete_label(file_id)
                if result['success']:
                    deleted_count += 1

            logger.info(f"Deleted {deleted_count} labels from category: {primary_category}/{secondary_category}")

            return {
                'success': True,
                'deleted_count': deleted_count,
                'message': f'{primary_category}/{secondary_category} 분류의 {deleted_count}개 라벨링 데이터가 삭제되었습니다.'
            }

        except Exception as e:
            logger.error(f"Failed to delete labels by secondary category: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': '세부 카테고리 라벨링 데이터 삭제 중 오류가 발생했습니다.'
            }

    def delete_all_labels(self) -> Dict[str, Any]:
        """
        모든 라벨링 데이터를 삭제합니다. (테스트/개발용)

        Returns:
            삭제 결과 (성공 여부, 삭제된 개수 등)
        """
        try:
            deleted_count = 0
            file_ids_to_delete = [label['file_id'] for label in self.label_index['labels']]

            for file_id in file_ids_to_delete:
                result = self.delete_label(file_id)
                if result['success']:
                    deleted_count += 1

            logger.warning(f"Deleted all {deleted_count} labels")

            return {
                'success': True,
                'deleted_count': deleted_count,
                'message': f'전체 {deleted_count}개의 라벨링 데이터가 삭제되었습니다.'
            }

        except Exception as e:
            logger.error(f"Failed to delete all labels: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': '모든 라벨링 데이터 삭제 중 오류가 발생했습니다.'
            }

    def _remove_from_index(self, file_id: str) -> None:
        """인덱스에서 라벨을 제거합니다."""
        try:
            # labels 리스트에서 제거
            label_to_remove = None
            for label in self.label_index['labels']:
                if label['file_id'] == file_id:
                    label_to_remove = label
                    break

            if label_to_remove:
                self.label_index['labels'].remove(label_to_remove)

                # 카테고리별 인덱스 업데이트
                primary = label_to_remove['primary_category']
                secondary = label_to_remove['secondary_category']

                if primary in self.label_index['labels_by_category']:
                    cat_info = self.label_index['labels_by_category'][primary]
                    cat_info['count'] -= 1

                    if secondary in cat_info['subcategories']:
                        cat_info['subcategories'][secondary] -= 1

                        # 서브카테고리 개수가 0이 되면 제거
                        if cat_info['subcategories'][secondary] == 0:
                            del cat_info['subcategories'][secondary]

                    # 주 카테고리 개수가 0이 되면 제거
                    if cat_info['count'] == 0:
                        del self.label_index['labels_by_category'][primary]

                self.label_index['total_labels'] -= 1

                # 인덱스 저장
                self._save_index()
                logger.debug(f"Index updated after deleting: {file_id}")

        except Exception as e:
            logger.error(f"Failed to remove from index: {e}")
            raise
