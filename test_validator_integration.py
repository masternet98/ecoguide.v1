#!/usr/bin/env python3
"""
district_validator 통합 테스트 스크립트

district_validator.py의 검증 기능들이 district_service.py에 제대로 통합되었는지 확인합니다.
"""

import sys
import os
import pandas as pd
from io import StringIO

# 프로젝트 루트를 path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.domains.district.services.district_validator import (
    normalize_admin_field, validate_district_row, get_validation_stats,
    validate_admin_hierarchy, clean_admin_code
)
from src.app.core.config import DistrictConfig

def test_normalize_admin_field():
    """normalize_admin_field 함수 테스트"""
    print("=== normalize_admin_field 테스트 ===")

    test_cases = [
        ("서울특별시", "서울특별시"),
        (None, ""),
        ("", ""),
        ("nan", ""),
        ("NaN", ""),
        ("  강남구  ", "강남구"),
        (123, "123")
    ]

    for input_val, expected in test_cases:
        result = normalize_admin_field(input_val)
        status = "✅" if result == expected else "❌"
        print(f"{status} Input: {repr(input_val)} → Output: {repr(result)} (Expected: {repr(expected)})")

    print()

def test_validate_admin_hierarchy():
    """validate_admin_hierarchy 함수 테스트"""
    print("=== validate_admin_hierarchy 테스트 ===")

    test_cases = [
        ("서울특별시", "강남구", "역삼동", True),
        ("서울특별시", "강남구", "", True),
        ("", "강남구", "역삼동", False),
        ("서울특별시", "", "역삼동", False),
        ("서울특별시" * 5, "강남구", "역삼동", False),  # 너무 긴 이름
    ]

    for sido, sigungu, dong, expected in test_cases:
        result = validate_admin_hierarchy(sido, sigungu, dong)
        status = "✅" if result == expected else "❌"
        print(f"{status} 시도: {sido[:10]}..., 시군구: {sigungu}, 동: {dong} → {result} (Expected: {expected})")

    print()

def test_clean_admin_code():
    """clean_admin_code 함수 테스트"""
    print("=== clean_admin_code 테스트 ===")

    test_cases = [
        ("1168010100", "1168010100"),
        ("1168-010-100", "1168010100"),
        ("1168010100.0", "1168010100"),
        (None, ""),
        ("abc123def", "123"),
        ("", "")
    ]

    for input_val, expected in test_cases:
        result = clean_admin_code(input_val)
        status = "✅" if result == expected else "❌"
        print(f"{status} Input: {repr(input_val)} → Output: {repr(result)} (Expected: {repr(expected)})")

    print()

def test_validate_district_row():
    """validate_district_row 함수 테스트"""
    print("=== validate_district_row 테스트 ===")

    # 유효한 데이터
    valid_row = {
        '시도명': '서울특별시',
        '시군구명': '강남구',
        '읍면동명': '역삼동',
        '법정동코드': '1168010100'
    }

    result = validate_district_row(valid_row)
    print(f"✅ 유효한 데이터: valid={result['valid']}, errors={result['errors']}")

    # 무효한 데이터 (시도명 누락)
    invalid_row = {
        '시도명': '',
        '시군구명': '강남구',
        '읍면동명': '역삼동',
        '법정동코드': '1168010100'
    }

    result = validate_district_row(invalid_row)
    print(f"❌ 무효한 데이터: valid={result['valid']}, errors={result['errors']}")

    print()

def test_get_validation_stats():
    """get_validation_stats 함수 테스트"""
    print("=== get_validation_stats 테스트 ===")

    validation_results = [
        {'valid': True, 'errors': []},
        {'valid': True, 'errors': []},
        {'valid': False, 'errors': ['시도명이 누락되었습니다']},
        {'valid': False, 'errors': ['시군구명이 누락되었습니다', '법정동코드가 누락되었습니다']},
    ]

    stats = get_validation_stats(validation_results)
    print(f"전체: {stats['total_count']}")
    print(f"유효: {stats['valid_count']}")
    print(f"무효: {stats['invalid_count']}")
    print(f"유효율: {stats['valid_rate']:.2%}")
    print(f"오류 통계: {stats['error_stats']}")

    print()

def test_import_integration():
    """district_service.py에서 import가 제대로 되는지 테스트"""
    print("=== Import 통합 테스트 ===")

    try:
        from src.domains.district.services.district_service import (
            normalize_admin_field, validate_district_row, get_validation_stats,
            validate_admin_hierarchy, clean_admin_code
        )
        print("✅ district_service.py에서 모든 함수 import 성공")

        # 간단한 함수 호출 테스트
        result = normalize_admin_field("서울특별시")
        print(f"✅ normalize_admin_field 호출 성공: {result}")

    except ImportError as e:
        print(f"❌ Import 실패: {e}")

    print()

def main():
    """모든 테스트 실행"""
    print("🔍 District Validator 통합 테스트 시작\n")

    test_normalize_admin_field()
    test_validate_admin_hierarchy()
    test_clean_admin_code()
    test_validate_district_row()
    test_get_validation_stats()
    test_import_integration()

    print("🎉 모든 테스트 완료!")

if __name__ == "__main__":
    main()