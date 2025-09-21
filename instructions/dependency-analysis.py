#!/usr/bin/env python3
"""
district_service.py 함수 의존성 분석 스크립트
"""
import re

def analyze_dependencies():
    """함수 간 의존성을 분석합니다."""

    with open('src/services/district_service.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 함수 정의 추출
    function_pattern = r'def ([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
    functions = re.findall(function_pattern, content)

    print("=== 발견된 함수들 ===")
    for i, func in enumerate(functions, 1):
        print(f"{i:2d}. {func}")

    print(f"\n총 {len(functions)}개 함수 발견")

    # 함수별 의존성 분석
    print("\n=== 함수별 호출 관계 ===")
    dependencies = {}

    # 각 함수 영역별로 분석
    function_blocks = re.split(r'\ndef ', content)

    for i, block in enumerate(function_blocks[1:], 0):  # 첫 번째는 import 부분이므로 제외
        if i < len(functions):
            current_func = functions[i]
            called_functions = []

            # 이 블록에서 다른 함수 호출 찾기
            for func in functions:
                if func != current_func:
                    # 함수 호출 패턴 찾기
                    call_pattern = rf'\b{func}\s*\('
                    if re.search(call_pattern, block):
                        called_functions.append(func)

            dependencies[current_func] = called_functions

            if called_functions:
                print(f"{current_func} → {', '.join(called_functions)}")
            else:
                print(f"{current_func} → (독립적)")

    # 외부 의존성 분석
    print("\n=== 외부 모듈 의존성 ===")
    external_calls = {}

    for i, block in enumerate(function_blocks[1:], 0):
        if i < len(functions):
            current_func = functions[i]
            externals = []

            # 로깅 함수들
            if re.search(r'log_', block):
                externals.append('logging')

            # 설정 관련
            if re.search(r'config\.', block):
                externals.append('config')

            # 파일 검증
            if re.search(r'validate_downloaded_file|detect_website_changes', block):
                externals.append('file_validator')

            # pandas 관련
            if re.search(r'pd\.|DataFrame', block):
                externals.append('pandas')

            # requests 관련
            if re.search(r'requests\.|session\.', block):
                externals.append('requests')

            external_calls[current_func] = externals

            if externals:
                print(f"{current_func} → {', '.join(externals)}")

    return functions, dependencies, external_calls

def categorize_functions(functions, dependencies, external_calls):
    """함수들을 기능별로 분류합니다."""

    print("\n=== 기능별 함수 분류 ===")

    # 데이터 로딩 관련 (CSV 파싱, 웹 다운로드)
    data_loading = []
    # 파일 관리 관련 (파일 목록, 삭제, 미리보기)
    file_management = []
    # 업데이트 관리 관련 (자동 업데이트, 업데이트 체크)
    update_management = []
    # 데이터 검증 관련 (CSV 검증, 데이터 정규화)
    data_validation = []

    for func in functions:
        if any(keyword in func.lower() for keyword in ['parse', 'csv', 'download', 'extract', 'try_']):
            data_loading.append(func)
        elif any(keyword in func.lower() for keyword in ['files', 'delete', 'preview', 'latest']):
            file_management.append(func)
        elif any(keyword in func.lower() for keyword in ['update', 'check', 'save', 'force']):
            update_management.append(func)
        elif any(keyword in func.lower() for keyword in ['validate', 'process', 'normalize']):
            data_validation.append(func)
        else:
            # 애매한 경우 내용으로 판단
            if func in ['get_last_update_info', 'save_update_info', 'clear_update_info']:
                update_management.append(func)
            else:
                data_loading.append(func)  # 기본적으로 데이터 로딩으로

    print("1. 데이터 로딩 (Data Loading):")
    for func in data_loading:
        print(f"   - {func}")

    print("\n2. 파일 관리 (File Management):")
    for func in file_management:
        print(f"   - {func}")

    print("\n3. 업데이트 관리 (Update Management):")
    for func in update_management:
        print(f"   - {func}")

    print("\n4. 데이터 검증 (Data Validation):")
    for func in data_validation:
        print(f"   - {func}")

    return {
        'data_loading': data_loading,
        'file_management': file_management,
        'update_management': update_management,
        'data_validation': data_validation
    }

if __name__ == "__main__":
    functions, dependencies, external_calls = analyze_dependencies()
    categories = categorize_functions(functions, dependencies, external_calls)