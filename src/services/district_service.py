"""
행정구역 데이터 처리를 위한 서비스 모듈입니다.
CSV 파일을 업로드하여 시군구명 기준으로 중복 제거 후 JSON으로 변환합니다.
data.go.kr에서 자동 업데이트 기능도 제공합니다.
"""
import csv
import json
import os
import io
import re
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup

# 로깅 시스템 import
from src.core.logger import (
    logger, log_function, log_step, log_info, log_warning, log_error, 
    LogLevel, LogCategory
)

# 파일 검증 시스템 import
from .file_source_validator import validate_downloaded_file, detect_website_changes

# Config 시스템 import
from src.core.config import DistrictConfig


def manual_csv_parse(csv_string: str) -> Optional[pd.DataFrame]:
    """
    표준 CSV 파싱이 실패했을 때 수동으로 CSV를 파싱합니다.
    
    Args:
        csv_string: CSV 문자열
        
    Returns:
        파싱된 DataFrame 또는 None
    """
    try:
        lines = csv_string.strip().split('\n')
        if len(lines) < 2:
            return None
        
        # 첫 번째 줄에서 구분자 추측
        first_line = lines[0]
        delimiters = [',', '\t', '|', ';']
        best_delimiter = ','
        max_fields = 0
        
        for delimiter in delimiters:
            field_count = len(first_line.split(delimiter))
            if field_count > max_fields:
                max_fields = field_count
                best_delimiter = delimiter
        
        # 수동으로 라인별 파싱
        data = []
        headers = None
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
                
            # 간단한 필드 분할 (따옴표 처리 포함)
            fields = []
            current_field = ""
            in_quotes = False
            quote_char = None
            
            for char in line:
                if char in ['"', "'"] and (quote_char is None or char == quote_char):
                    if not in_quotes:
                        in_quotes = True
                        quote_char = char
                    elif char == quote_char:
                        in_quotes = False
                        quote_char = None
                elif char == best_delimiter and not in_quotes:
                    fields.append(current_field.strip())
                    current_field = ""
                else:
                    current_field += char
            
            # 마지막 필드 추가
            fields.append(current_field.strip())
            
            # 빈 필드 제거 및 정리
            fields = [field.strip('"\'') for field in fields]
            
            if i == 0:
                headers = fields
            else:
                # 헤더와 필드 수가 다르면 조정
                while len(fields) < len(headers):
                    fields.append("")
                fields = fields[:len(headers)]  # 초과 필드 제거
                
                data.append(fields)
        
        if headers and data:
            df = pd.DataFrame(data, columns=headers)
            return df if len(df) > 0 else None
        
        return None
        
    except Exception as e:
        print(f"수동 파싱 오류: {e}")
        return None


def detect_csv_format(csv_string: str) -> Dict[str, Any]:
    """
    CSV 형식을 자동으로 감지합니다.
    
    Args:
        csv_string: CSV 문자열
        
    Returns:
        감지된 형식 정보
    """
    sample_lines = csv_string.split('\n')[:10]  # 처음 10줄만 분석
    
    # 구분자 감지
    delimiters = [',', '\t', '|', ';']
    delimiter_scores = {}
    
    for delimiter in delimiters:
        scores = []
        for line in sample_lines:
            if line.strip():
                scores.append(len(line.split(delimiter)))
        
        if scores:
            # 일관성 점수 (표준편차가 낮을수록 좋음)
            avg_fields = sum(scores) / len(scores)
            if avg_fields > 1:  # 최소 2개 필드 필요
                variance = sum((x - avg_fields) ** 2 for x in scores) / len(scores)
                delimiter_scores[delimiter] = (avg_fields, 1 / (variance + 1))
    
    best_delimiter = ','
    if delimiter_scores:
        best_delimiter = max(delimiter_scores.keys(), 
                           key=lambda d: delimiter_scores[d][1])
    
    # 인코딩 힌트
    has_korean = any(ord(char) > 127 for char in csv_string[:1000])
    
    return {
        'delimiter': best_delimiter,
        'has_korean': has_korean,
        'sample_field_count': delimiter_scores.get(best_delimiter, (0, 0))[0]
    }


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


