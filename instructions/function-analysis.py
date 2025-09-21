#!/usr/bin/env python3
"""
district_service.py 함수 분석 스크립트
"""

def analyze_functions():
    """함수별 라인 수와 의존성을 분석합니다."""

    with open('src/services/district_service.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    functions = []
    current_func = None

    for i, line in enumerate(lines, 1):
        if line.strip().startswith('def '):
            if current_func:
                current_func['end_line'] = i - 1
                current_func['line_count'] = current_func['end_line'] - current_func['start_line'] + 1

            func_name = line.strip().split('(')[0].replace('def ', '')
            current_func = {
                'name': func_name,
                'start_line': i,
                'end_line': None,
                'line_count': 0
            }
            functions.append(current_func)

    # 마지막 함수 처리
    if current_func:
        current_func['end_line'] = len(lines)
        current_func['line_count'] = current_func['end_line'] - current_func['start_line'] + 1

    # 함수별 라인 수 출력
    print("=== 함수별 라인 수 분석 ===")
    total_lines = 0
    for func in functions:
        print(f"{func['name']}: {func['line_count']}줄 (라인 {func['start_line']}-{func['end_line']})")
        total_lines += func['line_count']

    print(f"\n총 함수 라인 수: {total_lines}줄")
    print(f"전체 파일 라인 수: {len(lines)}줄")
    print(f"함수 외 라인 수: {len(lines) - total_lines}줄")

if __name__ == "__main__":
    analyze_functions()