"""
행정구역 데이터 검증 및 정규화 모듈

이 모듈은 행정구역 데이터의 검증, 정규화, 정제 작업을 담당합니다.
CSV 데이터의 필드 정규화, null 값 처리, 데이터 형식 검증 등을 수행합니다.
"""

from typing import Any, Dict, List, Optional
import pandas as pd
from src.app.core.config import DistrictConfig


def normalize_admin_field(value: Any) -> str:
    """
    행정구역 필드를 정규화합니다.

    NaN, None, 빈 문자열 등을 처리하고 문자열로 정규화합니다.

    Args:
        value: 정규화할 값 (Any 타입)

    Returns:
        str: 정규화된 문자열 (빈 값인 경우 빈 문자열 반환)

    Examples:
        >>> normalize_admin_field("서울특별시")
        "서울특별시"
        >>> normalize_admin_field(None)
        ""
        >>> normalize_admin_field("NaN")
        ""
    """
    # None 또는 pandas NaN 처리
    if value is None or pd.isna(value):
        return ""

    # 문자열로 변환 후 공백 제거
    text = str(value).strip()

    # 빈 문자열이거나 "nan" (대소문자 구분 안함) 처리
    if not text or text.lower() == "nan":
        return ""

    return text


def validate_admin_hierarchy(sido: str, sigungu: str, dong: str = "",
                           config: Optional[DistrictConfig] = None) -> bool:
    """
    행정구역 계층구조가 유효한지 검증합니다.

    Args:
        sido: 시도명
        sigungu: 시군구명
        dong: 읍면동명 (선택사항)
        config: 설정 객체

    Returns:
        bool: 유효한 계층구조인지 여부
    """
    config = config or DistrictConfig()

    # 필수 필드 검증
    if not sido or not sigungu:
        return False

    # 기본적인 길이 검증
    if len(sido) > 10 or len(sigungu) > 10:
        return False

    if dong and len(dong) > 10:
        return False

    return True


def clean_admin_code(code: Any) -> str:
    """
    행정구역 코드를 정리합니다.

    Args:
        code: 행정구역 코드

    Returns:
        str: 정리된 코드 (숫자로만 구성)
    """
    if code is None or pd.isna(code):
        return ""

    # 문자열로 변환
    code_str = str(code).strip()

    # 숫자가 아닌 문자 제거
    cleaned_code = ''.join(c for c in code_str if c.isdigit())

    return cleaned_code


def validate_district_row(row_data: dict, config: Optional[DistrictConfig] = None) -> dict:
    """
    행정구역 데이터 행을 검증하고 정규화합니다.

    Args:
        row_data: 행 데이터 딕셔너리
        config: 설정 객체

    Returns:
        dict: 검증 결과와 정규화된 데이터
        {
            'valid': bool,
            'data': dict,
            'errors': list
        }
    """
    config = config or DistrictConfig()
    errors = []

    # 필드 정규화
    sido = normalize_admin_field(row_data.get('시도명', ''))
    sigungu = normalize_admin_field(row_data.get('시군구명', ''))
    dong = normalize_admin_field(row_data.get('읍면동명', ''))
    code = clean_admin_code(row_data.get('법정동코드', ''))

    # 필수 필드 검증
    if not sido:
        errors.append("시도명이 누락되었습니다")
    if not sigungu:
        errors.append("시군구명이 누락되었습니다")
    if not dong:
        errors.append("읍면동명이 누락되었습니다")
    if not code:
        errors.append("법정동코드가 누락되었습니다")

    # 계층구조 검증
    if sido and sigungu and dong:
        if not validate_admin_hierarchy(sido, sigungu, dong, config):
            errors.append("유효하지 않은 행정구역 계층구조입니다")

    # 코드 길이 검증 (법정동코드는 보통 10자리)
    if code and len(code) != 10:
        errors.append(f"법정동코드 길이가 올바르지 않습니다: {len(code)}자리")

    return {
        'valid': len(errors) == 0,
        'data': {
            'sido': sido,
            'sigungu': sigungu,
            'dong': dong,
            'code': code
        },
        'errors': errors
    }


def get_validation_stats(validation_results: list) -> dict:
    """
    검증 결과 통계를 계산합니다.

    Args:
        validation_results: validate_district_row 결과 리스트

    Returns:
        dict: 검증 통계
    """
    total_count = len(validation_results)
    valid_count = sum(1 for result in validation_results if result['valid'])
    invalid_count = total_count - valid_count

    # 오류 유형별 통계
    error_stats = {}
    for result in validation_results:
        for error in result['errors']:
            error_stats[error] = error_stats.get(error, 0) + 1

    return {
        'total_count': total_count,
        'valid_count': valid_count,
        'invalid_count': invalid_count,
        'valid_rate': valid_count / total_count if total_count > 0 else 0,
        'error_stats': error_stats
    }


# 기존 함수명과의 호환성을 위한 별칭
_normalize_admin_field = normalize_admin_field