@log_function(LogCategory.CSV_PROCESSING, "CSV_처리_전체", include_args=False, include_result=False)
def process_district_csv(csv_content: bytes, output_filename: Optional[str] = None, config: Optional[DistrictConfig] = None) -> Dict[str, Any]:
    """
    행정구역 CSV 파일을 처리하여 시군구명 기준으로 중복 제거 후 JSON으로 변환합니다.
    
    Args:
        csv_content: CSV 파일의 바이트 내용
        output_filename: 출력 파일명 (없으면 타임스탬프 기반으로 생성)
        config: District 설정 (None이면 기본 config 사용)
    
    Returns:
        처리 결과 딕셔너리 (성공여부, 메시지, 파일경로, 통계정보)
    """
    module_name = "district_service"
    function_name = "process_district_csv"
    
    # Config 로드
    if config is None:
        from src.core.config import load_config
        config = load_config().district
    
    log_info(
        LogCategory.CSV_PROCESSING, module_name, function_name, "함수_시작",
        f"CSV 처리 시작 - 데이터 크기: {len(csv_content):,} bytes, 출력파일: {output_filename or '자동생성'}"
    )
    
    try:
        # CSV 내용을 DataFrame으로 읽기 (다양한 인코딩과 구분자 시도)
        csv_string = None
        df = None
        
        # 인코딩 시도 순서
        encodings = ['utf-8-sig', 'utf-8', 'euc-kr', 'cp949']
        
        with log_step(LogCategory.CSV_PROCESSING, module_name, function_name, "인코딩_시도"):
            log_info(
                LogCategory.CSV_PROCESSING, module_name, function_name, "인코딩_시작",
                f"인코딩 시도 시작 - 시도할 인코딩: {encodings}"
            )
            
            for encoding in encodings:
                try:
                    csv_string = csv_content.decode(encoding)
                    log_info(
                        LogCategory.CSV_PROCESSING, module_name, function_name, "인코딩_성공",
                        f"인코딩 성공: {encoding}, 문자열 길이: {len(csv_string):,}"
                    )
                    break
                except UnicodeDecodeError as e:
                    log_warning(
                        LogCategory.CSV_PROCESSING, module_name, function_name, "인코딩_실패",
                        f"인코딩 실패: {encoding} - {str(e)}"
                    )
                    continue
        
        if not csv_string:
            log_error(
                LogCategory.CSV_PROCESSING, module_name, function_name, "인코딩_전체_실패",
                f"모든 인코딩 시도 실패 - 시도한 인코딩: {encodings}"
            )
            raise UnicodeDecodeError("모든 인코딩 시도 실패")
        
        # CSV 구분자와 형식 시도
        csv_options = [
            {'sep': ',', 'quotechar': '"'},  # 표준 CSV
            {'sep': '\t', 'quotechar': '"'},  # TSV (탭 구분)
            {'sep': '|', 'quotechar': '"'},   # 파이프 구분
            {'sep': ',', 'quotechar': "'"},   # 싱글 쿼트
            {'sep': ',', 'engine': 'python', 'on_bad_lines': 'skip'},  # 오류 줄 건너뛰기
        ]
        
        with log_step(LogCategory.CSV_PROCESSING, module_name, function_name, "CSV_파싱"):
            log_info(
                LogCategory.CSV_PROCESSING, module_name, function_name, "CSV_파싱_시작",
                f"CSV 파싱 시도 - 옵션 수: {len(csv_options)}"
            )
            
            # 데이터 미리보기로 형식 확인
            data_preview = csv_string[:1000]  # 처음 1000자 미리보기
            log_info(
                LogCategory.CSV_PROCESSING, module_name, function_name, "데이터_미리보기",
                f"데이터 미리보기: {data_preview[:200]}..."
            )
            
            parsing_success = False
            for i, options in enumerate(csv_options):
                try:
                    log_info(
                        LogCategory.CSV_PROCESSING, module_name, function_name, f"파싱_옵션_{i+1}",
                        f"파싱 옵션 시도: {options}"
                    )
                    
                    # 작은 샘플로 먼저 시도
                    sample_df = pd.read_csv(io.StringIO(data_preview), **options)
                    log_info(
                        LogCategory.CSV_PROCESSING, module_name, function_name, f"샘플_파싱_성공_{i+1}",
                        f"샘플 파싱 성공 - 컬럼 수: {len(sample_df.columns)}, 컬럼명: {list(sample_df.columns)}"
                    )
                    
                    if len(sample_df.columns) >= 3:  # 최소 3개 컬럼 필요
                        # 전체 데이터로 파싱 시도
                        df = pd.read_csv(io.StringIO(csv_string), **options)
                        log_info(
                            LogCategory.CSV_PROCESSING, module_name, function_name, f"전체_파싱_성공_{i+1}",
                            f"전체 파싱 성공 - 행 수: {len(df):,}, 컬럼 수: {len(df.columns)}, 컬럼명: {list(df.columns)}"
                        )
                        parsing_success = True
                        break
                    else:
                        log_warning(
                            LogCategory.CSV_PROCESSING, module_name, function_name, f"컬럼_부족_{i+1}",
                            f"컬럼 수 부족 - 필요: 3개, 실제: {len(sample_df.columns)}개"
                        )
                except Exception as e:
                    log_warning(
                        LogCategory.CSV_PROCESSING, module_name, function_name, f"파싱_실패_{i+1}",
                        f"파싱 옵션 {i+1} 실패: {str(e)}"
                    )
                    continue
            
            if df is None or len(df) == 0:
                log_warning(
                    LogCategory.CSV_PROCESSING, module_name, function_name, "수동_파싱_시도",
                    "표준 파싱 실패 - 수동 파싱 시도"
                )
                # 마지막 수단: 수동 파싱
                df = manual_csv_parse(csv_string)
                if df is not None and len(df) > 0:
                    log_info(
                        LogCategory.CSV_PROCESSING, module_name, function_name, "수동_파싱_성공",
                        f"수동 파싱 성공 - 행 수: {len(df):,}, 컬럼 수: {len(df.columns)}"
                    )
                    parsing_success = True
        
        if df is None or len(df) == 0:
            log_error(
                LogCategory.CSV_PROCESSING, module_name, function_name, "파싱_전체_실패",
                "모든 CSV 파싱 방법 실패"
            )
            raise ValueError("CSV 파싱에 실패했습니다. 파일 형식을 확인해주세요.")
        
        # 원본 데이터 통계
        original_count = len(df)
        log_info(
            LogCategory.CSV_PROCESSING, module_name, function_name, "원본_통계",
            f"원본 데이터 통계 - 행 수: {original_count:,}, 컬럼 수: {len(df.columns)}"
        )
        
        # 컬럼명 확인 및 정규화 (config에서 가져옴)
        expected_columns = config.expected_columns
        
        with log_step(LogCategory.CSV_PROCESSING, module_name, function_name, "컬럼명_매핑"):
            log_info(
                LogCategory.CSV_PROCESSING, module_name, function_name, "컬럼명_매핑_시작",
                f"실제 컬럼: {list(df.columns)}, 예상 컬럼: {expected_columns}"
            )
            
            # 실제 컬럼과 예상 컬럼 매핑
            column_mapping = {}
            for i, col in enumerate(df.columns):
                if i < len(expected_columns):
                    column_mapping[col] = expected_columns[i]
                    log_info(
                        LogCategory.CSV_PROCESSING, module_name, function_name, f"컬럼_매핑_{i+1}",
                        f"컬럼 매핑: '{col}' → '{expected_columns[i]}'"
                    )
            
            log_info(
                LogCategory.CSV_PROCESSING, module_name, function_name, "컬럼_매핑_완료",
                f"컬럼 매핑 완료 - 매핑된 컬럼 수: {len(column_mapping)}"
            )
            
            # 컬럼명 변경
            df = df.rename(columns=column_mapping)
            log_info(
                LogCategory.CSV_PROCESSING, module_name, function_name, "컬럼명_변경_완료",
                f"컬럼명 변경 완료 - 변경 후 컬럼: {list(df.columns)}"
            )
            
            # 시군구명 컬럼 존재 여부 확인
            if '시군구명' not in df.columns:
                log_error(
                    LogCategory.CSV_PROCESSING, module_name, function_name, "시군구명_컬럼_없음",
                    f"'시군구명' 컬럼이 존재하지 않음 - 현재 컬럼: {list(df.columns)}"
                )
                raise KeyError("'시군구명' 컬럼이 존재하지 않습니다. CSV 파일 형식을 확인해주세요.")
        
        with log_step(LogCategory.CSV_PROCESSING, module_name, function_name, "데이터_정리"):
            log_info(
                LogCategory.CSV_PROCESSING, module_name, function_name, "데이터_정리_시작",
                f"데이터 정리 시작 - 정리 전 행 수: {len(df):,}"
            )
            
            # 시군구명 컬럼의 현재 상태 확인
            null_count = df['시군구명'].isnull().sum()
            empty_count = (df['시군구명'].astype(str).str.strip() == '').sum()
            valid_count = len(df) - null_count - empty_count
            
            log_info(
                LogCategory.CSV_PROCESSING, module_name, function_name, "시군구명_상태_확인",
                f"시군구명 상태 - 전체: {len(df):,}, 유효: {valid_count:,}, NULL: {null_count:,}, 빈값: {empty_count:,}"
            )
            
            # 시군구명이 비어있거나 NaN인 행 제거
            before_cleanup = len(df)
            df = df.dropna(subset=['시군구명'])
            after_dropna = len(df)
            
            df = df[df['시군구명'].astype(str).str.strip() != '']
            after_cleanup = len(df)
            
            log_info(
                LogCategory.CSV_PROCESSING, module_name, function_name, "데이터_정리_완료",
                f"데이터 정리 완료 - 정리 전: {before_cleanup:,}, dropna 후: {after_dropna:,}, 최종: {after_cleanup:,}"
            )
        
        # 시군구명별 중복 개수 계산
        with log_step(LogCategory.CSV_PROCESSING, module_name, function_name, "중복_처리"):
            duplicate_counts = df['시군구명'].value_counts().to_dict()
            log_info(
                LogCategory.CSV_PROCESSING, module_name, function_name, "중복_계산_완료",
                f"시군구명별 중복 계산 - 고유 시군구: {len(duplicate_counts):,}개"
            )
            
            # 시군구명 기준으로 중복 제거 (첫 번째 행 유지)
            before_dedup = len(df)
            df_unique = df.drop_duplicates(subset=['시군구명'], keep='first')
            after_dedup = len(df_unique)
            
            log_info(
                LogCategory.CSV_PROCESSING, module_name, function_name, "중복_제거_완료",
                f"중복 제거 완료 - 제거 전: {before_dedup:,}, 제거 후: {after_dedup:,}, 제거된 수: {before_dedup - after_dedup:,}"
            )
            
            # 필요한 컬럼만 선택 (config에서 정의된 required_columns 사용)
            columns_to_keep = config.required_columns
            available_columns = [col for col in columns_to_keep if col in df_unique.columns]
            df_unique = df_unique[available_columns]
            
            log_info(
                LogCategory.CSV_PROCESSING, module_name, function_name, "컬럼_선택_완료",
                f"컬럼 선택 완료 - 선택된 컬럼: {available_columns}"
            )
            
            # 각 시군구명에 중복 개수 정보 추가
            df_unique['중복개수'] = df_unique['시군구명'].map(duplicate_counts)
        
        # 처리 후 데이터 통계
        after_cleanup_count = len(df)
        unique_count = len(df_unique)
        
        with log_step(LogCategory.CSV_PROCESSING, module_name, function_name, "JSON_저장"):
            log_info(
                LogCategory.CSV_PROCESSING, module_name, function_name, "JSON_변환_시작",
                f"JSON 변환 시작 - 최종 데이터 수: {unique_count:,}"
            )
            
            # JSON으로 변환할 데이터 준비
            json_data = {
                "metadata": {
                    "processed_date": datetime.now().isoformat(),
                    "original_count": original_count,
                    "after_cleanup_count": after_cleanup_count,
                    "unique_districts_count": unique_count,
                    "removed_duplicates": after_cleanup_count - unique_count
                },
                "districts": df_unique.to_dict('records')
            }
            
            # 출력 파일명 생성
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"districts_{timestamp}.json"
            
            log_info(
                LogCategory.CSV_PROCESSING, module_name, function_name, "파일명_생성",
                f"출력 파일명: {output_filename}"
            )
            
            # uploads 폴더 경로 설정 (config에서 가져옴)
            uploads_dir = config.uploads_dir
            os.makedirs(uploads_dir, exist_ok=True)
            
            output_path = os.path.join(uploads_dir, output_filename)
            
            # JSON 파일로 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            log_info(
                LogCategory.CSV_PROCESSING, module_name, function_name, "파일_저장_완료",
                f"파일 저장 완료 - 경로: {output_path}"
            )
        
        log_info(
            LogCategory.CSV_PROCESSING, module_name, function_name, "처리_최종_완료",
            f"CSV 처리 최종 완료 - 원본: {original_count:,} → 정리: {after_cleanup_count:,} → 최종: {unique_count:,}"
        )
        
        return {
            "success": True,
            "message": "CSV 파일이 성공적으로 처리되었습니다.",
            "file_path": output_path,
            "statistics": {
                "원본_데이터_수": original_count,
                "정리_후_데이터_수": after_cleanup_count,
                "중복제거_후_수": unique_count,
                "제거된_중복_수": after_cleanup_count - unique_count
            }
        }
        
    except UnicodeDecodeError as e:
        log_error(
            LogCategory.CSV_PROCESSING, module_name, function_name, "인코딩_오류",
            f"CSV 파일 인코딩 오류: {str(e)}", error=e
        )
        return {
            "success": False,
            "message": f"CSV 파일 인코딩 오류입니다: {str(e)}. 파일이 올바른 텍스트 형식인지 확인해주세요.",
            "file_path": None,
            "statistics": None
        }
    except pd.errors.EmptyDataError as e:
        log_error(
            LogCategory.CSV_PROCESSING, module_name, function_name, "빈_파일_오류",
            "CSV 파일이 비어있음", error=e
        )
        return {
            "success": False,
            "message": "CSV 파일이 비어있습니다.",
            "file_path": None,
            "statistics": None
        }
    except pd.errors.ParserError as e:
        log_error(
            LogCategory.CSV_PROCESSING, module_name, function_name, "파싱_오류",
            f"CSV 파싱 오류: {str(e)}", error=e
        )
        return {
            "success": False,
            "message": f"CSV 파싱 오류: {str(e)}. 파일 형식이나 구분자를 확인해주세요.",
            "file_path": None,
            "statistics": None
        }
    except ValueError as e:
        log_error(
            LogCategory.CSV_PROCESSING, module_name, function_name, "데이터_형식_오류",
            f"데이터 형식 오류: {str(e)}", error=e
        )
        return {
            "success": False,
            "message": f"데이터 형식 오류: {str(e)}",
            "file_path": None,
            "statistics": None
        }
    except KeyError as e:
        log_error(
            LogCategory.CSV_PROCESSING, module_name, function_name, "컬럼_오류",
            f"필수 컬럼 누락: {str(e)}", error=e,
            context_data={
                "available_columns": list(df.columns) if 'df' in locals() and df is not None else "없음",
                "expected_columns": expected_columns if 'expected_columns' in locals() else "없음"
            }
        )
        return {
            "success": False,
            "message": f"CSV 처리 중 오류가 발생했습니다: {str(e)}",
            "file_path": None,
            "statistics": None
        }
    except Exception as e:
        # 디버깅을 위한 상세 오류 정보
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "data_sample": csv_string[:200] if 'csv_string' in locals() else "데이터 없음",
            "data_size": len(csv_content) if csv_content else 0,
            "available_columns": list(df.columns) if 'df' in locals() and df is not None else "없음"
        }
        
        log_error(
            LogCategory.CSV_PROCESSING, module_name, function_name, "예상치_못한_오류",
            f"예상치 못한 오류: {str(e)}", error=e, context_data=error_details
        )
        
        return {
            "success": False,
            "message": f"CSV 처리 중 오류가 발생했습니다: {str(e)}",
            "file_path": None,
            "statistics": None,
            "debug_info": error_details
        }


def get_district_files(config: Optional[DistrictConfig] = None) -> List[Dict[str, Any]]:
    """
    uploads 폴더의 행정구역 JSON 파일 목록을 반환합니다.
    
    Args:
        config: District 설정 (None이면 기본 config 사용)
    
    Returns:
        파일 정보 리스트 (파일명, 경로, 크기, 생성일시)
    """
    # Config 로드
    if config is None:
        from src.core.config import load_config
        config = load_config().district
    
    uploads_dir = config.uploads_dir
    if not os.path.exists(uploads_dir):
        return []
    
    files = []
    for filename in os.listdir(uploads_dir):
        if filename.startswith(f"{config.file_prefix}_") and filename.endswith(f".{config.file_extension}"):
            file_path = os.path.join(uploads_dir, filename)
            try:
                stat = os.stat(file_path)
                files.append({
                    "filename": filename,
                    "file_path": file_path,
                    "size_mb": round(stat.st_size / 1024 / 1024, 2),
                    "created_time": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                })
            except OSError:
                continue
    
    # 생성일시 기준 내림차순 정렬
    files.sort(key=lambda x: x["created_time"], reverse=True)
    return files


def preview_district_file(file_path: str, limit: int = 10) -> Dict[str, Any]:
    """
    행정구역 JSON 파일의 내용을 미리보기합니다.
    
    Args:
        file_path: JSON 파일 경로
        limit: 미리보기할 레코드 수
    
    Returns:
        미리보기 결과 딕셔너리
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metadata = data.get("metadata", {})
        districts = data.get("districts", [])
        
        return {
            "success": True,
            "metadata": metadata,
            "preview_data": districts[:limit],
            "total_count": len(districts)
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"파일 읽기 오류: {str(e)}"
        }


def check_data_go_kr_update(url: str = "https://www.data.go.kr/data/15063424/fileData.do", config: Optional[DistrictConfig] = None) -> Dict[str, Any]:
    """
    data.go.kr 페이지에서 데이터 수정일을 확인합니다.
    
    Args:
        url: data.go.kr 페이지 URL
        config: District 설정 (None이면 기본 config 사용)
    
    Returns:
        수정일 정보와 확인 결과
    """
    try:
        # Config 로드
        if config is None:
            from src.core.config import load_config
            config = load_config().district
        
        headers = {
            'User-Agent': config.user_agent
        }
        
        response = requests.get(url, headers=headers, timeout=config.request_timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 수정일 정보 찾기 (여러 패턴 시도)
        modification_date = None
        
        # 패턴 1: 수정일 텍스트 찾기
        date_patterns = [
            r'수정일[:\s]*(\d{4}-\d{2}-\d{2})',
        ]
        
        page_text = soup.get_text()
        for pattern in date_patterns:
            match = re.search(pattern, page_text)
            if match:
                modification_date = match.group(1)
                break
        
        # 패턴 2: 특정 CSS 클래스나 태그에서 날짜 찾기
        if not modification_date:
            date_elements = soup.find_all(text=re.compile(r'\d{4}-\d{2}-\d{2}'))
            for element in date_elements:
                if any(keyword in str(element.parent) for keyword in ['수정일', '업데이트', 'update']):
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', element)
                    if date_match:
                        modification_date = date_match.group(1)
                        break
        
        if modification_date:
            return {
                "success": True,
                "modification_date": modification_date,
                "message": f"데이터 수정일: {modification_date}"
            }
        else:
            return {
                "success": False,
                "modification_date": None,
                "message": "페이지에서 수정일 정보를 찾을 수 없습니다."
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "modification_date": None,
            "message": f"페이지 접근 오류: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "modification_date": None,
            "message": f"수정일 확인 중 오류: {str(e)}"
        }


def download_district_data_from_web(config: Optional[DistrictConfig] = None) -> Dict[str, Any]:
    """
    data.go.kr에서 행정구역 데이터를 자동으로 다운로드합니다.
    test.py의 검증된 로직을 사용합니다.
    
    Args:
        config: District 설정 (None이면 기본 config 사용)
    
    Returns:
        다운로드 결과와 CSV 데이터
    """
    # Config 로드
    if config is None:
        from src.core.config import load_config
        config = load_config().district
    
    try:
        # test.py에서 검증된 META_URL 사용
        meta_url = config.meta_url
        
        session = requests.Session()
        headers = {
            "User-Agent": config.user_agent,
            "Referer": meta_url,
            "Accept": "application/json, text/plain, */*",
        }
        
        # 1) 메타 호출 → atchFileId 추출
        response = session.get(meta_url, headers=headers, timeout=config.request_timeout)
        response.raise_for_status()
        
        atch_file_id = None
        org_filename = None
        file_ext = None
        
        # JSON 시도
        try:
            data = response.json()
            # 보통 응답 최상단 or fileDataRegistVO에 atchFileId가 있음
            atch_file_id = (
                data.get("atchFileId")
                or data.get("fileDataRegistVO", {}).get("atchFileId")
                or data.get("dataSetFileDetailInfo", {}).get("atchFileId")
            )
            org_filename = (
                data.get("fileDataRegistVO", {}).get("orginlFileNm")
                or data.get("dataSetFileDetailInfo", {}).get("orginlFileNm")
            )
            file_ext = (
                data.get("fileDataRegistVO", {}).get("atchFileExtsn")
                or data.get("dataSetFileDetailInfo", {}).get("atchFileExtsn")
            )
        except json.JSONDecodeError:
            # 혹시 text/html로 JSON 문자열이 올 때를 대비해 정규식 백업
            import re
            m = re.search(r'"atchFileId"\s*:\\s*"([^"]+)"', response.text)
            if m:
                atch_file_id = m.group(1)
            m2 = re.search(r'"orginlFileNm"\\s*:\\s*"([^"]+)"', response.text)
            if m2:
                org_filename = m2.group(1)
            m3 = re.search(r'"atchFileExtsn"\\s*:\\s*"([^"]+)"', response.text)
            if m3:
                file_ext = m3.group(1)
        
        if not atch_file_id:
            return {
                "success": False,
                "message": "atchFileId를 찾지 못했습니다. 링크가 맞는지 또는 접근 권한/로그인 필요 여부를 확인하세요.",
                "csv_data": None
            }
        
        # 2) 실제 파일 다운로드
        dl_url = config.download_url
        params = {"atchFileId": atch_file_id, "fileDetailSn": "1"}
        response2 = session.get(dl_url, params=params, headers=headers, stream=True, timeout=config.download_timeout)
        response2.raise_for_status()
        
        # 원본 바이트를 읽음
        content_bytes = response2.content
        
        # 간단한 검증: HTML 오류페이지 방지
        content_preview = content_bytes[:1000].decode('utf-8', errors='ignore').lower()
        if '<html' in content_preview or '<!doctype html' in content_preview:
            return {
                "success": False,
                "message": "다운로드 결과가 파일이 아니라 HTML 페이지로 보입니다. 로그인/권한/세션을 확인하세요.",
                "csv_data": None
            }
        
        # CSV 데이터 검증
        validation_result = validate_csv_data(content_bytes)
        if not validation_result['is_valid']:
            return {
                "success": False,
                "message": f"다운로드된 데이터가 유효한 CSV가 아닙니다 (검증 점수: {validation_result.get('validation_score', 0)}/100)",
                "csv_data": None,
                "validation_info": validation_result
            }
        
        return {
            "success": True,
            "message": "data.go.kr에서 데이터 다운로드 성공",
            "csv_data": content_bytes,
            "validation_info": validation_result,
            "metadata": {
                "atch_file_id": atch_file_id,
                "org_filename": org_filename,
                "file_ext": file_ext,
                "size_bytes": len(content_bytes)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"자동 다운로드 중 오류: {str(e)}",
            "csv_data": None
        }


def extract_download_params(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    페이지에서 다운로드 파라미터를 추출하고 신뢰도를 평가합니다.
    """
    result = {
        'params': {},
        'confidence_score': 0,  # 0-100
        'extraction_method': None,
        'verification_info': {},
        'issues': []
    }
    
    # 1. JavaScript 함수 호출에서 파라미터 찾기
    script_tags = soup.find_all('script')
    js_patterns = [
        r'fn_fileDataDown\(["\']([^"\']+)["\'],\s*["\']([^"\']+)["\'],\s*["\']([^"\']*)["\'],\s*["\']([^"\']*)["\'],?\s*["\']([^"\']*)["\']?\)',
        r'fileDetailObj\.fn_fileDataDown\(["\']([^"\']+)["\'],\s*["\']([^"\']+)["\'],\s*["\']([^"\']*)["\'],\s*["\']([^"\']*)["\'],?\s*["\']([^"\']*)["\']?\)'
    ]
    
    for script in script_tags:
        if script.string and 'fn_fileDataDown' in script.string:
            for pattern in js_patterns:
                matches = re.findall(pattern, script.string)
                if matches:
                    # 가장 완전한 매치 찾기
                    best_match = max(matches, key=lambda m: len([p for p in m if p]))
                    
                    result['params'] = {
                        'publicDataPk': best_match[0] if len(best_match) > 0 else '',
                        'publicDataDetailPk': best_match[1] if len(best_match) > 1 else '', 
                        'atchFileId': best_match[2] if len(best_match) > 2 else '',
                        'fileDetailSn': best_match[3] if len(best_match) > 3 else '',
                        'downType': best_match[4] if len(best_match) > 4 else '1'
                    }
                    result['extraction_method'] = 'javascript_script'
                    result['confidence_score'] = 85
                    break
            
            if result['params']:
                break
    
    # 2. onclick 속성에서 파라미터 찾기
    if not result['params']:
        download_buttons = soup.find_all(['a', 'button'], onclick=re.compile(r'fn_fileDataDown'))
        for button in download_buttons:
            onclick = button.get('onclick', '')
            for pattern in js_patterns:
                match = re.search(pattern, onclick)
                if match:
                    result['params'] = {
                        'publicDataPk': match.group(1) if len(match.groups()) > 0 else '',
                        'publicDataDetailPk': match.group(2) if len(match.groups()) > 1 else '',
                        'atchFileId': match.group(3) if len(match.groups()) > 2 else '',
                        'fileDetailSn': match.group(4) if len(match.groups()) > 3 else '',
                        'downType': match.group(5) if len(match.groups()) > 4 else '1'
                    }
                    result['extraction_method'] = 'onclick_attribute'
                    result['confidence_score'] = 90
                    break
            
            if result['params']:
                break
    
    # 3. 대체 패턴들 시도
    if not result['params']:
        # data 속성에서 찾기
        data_elements = soup.find_all(attrs=lambda x: x and any('data-' in key for key in x.keys()))
        for element in data_elements:
            data_attrs = {k: v for k, v in element.attrs.items() if k.startswith('data-')}
            if len(data_attrs) >= 2:
                result['params'] = data_attrs
                result['extraction_method'] = 'data_attributes'
                result['confidence_score'] = 30
                break
        
        # 숨겨진 input 필드에서 찾기
        if not result['params']:
            hidden_inputs = soup.find_all('input', type='hidden')
            params_from_inputs = {}
            for inp in hidden_inputs:
                name = inp.get('name', '')
                value = inp.get('value', '')
                if name and value and any(keyword in name.lower() for keyword in ['pk', 'id', 'file', 'down']):
                    params_from_inputs[name] = value
            
            if params_from_inputs:
                result['params'] = params_from_inputs
                result['extraction_method'] = 'hidden_inputs'
                result['confidence_score'] = 40
    
    # 4. 파라미터 검증 및 신뢰도 조정
    if result['params']:
        # 필수 파라미터 존재 여부 확인
        required_params = ['publicDataPk']
        optional_params = ['publicDataDetailPk', 'atchFileId', 'fileDetailSn']
        
        missing_required = [p for p in required_params if not result['params'].get(p)]
        missing_optional = [p for p in optional_params if not result['params'].get(p)]
        
        if missing_required:
            result['issues'].append(f"필수 파라미터 누락: {missing_required}")
            result['confidence_score'] = max(0, result['confidence_score'] - 30)
        
        if missing_optional:
            result['issues'].append(f"선택적 파라미터 누락: {missing_optional}")
            result['confidence_score'] = max(0, result['confidence_score'] - 5 * len(missing_optional))
        
        # 파라미터 값 유효성 검사
        for key, value in result['params'].items():
            if key in required_params + optional_params:
                if not value or value.isspace():
                    result['issues'].append(f"빈 파라미터: {key}")
                elif not re.match(r'^[a-zA-Z0-9\-_:.]+$', value):
                    result['issues'].append(f"의심스러운 파라미터 형식: {key}={value}")
                    result['confidence_score'] = max(0, result['confidence_score'] - 10)
        
        # 검증 정보 수집
        result['verification_info'] = {
            'param_count': len(result['params']),
            'has_required_params': not bool(missing_required),
            'param_completeness': (len(required_params + optional_params) - len(missing_required) - len(missing_optional)) / len(required_params + optional_params) * 100
        }
    else:
        result['issues'].append("다운로드 파라미터를 찾을 수 없음")
        result['confidence_score'] = 0
    
    return result