def validate_csv_data(data: bytes, expected_content_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    다운로드된 데이터가 유효한 CSV 형식인지 확인하고 상세한 검증 결과를 반환합니다.
    
    Args:
        data: 검사할 데이터
        expected_content_patterns: 기대되는 콘텐츠 패턴 리스트
        
    Returns:
        검증 결과 딕셔너리 (is_valid, issues, metadata, content_preview)
    """
    result = {
        'is_valid': False,
        'issues': [],
        'metadata': {},
        'content_preview': '',
        'validation_score': 0  # 0-100 점수
    }
    
    try:
        if not data or len(data) < 10:
            result['issues'].append("데이터가 너무 작습니다 (10바이트 미만)")
            return result
        
        # 기본 메타데이터 수집
        result['metadata']['size_bytes'] = len(data)
        
        # 다양한 인코딩으로 디코딩 시도
        data_str = None
        detected_encoding = None
        
        encodings = ['utf-8-sig', 'utf-8', 'euc-kr', 'cp949', 'latin1']
        for encoding in encodings:
            try:
                data_str = data[:2000].decode(encoding, errors='ignore')
                detected_encoding = encoding
                break
            except:
                continue
        
        if not data_str:
            result['issues'].append("텍스트 디코딩 실패 - 바이너리 파일일 가능성")
            return result
        
        result['metadata']['detected_encoding'] = detected_encoding
        result['content_preview'] = data_str[:500] + ('...' if len(data_str) > 500 else '')
        
        data_lower = data_str.lower()
        lines = data_str.split('\n')
        result['metadata']['line_count'] = len(lines)
        
        # 1. HTML/XML/JSON 형식 검사
        html_tags = ['<html', '<body', '<div', '<!doctype', '<head', '<meta']
        xml_tags = ['<?xml', '<root', '<response']
        
        if any(tag in data_lower for tag in html_tags):
            result['issues'].append("HTML 문서로 감지됨 - CSV가 아님")
            result['validation_score'] = 0
            return result
        
        if any(tag in data_lower for tag in xml_tags):
            result['issues'].append("XML 문서로 감지됨 - CSV가 아님") 
            result['validation_score'] = 0
            return result
        
        if data_str.strip().startswith(('{', '[')):
            result['issues'].append("JSON 형식으로 감지됨 - CSV가 아님")
            result['validation_score'] = 0
            return result
        
        # 2. 에러 메시지 확인
        error_patterns = ['error', '오류', '404', '500', 'not found', 'access denied']
        if any(pattern in data_lower for pattern in error_patterns):
            result['issues'].append(f"오류 메시지 감지: {[p for p in error_patterns if p in data_lower]}")
            result['validation_score'] = 10
        
        # 3. CSV 구조 검증
        score = 0
        
        # 구분자 일관성 검사
        delimiters = [',', '\t', '|', ';']
        delimiter_scores = {}
        
        for delimiter in delimiters:
            line_counts = []
            for i, line in enumerate(lines[:10]):  # 처음 10줄만 검사
                if line.strip():
                    count = line.count(delimiter)
                    line_counts.append(count)
            
            if len(line_counts) >= 2:
                # 일관성 점수 계산
                avg_count = sum(line_counts) / len(line_counts)
                if avg_count >= 1:  # 최소 1개 구분자 필요
                    variance = sum((c - avg_count) ** 2 for c in line_counts) / len(line_counts)
                    consistency = max(0, 10 - variance)  # 분산이 낮을수록 좋음
                    delimiter_scores[delimiter] = (avg_count, consistency)
        
        best_delimiter = None
        best_score = 0
        if delimiter_scores:
            best_delimiter = max(delimiter_scores.keys(), 
                               key=lambda d: delimiter_scores[d][1])
            best_score = delimiter_scores[best_delimiter][1]
            score += min(30, best_score * 3)  # 최대 30점
        
        result['metadata']['best_delimiter'] = best_delimiter
        result['metadata']['delimiter_consistency_score'] = best_score
        
        # 4. 헤더 검증
        if lines and best_delimiter:
            first_line = lines[0].strip()
            if first_line:
                headers = [h.strip().strip('"\'') for h in first_line.split(best_delimiter)]
                result['metadata']['header_count'] = len(headers)
                result['metadata']['headers'] = headers[:10]  # 처음 10개만
                
                if len(headers) >= 3:
                    score += 20  # 충분한 컬럼 수
                
                # 한글 헤더 확인 (한국 공공데이터 특징)
                if any(ord(char) > 127 for char in first_line):
                    score += 10
        
        # 5. 예상 콘텐츠 패턴 검증
        if not expected_content_patterns:
            expected_content_patterns = ['법정동코드', '시도명', '시군구명']
        
        found_patterns = []
        for pattern in expected_content_patterns:
            if pattern in data_str:
                found_patterns.append(pattern)
                score += 15  # 각 패턴당 15점
        
        result['metadata']['found_patterns'] = found_patterns
        result['metadata']['missing_patterns'] = [p for p in expected_content_patterns if p not in found_patterns]
        
        # 6. 데이터 품질 검증
        if len(lines) >= 2:
            score += 10  # 여러 줄 데이터
        
        if len(lines) >= 10:
            score += 10  # 충분한 데이터
        
        # 최종 점수 및 유효성 판정
        result['validation_score'] = min(100, score)
        
        # 유효성 기준 (60점 이상)
        if score >= 60:
            result['is_valid'] = True
        elif score >= 40:
            result['issues'].append(f"부분적으로 유효함 (점수: {score}/100)")
        else:
            result['issues'].append(f"유효하지 않은 CSV (점수: {score}/100)")
        
        # 경고 메시지
        if not found_patterns:
            result['issues'].append("예상되는 콘텐츠 패턴이 발견되지 않음")
        
        if not best_delimiter:
            result['issues'].append("일관된 구분자를 찾을 수 없음")
        
        return result
        
    except Exception as e:
        result['issues'].append(f"검증 중 오류: {str(e)}")
        return result