def try_javascript_download(session: requests.Session, params: Dict[str, str]) -> Dict[str, Any]:
    """
    JavaScript 기반 다운로드를 시도합니다.
    실제 data.go.kr는 2단계 다운로드 방식을 사용합니다.
    """
    try:
        # 1단계: 다운로드 정보 요청 (publicDataPk, publicDataDetailPk만 사용)
        info_url = "https://www.data.go.kr/tcs/dss/selectFileDataDownload.do"
        
        info_data = {
            'publicDataPk': params.get('publicDataPk', ''),
            'publicDataDetailPk': params.get('publicDataDetailPk', '')
        }
        
        # 1단계 요청
        info_response = session.post(info_url, data=info_data, timeout=30)
        info_response.raise_for_status()
        
        # HTML 응답 조기 감지
        response_preview = info_response.content[:1000].decode('utf-8', errors='ignore').lower().strip()
        
        if (response_preview.startswith('<!doctype html') or 
            response_preview.startswith('<html') or
            '<html' in response_preview[:200]):
            return {
                "success": False,
                "message": "HTML 페이지 응답 - CSV 다운로드 링크가 아님. 웹사이트 구조가 변경되었거나 다운로드 파라미터가 잘못됨",
                "csv_data": None,
                "validation_info": {
                    "is_html": True,
                    "content_preview": response_preview[:200]
                },
                "debug_info": {
                    "url": info_url,
                    "params": info_data,
                    "content_type": info_response.headers.get('content-type', ''),
                    "response_size": len(info_response.content)
                }
            }
        
        # 1단계 응답 파싱 (JSON 형태여야 함)
        try:
            import json
            info_json = json.loads(info_response.text)
            
            if not info_json.get('status'):
                return {
                    "success": False,
                    "message": f"다운로드 정보 요청 실패: {info_json.get('message', '알 수 없는 오류')}",
                    "csv_data": None,
                    "debug_info": {
                        "response": info_response.text[:500]
                    }
                }
            
            # 실제 다운로드 파라미터 추출
            atch_file_id = info_json.get('atchFileId', '')
            file_detail_sn = info_json.get('fileDetailSn', '')
            
            if not atch_file_id or not file_detail_sn:
                return {
                    "success": False,
                    "message": "다운로드 파라미터 추출 실패 - atchFileId 또는 fileDetailSn이 없음",
                    "csv_data": None,
                    "debug_info": {
                        "info_response": info_json
                    }
                }
            
        except json.JSONDecodeError:
            # JSON이 아닌 경우 직접 다운로드 시도 (구 방식)
            return try_direct_file_download(session, info_response.content, info_url, info_data)
        
        # 2단계: 실제 파일 다운로드
        download_url = "https://www.data.go.kr/tcs/dss/selectFileDataDownload.do"
        
        download_data = {
            'atchFileId': atch_file_id,
            'fileDetailSn': file_detail_sn,
            'downType': 'file'
        }
        
        # 2단계 요청
        response = session.post(download_url, data=download_data, timeout=60)
        response.raise_for_status()
        
        # Content-Type 확인
        content_type = response.headers.get('content-type', '').lower()
        content_disposition = response.headers.get('content-disposition', '')
        
        # HTML 응답 재확인
        response_preview = response.content[:1000].decode('utf-8', errors='ignore').lower().strip()
        
        if (response_preview.startswith('<!doctype html') or 
            response_preview.startswith('<html') or
            '<html' in response_preview[:200]):
            return {
                "success": False,
                "message": "2단계에서도 HTML 응답 - 다운로드 프로세스 오류",
                "csv_data": None,
                "validation_info": {
                    "is_html": True,
                    "content_preview": response_preview[:200]
                },
                "debug_info": {
                    "url": download_url,
                    "params": download_data,
                    "content_type": content_type,
                    "response_size": len(response.content)
                }
            }
        
        # 실제 데이터가 CSV 형식인지 확인
        validation_result = validate_csv_data(response.content)
        is_valid_csv = validation_result['is_valid']
        
        # 파일 소스 검증 추가
        source_validation = validate_downloaded_file(
            response.content, 
            download_url, 
            download_data
        )
        
        if not is_valid_csv:
            # CSV가 아닌 경우 상세 정보 제공
            return {
                "success": False,
                "message": f"잘못된 데이터 형식 - CSV가 아님 (검증 점수: {validation_result.get('validation_score', 0)}/100)",
                "csv_data": None,
                "validation_info": validation_result,
                "debug_info": {
                    "url": download_url,
                    "params": download_data,
                    "content_type": content_type,
                    "response_size": len(response.content),
                    "content_preview": response_preview[:500]
                }
            }
        
        if (('csv' in content_type or 'text' in content_type or 
             'attachment' in content_disposition or 'filename' in content_disposition) 
             and is_valid_csv):
            return {
                "success": True,
                "message": "JavaScript 2단계 다운로드 성공",
                "csv_data": response.content,
                "validation_info": validation_result,
                "source_validation": source_validation
            }
        elif is_valid_csv:
            # Content-Type이 잘못되었지만 실제 데이터는 CSV인 경우
            return {
                "success": True,
                "message": "JavaScript 2단계 다운로드 성공 (Content-Type 불일치)",
                "csv_data": response.content,
                "validation_info": validation_result
            }
        
        return {
            "success": False,
            "message": f"잘못된 Content-Type: {content_type}",
            "csv_data": None,
            "validation_info": validation_result
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"JavaScript 다운로드 실패: {str(e)}",
            "csv_data": None
        }


def try_direct_file_download(session: requests.Session, content: bytes, url: str, params: Dict[str, str]) -> Dict[str, Any]:
    """
    1단계에서 JSON이 아닌 직접 파일이 반환된 경우 처리합니다.
    """
    # 실제 데이터가 CSV 형식인지 확인
    validation_result = validate_csv_data(content)
    is_valid_csv = validation_result['is_valid']
    
    if is_valid_csv:
        return {
            "success": True,
            "message": "1단계 직접 다운로드 성공",
            "csv_data": content,
            "validation_info": validation_result
        }
    else:
        return {
            "success": False,
            "message": f"1단계 응답이 유효한 CSV가 아님 (검증 점수: {validation_result.get('validation_score', 0)}/100)",
            "csv_data": None,
            "validation_info": validation_result,
            "debug_info": {
                "url": url,
                "params": params,
                "content_size": len(content),
                "content_preview": content[:500].decode('utf-8', errors='ignore')
            }
        }


def try_direct_links(session: requests.Session, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
    """
    직접 링크 방식 다운로드를 시도합니다.
    """
    # 다운로드 링크 찾기
    download_links = []
    
    # href 속성에서 찾기
    links = soup.find_all('a', href=True)
    for link in links:
        href = link['href']
        text = link.get_text().lower()
        if 'download' in text or '다운로드' in text:
            if not href.startswith('http'):
                href = 'https://www.data.go.kr' + href
            download_links.append(href)
    
    # 찾은 링크들로 다운로드 시도
    for link in download_links:
        try:
            response = session.get(link, timeout=60)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            if 'csv' in content_type or 'text' in content_type:
                return {
                    "success": True,
                    "message": "직접 링크 다운로드 성공",
                    "csv_data": response.content
                }
        except:
            continue
    
    return {
        "success": False,
        "message": "직접 링크 다운로드 실패",
        "csv_data": None
    }


def try_api_endpoints(session: requests.Session, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
    """
    알려진 API 엔드포인트를 시도합니다.
    """
    # 공통적으로 사용되는 API 엔드포인트들
    api_endpoints = [
        "/tcs/dss/selectFileDataDownload.do",
        "/api/fileData/download",
        "/fileDownload.do"
    ]
    
    for endpoint in api_endpoints:
        try:
            url = f"https://www.data.go.kr{endpoint}"
            
            # GET 방식 시도
            response = session.get(url, timeout=30)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                if 'csv' in content_type or 'text' in content_type:
                    return {
                        "success": True,
                        "message": f"API 엔드포인트 성공: {endpoint}",
                        "csv_data": response.content
                    }
        except:
            continue
    
    return {
        "success": False,
        "message": "API 엔드포인트 다운로드 실패",
        "csv_data": None
    }


def try_fallback_download(session: requests.Session, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
    """
    최후의 수단으로 알려진 파일 URL을 시도합니다.
    """
    # 행정안전부 법정동코드는 보통 고정된 패턴을 가짐
    fallback_urls = [
        "https://www.data.go.kr/tcs/dss/selectFileDataDownload.do?publicDataPk=15063424",
    ]
    
    for url in fallback_urls:
        try:
            response = session.get(url, timeout=60)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                if ('csv' in content_type or 'text' in content_type or 
                    len(response.content) > 1000):  # 최소 파일 크기 체크
                    return {
                        "success": True,
                        "message": f"폴백 다운로드 성공: {url}",
                        "csv_data": response.content
                    }
        except:
            continue
    
    return {
        "success": False,
        "message": "폴백 다운로드 실패",
        "csv_data": None
    }


def debug_download_process(url: str = "https://www.data.go.kr/data/15063424/fileData.do") -> Dict[str, Any]:
    """
    다운로드 과정을 디버깅하고 상세 정보를 반환합니다.
    개발/테스트 목적으로 사용됩니다.
    
    Args:
        url: data.go.kr 페이지 URL
    
    Returns:
        디버깅 정보가 포함된 결과
    """
    debug_info = {
        "steps": [],
        "errors": [],
        "found_elements": {},
        "final_result": None
    }
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
        
        session = requests.Session()
        session.headers.update(headers)
        
        # 1단계: 페이지 접근
        debug_info["steps"].append("1. 페이지 접근 시도")
        response = session.get(url, timeout=30)
        response.raise_for_status()
        debug_info["steps"].append(f"   - 응답 코드: {response.status_code}")
        debug_info["steps"].append(f"   - 페이지 크기: {len(response.text):,} bytes")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 2단계: 다운로드 버튼/링크 찾기
        debug_info["steps"].append("2. 다운로드 요소 검색")
        
        # 다운로드 관련 링크
        download_links = soup.find_all('a', href=True)
        relevant_links = []
        for link in download_links:
            href = link.get('href', '')
            text = link.get_text().strip()
            if any(keyword in text.lower() for keyword in ['다운로드', 'download', '내려받기']):
                relevant_links.append({
                    'href': href,
                    'text': text,
                    'onclick': link.get('onclick', '')
                })
        
        debug_info["found_elements"]["download_links"] = relevant_links
        debug_info["steps"].append(f"   - 다운로드 링크 수: {len(relevant_links)}")
        
        # JavaScript 함수 찾기
        script_tags = soup.find_all('script')
        js_functions = []
        for script in script_tags:
            if script.string and 'fn_fileDataDown' in script.string:
                js_functions.append(script.string[:200] + "..." if len(script.string) > 200 else script.string)
        
        debug_info["found_elements"]["javascript_functions"] = js_functions
        debug_info["steps"].append(f"   - JavaScript 함수 수: {len(js_functions)}")
        
        # 3단계: 파라미터 추출 시도
        debug_info["steps"].append("3. 다운로드 파라미터 추출")
        download_params = extract_download_params(soup)
        debug_info["found_elements"]["download_params"] = download_params
        debug_info["steps"].append(f"   - 추출된 파라미터: {len(download_params)} 개")
        
        # 4단계: 각 다운로드 방법 시도
        methods = [
            ("JavaScript 방식", lambda: try_javascript_download(session, download_params) if download_params else {"success": False, "message": "파라미터 없음"}),
            ("직접 링크 방식", lambda: try_direct_links(session, soup, url)),
            ("API 엔드포인트 방식", lambda: try_api_endpoints(session, soup, url)),
            ("폴백 방식", lambda: try_fallback_download(session, soup, url))
        ]
        
        for method_name, method_func in methods:
            debug_info["steps"].append(f"4. {method_name} 시도")
            try:
                result = method_func()
                debug_info["steps"].append(f"   - 결과: {'성공' if result['success'] else '실패'}")
                debug_info["steps"].append(f"   - 메시지: {result['message']}")
                
                if result["success"]:
                    debug_info["final_result"] = {
                        "method": method_name,
                        "success": True,
                        "data_size": len(result.get("csv_data", b"")),
                        "message": result["message"]
                    }
                    return {
                        "success": True,
                        "message": f"디버깅 완료 - {method_name} 성공",
                        "debug_info": debug_info,
                        "csv_data": result["csv_data"]
                    }
            except Exception as e:
                debug_info["errors"].append(f"{method_name} 오류: {str(e)}")
                debug_info["steps"].append(f"   - 오류: {str(e)}")
        
        debug_info["final_result"] = {
            "method": "없음",
            "success": False,
            "message": "모든 방법 실패"
        }
        
        return {
            "success": False,
            "message": "모든 다운로드 방법 실패 - 디버깅 정보 확인",
            "debug_info": debug_info,
            "csv_data": None
        }
        
    except Exception as e:
        debug_info["errors"].append(f"전체 과정 오류: {str(e)}")
        return {
            "success": False,
            "message": f"디버깅 중 오류: {str(e)}",
            "debug_info": debug_info,
            "csv_data": None
        }


def get_last_update_info(config: Optional[DistrictConfig] = None) -> Dict[str, Any]:
    """
    로컬에 저장된 마지막 업데이트 정보를 가져옵니다.
    
    Args:
        config: District 설정 (None이면 기본 config 사용)
    
    Returns:
        마지막 업데이트 정보
    """
    # Config 로드
    if config is None:
        from src.core.config import load_config
        config = load_config().district
    
    uploads_dir = config.uploads_dir
    info_file = os.path.join(uploads_dir, "last_update_info.json")
    
    if os.path.exists(info_file):
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"last_modification_date": None, "last_update_time": None}
    
    return {"last_modification_date": None, "last_update_time": None}


def save_update_info(modification_date: str, config: Optional[DistrictConfig] = None):
    """
    업데이트 정보를 로컬에 저장합니다.
    
    Args:
        modification_date: 데이터 수정일
        config: District 설정 (None이면 기본 config 사용)
    """
    # Config 로드
    if config is None:
        from src.core.config import load_config
        config = load_config().district
    
    uploads_dir = config.uploads_dir
    os.makedirs(uploads_dir, exist_ok=True)
    
    info_file = os.path.join(uploads_dir, "last_update_info.json")
    
    update_info = {
        "last_modification_date": modification_date,
        "last_update_time": datetime.now().isoformat()
    }
    
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(update_info, f, ensure_ascii=False, indent=2)


@log_function(LogCategory.WEB_SCRAPING, "자동_업데이트", include_args=False, include_result=False)
def auto_update_district_data(config: Optional[DistrictConfig] = None) -> Dict[str, Any]:
    """
    data.go.kr에서 데이터 업데이트를 자동으로 확인하고 필요시 다운로드/처리합니다.
    
    Args:
        config: District 설정 (None이면 기본 config 사용)
    
    Returns:
        자동 업데이트 결과
    """
    module_name = "district_service"
    function_name = "auto_update_district_data"
    
    # Config 로드
    if config is None:
        from src.core.config import load_config
        config = load_config().district
    
    log_info(
        LogCategory.WEB_SCRAPING, module_name, function_name, "자동_업데이트_시작",
        "data.go.kr 자동 업데이트 프로세스 시작"
    )
    
    # 1. 웹사이트에서 수정일 확인
    with log_step(LogCategory.WEB_SCRAPING, module_name, function_name, "웹사이트_확인"):
        log_info(
            LogCategory.WEB_SCRAPING, module_name, function_name, "수정일_확인_시작",
            "웹사이트에서 데이터 수정일 확인 시작"
        )
        
        check_result = check_data_go_kr_update(config=config)
        if not check_result["success"]:
            log_error(
                LogCategory.WEB_SCRAPING, module_name, function_name, "수정일_확인_실패",
                f"웹사이트 수정일 확인 실패: {check_result['message']}"
            )
            return {
                "success": False,
                "action": "check_failed",
                "message": check_result["message"]
            }
        
        web_modification_date = check_result["modification_date"]
        log_info(
            LogCategory.WEB_SCRAPING, module_name, function_name, "수정일_확인_완료",
            f"웹사이트 수정일 확인 완료: {web_modification_date}"
        )
    
    # 2. 로컬 업데이트 정보 확인
    with log_step(LogCategory.FILE_OPERATION, module_name, function_name, "로컬_정보_확인"):
        log_info(
            LogCategory.FILE_OPERATION, module_name, function_name, "로컬_정보_조회_시작",
            "로컬 업데이트 정보 조회 시작"
        )
        
        local_info = get_last_update_info(config)
        local_modification_date = local_info.get("last_modification_date")
        
        log_info(
            LogCategory.FILE_OPERATION, module_name, function_name, "로컬_정보_조회_완료",
            f"로컬 수정일: {local_modification_date or '없음'}"
        )
    
    # 3. 날짜 비교
    with log_step(LogCategory.VALIDATION, module_name, function_name, "날짜_비교"):
        log_info(
            LogCategory.VALIDATION, module_name, function_name, "날짜_비교_시작",
            f"날짜 비교 - 웹사이트: {web_modification_date}, 로컬: {local_modification_date}"
        )
        
        if local_modification_date == web_modification_date:
            log_info(
                LogCategory.VALIDATION, module_name, function_name, "업데이트_불필요",
                "데이터가 최신 상태 - 업데이트 불필요"
            )
            return {
                "success": True,
                "action": "no_update_needed",
                "message": f"데이터가 최신 상태입니다. (수정일: {web_modification_date})",
                "web_date": web_modification_date,
                "local_date": local_modification_date
            }
        
        log_info(
            LogCategory.VALIDATION, module_name, function_name, "업데이트_필요",
            "데이터 업데이트 필요 - 다운로드 진행"
        )
    
    # 4. 업데이트 필요 - 데이터 다운로드
    with log_step(LogCategory.WEB_SCRAPING, module_name, function_name, "데이터_다운로드"):
        log_info(
            LogCategory.WEB_SCRAPING, module_name, function_name, "다운로드_시작",
            "웹사이트에서 데이터 다운로드 시작"
        )
        
        download_result = download_district_data_from_web(config)
        if not download_result["success"]:
            # HTML 응답인지 확인하여 더 구체적인 에러 메시지 제공
            error_message = download_result["message"]
            
            # 디버그 정보가 있는 경우 추가 분석
            if "debug_info" in download_result:
                debug_info = download_result["debug_info"]
                if "page_size" in debug_info and debug_info.get("found_params") == False:
                    error_message += "\n\n🔍 가능한 해결방법:\n"
                    error_message += "1. 웹사이트 구조가 변경되어 다운로드 파라미터를 찾을 수 없습니다\n"
                    error_message += "2. 수동으로 CSV 파일을 다운로드하여 업로드해 주세요\n"
                    error_message += f"3. 페이지 주소: https://www.data.go.kr/data/15063424/fileData.do"
            
            # HTML 응답 관련 정보가 있는 경우
            validation_info = download_result.get("validation_info", {})
            if validation_info.get("is_html"):
                error_message += "\n\n⚠️ 웹사이트가 HTML 페이지를 반환했습니다. 다운로드 링크가 변경되었을 가능성이 높습니다."
            
            log_error(
                LogCategory.WEB_SCRAPING, module_name, function_name, "다운로드_실패",
                f"데이터 다운로드 실패: {error_message}"
            )
            return {
                "success": False,
                "action": "download_failed",
                "message": error_message,
                "web_date": web_modification_date,
                "local_date": local_modification_date,
                "debug_info": download_result.get("debug_info"),
                "validation_info": validation_info
            }
        
        data_size = len(download_result.get("csv_data", b""))
        log_info(
            LogCategory.WEB_SCRAPING, module_name, function_name, "다운로드_완료",
            f"데이터 다운로드 완료 - 크기: {data_size:,} bytes"
        )
    
    # 5. 다운로드된 데이터 검증 및 처리
    with log_step(LogCategory.CSV_PROCESSING, module_name, function_name, "자동_데이터_처리"):
        # config를 사용하여 파일명 생성
        if web_modification_date:
            date_str = web_modification_date.replace("-", "")
            filename = f"{config.file_prefix}_auto_{date_str}.{config.file_extension}"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{config.file_prefix}_auto_{timestamp}.{config.file_extension}"
        log_info(
            LogCategory.CSV_PROCESSING, module_name, function_name, "데이터_처리_시작",
            f"다운로드된 데이터 처리 시작 - 출력 파일: {filename}"
        )
        
        # 다운로드 검증 정보 로깅
        if "source_validation" in download_result:
            validation_info = download_result["source_validation"]
            log_info(
                LogCategory.VALIDATION, module_name, function_name, "소스_검증_결과",
                f"파일 소스 검증 - 유효: {validation_info['is_valid']}, 신뢰도: {validation_info['confidence_score']}, 이슈: {len(validation_info['issues'])}"
            )
            
            if not validation_info['is_valid']:
                log_warning(
                    LogCategory.VALIDATION, module_name, function_name, "소스_검증_경고",
                    f"파일 소스 검증 실패 - 이슈: {validation_info['issues']}"
                )
        
        # 웹사이트 변경 정보 로깅
        if "website_change_info" in download_result:
            change_info = download_result["website_change_info"]
            if change_info.get('changes_detected'):
                log_warning(
                    LogCategory.WEB_SCRAPING, module_name, function_name, "웹사이트_변경_감지",
                    f"웹사이트 변경사항 감지 - 심각도: {change_info['severity']}, 변경유형: {change_info['change_types']}"
                )
        
        process_result = process_district_csv(download_result["csv_data"], filename, config)
        
        if not process_result["success"]:
            log_error(
                LogCategory.CSV_PROCESSING, module_name, function_name, "데이터_처리_실패",
                f"데이터 처리 실패: {process_result['message']}"
            )
            return {
                "success": False,
                "action": "process_failed",
                "message": process_result["message"],
                "web_date": web_modification_date,
                "local_date": local_modification_date
            }
        
        log_info(
            LogCategory.CSV_PROCESSING, module_name, function_name, "데이터_처리_완료",
            f"데이터 처리 완료 - 저장 경로: {process_result['file_path']}"
        )
    
    # 6. 업데이트 정보 저장
    with log_step(LogCategory.FILE_OPERATION, module_name, function_name, "업데이트_정보_저장"):
        log_info(
            LogCategory.FILE_OPERATION, module_name, function_name, "정보_저장_시작",
            f"업데이트 정보 저장 - 수정일: {web_modification_date}"
        )
        
        save_update_info(web_modification_date, config)
        
        log_info(
            LogCategory.FILE_OPERATION, module_name, function_name, "정보_저장_완료",
            "업데이트 정보 저장 완료"
        )
    
    log_info(
        LogCategory.WEB_SCRAPING, module_name, function_name, "자동_업데이트_완료",
        f"자동 업데이트 프로세스 성공적으로 완료 - 웹: {web_modification_date}, 로컬: {local_modification_date}"
    )
    
    return {
        "success": True,
        "action": "updated",
        "message": f"데이터가 성공적으로 업데이트되었습니다. (수정일: {web_modification_date})",
        "web_date": web_modification_date,
        "local_date": local_modification_date,
        "file_path": process_result["file_path"],
        "statistics": process_result["statistics"]
    }


def delete_district_file(file_path: str, config: Optional[DistrictConfig] = None) -> Dict[str, Any]:
    """
    uploads 폴더에서 특정 행정구역 JSON 파일을 삭제합니다.

    Args:
        file_path: 삭제할 파일의 전체 경로
        config: District 설정 (None이면 기본 config 사용)

    Returns:
        삭제 결과 딕셔너리
    """
    # Config 로드
    if config is None:
        from src.core.config import load_config
        config = load_config().district
    
    # 보안 검증: uploads_dir 내부의 파일만 삭제 허용
    uploads_dir = os.path.abspath(config.uploads_dir)
    abs_file_path = os.path.abspath(file_path)
    
    if not abs_file_path.startswith(uploads_dir):
        return {
            "success": False,
            "message": "허용된 디렉토리 외부의 파일은 삭제할 수 없습니다."
        }

    try:
        if not os.path.exists(abs_file_path):
            return {
                "success": False,
                "message": f"파일이 존재하지 않습니다: {abs_file_path}"
            }

        os.remove(abs_file_path)
        log_info(
            LogCategory.FILE_OPERATION, "district_service", "delete_district_file", "파일_삭제_완료",
            f"파일 삭제 완료 - 경로: {abs_file_path}"
        )
        return {
            "success": True,
            "message": "파일이 성공적으로 삭제되었습니다.",
            "file_path": abs_file_path
        }
    except Exception as e:
        # 로그에 오류 기록
        try:
            log_error(
                LogCategory.FILE_OPERATION, "district_service", "delete_district_file", "파일_삭제_오류",
                f"파일 삭제 실패: {str(e)}", error=e, context_data={"file_path": file_path}
            )
        except Exception:
            # 로거에서 예외가 발생하면 안전하게 무시
            pass

        return {
            "success": False,
            "message": f"파일 삭제 중 오류가 발생했습니다: {str(e)}"
        }
