"""
파일 소스 검증 및 홈페이지 변경 대응을 위한 모듈입니다.
다운로드 받은 파일이 올바른 소스에서 온 것인지 검증하고,
홈페이지 구조 변경 시 대응 방안을 제공합니다.
"""
import re
import hashlib
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
import requests

# 로깅 시스템 import
from src.core.logger import (
    logger, log_function, log_step, log_info, log_warning, log_error, 
    LogLevel, LogCategory
)


class FileSourceValidator:
    """파일 소스 검증을 위한 클래스"""
    
    def __init__(self):
        self.expected_patterns = {
            'data.go.kr': {
                'domain': 'data.go.kr',
                'content_patterns': ['법정동코드', '시도명', '시군구명'],
                'url_patterns': [r'/data/\d+/fileData\.do', r'/tcs/dss/selectFileDataDownload\.do'],
                'file_id_pattern': r'\d{8,}',  # 15123287과 같은 숫자 ID
                'expected_headers': ['법정동코드', '시도명', '시군구명', '읍면동명'],
                'min_data_size': 50000,  # 최소 50KB
                'max_data_size': 10000000  # 최대 10MB
            }
        }
        
        self.known_good_sources = []  # 검증된 좋은 소스들의 기록
        self.validation_history = []  # 검증 이력
    
    @log_function(LogCategory.VALIDATION, "파일_소스_검증", include_args=False)
    def validate_file_source(self, 
                           file_data: bytes, 
                           source_url: str, 
                           download_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        다운로드된 파일이 올바른 소스에서 온 것인지 검증합니다.
        
        Args:
            file_data: 다운로드된 파일 데이터
            source_url: 다운로드 소스 URL
            download_params: 다운로드에 사용된 파라미터
            
        Returns:
            검증 결과
        """
        module_name = "file_source_validator"
        function_name = "validate_file_source"
        
        log_info(
            LogCategory.VALIDATION, module_name, function_name, "검증_시작",
            f"파일 소스 검증 시작 - URL: {source_url}, 데이터 크기: {len(file_data):,}bytes"
        )
        
        result = {
            'is_valid': False,
            'confidence_score': 0,  # 0-100
            'issues': [],
            'warnings': [],
            'metadata': {},
            'recommendations': []
        }
        
        try:
            # 1. URL 검증
            url_validation = self._validate_url(source_url)
            result['metadata']['url_validation'] = url_validation
            
            if not url_validation['is_valid']:
                result['issues'].extend(url_validation['issues'])
                log_warning(
                    LogCategory.VALIDATION, module_name, function_name, "URL_검증_실패",
                    f"URL 검증 실패: {url_validation['issues']}"
                )
            else:
                result['confidence_score'] += 30
            
            # 2. 파일 내용 검증
            content_validation = self._validate_file_content(file_data)
            result['metadata']['content_validation'] = content_validation
            
            if content_validation['is_valid']:
                result['confidence_score'] += 40
                log_info(
                    LogCategory.VALIDATION, module_name, function_name, "내용_검증_성공",
                    f"파일 내용 검증 성공 - 점수: {content_validation['score']}"
                )
            else:
                result['issues'].extend(content_validation['issues'])
                log_warning(
                    LogCategory.VALIDATION, module_name, function_name, "내용_검증_실패",
                    f"파일 내용 검증 실패: {content_validation['issues']}"
                )
            
            # 3. 파라미터 검증
            if download_params:
                param_validation = self._validate_download_params(download_params)
                result['metadata']['param_validation'] = param_validation
                
                if param_validation['is_valid']:
                    result['confidence_score'] += 20
                else:
                    result['warnings'].extend(param_validation['issues'])
            
            # 4. 데이터 무결성 검증
            integrity_validation = self._validate_data_integrity(file_data)
            result['metadata']['integrity_validation'] = integrity_validation
            
            if integrity_validation['is_valid']:
                result['confidence_score'] += 10
            else:
                result['issues'].extend(integrity_validation['issues'])
            
            # 5. 최종 평가
            result['is_valid'] = result['confidence_score'] >= 70
            
            if result['is_valid']:
                result['recommendations'].append("파일이 검증되었습니다. 안전하게 사용할 수 있습니다.")
                log_info(
                    LogCategory.VALIDATION, module_name, function_name, "검증_성공",
                    f"파일 소스 검증 성공 - 최종 점수: {result['confidence_score']}"
                )
            else:
                result['recommendations'].append("파일 검증에 문제가 있습니다. 수동 검토를 권장합니다.")
                if result['confidence_score'] >= 50:
                    result['recommendations'].append("부분적으로 유효하므로 신중히 사용하세요.")
                
                log_warning(
                    LogCategory.VALIDATION, module_name, function_name, "검증_부분실패",
                    f"파일 소스 검증 부분 실패 - 최종 점수: {result['confidence_score']}"
                )
            
            # 검증 이력 기록
            self._record_validation_history(source_url, result)
            
            return result
            
        except Exception as e:
            log_error(
                LogCategory.VALIDATION, module_name, function_name, "검증_오류",
                f"파일 소스 검증 중 오류: {str(e)}", error=e
            )
            result['issues'].append(f"검증 중 오류 발생: {str(e)}")
            return result
    
    def _validate_url(self, url: str) -> Dict[str, Any]:
        """URL의 유효성을 검증합니다."""
        result = {
            'is_valid': False,
            'issues': [],
            'metadata': {}
        }
        
        try:
            parsed = urlparse(url)
            result['metadata']['domain'] = parsed.netloc
            result['metadata']['path'] = parsed.path
            result['metadata']['query'] = parsed.query
            
            # 도메인 검증
            if 'data.go.kr' in parsed.netloc:
                result['metadata']['source_type'] = 'data.go.kr'
                
                # 알려진 패턴과 비교
                patterns = self.expected_patterns['data.go.kr']['url_patterns']
                if any(re.search(pattern, url) for pattern in patterns):
                    result['is_valid'] = True
                else:
                    result['issues'].append(f"알려진 URL 패턴과 일치하지 않음: {url}")
            else:
                result['issues'].append(f"알 수 없는 도메인: {parsed.netloc}")
            
            return result
            
        except Exception as e:
            result['issues'].append(f"URL 파싱 오류: {str(e)}")
            return result
    
    def _validate_file_content(self, file_data: bytes) -> Dict[str, Any]:
        """파일 내용의 유효성을 검증합니다."""
        result = {
            'is_valid': False,
            'score': 0,
            'issues': [],
            'metadata': {}
        }
        
        try:
            # 기본 크기 검증
            size = len(file_data)
            result['metadata']['file_size'] = size
            
            expected_config = self.expected_patterns['data.go.kr']
            
            if size < expected_config['min_data_size']:
                result['issues'].append(f"파일이 너무 작음: {size:,}bytes (최소: {expected_config['min_data_size']:,}bytes)")
            elif size > expected_config['max_data_size']:
                result['issues'].append(f"파일이 너무 큼: {size:,}bytes (최대: {expected_config['max_data_size']:,}bytes)")
            else:
                result['score'] += 20
            
            # 텍스트 디코딩 시도
            text_content = None
            encodings = ['utf-8-sig', 'utf-8', 'euc-kr', 'cp949']
            
            for encoding in encodings:
                try:
                    text_content = file_data[:5000].decode(encoding)
                    result['metadata']['detected_encoding'] = encoding
                    break
                except UnicodeDecodeError:
                    continue
            
            if not text_content:
                result['issues'].append("텍스트 디코딩 실패 - 올바른 CSV 파일이 아닐 가능성")
                return result
            
            # 예상 콘텐츠 패턴 검증
            found_patterns = []
            for pattern in expected_config['content_patterns']:
                if pattern in text_content:
                    found_patterns.append(pattern)
                    result['score'] += 20
            
            result['metadata']['found_patterns'] = found_patterns
            result['metadata']['missing_patterns'] = [
                p for p in expected_config['content_patterns'] if p not in found_patterns
            ]
            
            if len(found_patterns) >= len(expected_config['content_patterns']) * 0.7:
                result['score'] += 20
            else:
                result['issues'].append(f"필수 패턴 부족: 발견됨 {len(found_patterns)}/{len(expected_config['content_patterns'])}")
            
            # CSV 구조 검증
            lines = text_content.split('\n')[:20]  # 처음 20줄만 검사
            if len(lines) >= 2:
                result['score'] += 10
                
                # 헤더 검증
                first_line = lines[0].strip()
                if first_line:
                    # 구분자 감지
                    delimiters = [',', '\t', '|', ';']
                    best_delimiter = ','
                    max_count = 0
                    
                    for delimiter in delimiters:
                        count = first_line.count(delimiter)
                        if count > max_count:
                            max_count = count
                            best_delimiter = delimiter
                    
                    if max_count >= 3:  # 최소 4개 컬럼
                        result['score'] += 10
                        headers = [h.strip().strip('"\'') for h in first_line.split(best_delimiter)]
                        result['metadata']['detected_headers'] = headers
                        
                        # 예상 헤더와 비교
                        expected_headers = expected_config['expected_headers']
                        matching_headers = [h for h in headers if h in expected_headers]
                        result['metadata']['matching_headers'] = matching_headers
                        
                        if len(matching_headers) >= len(expected_headers) * 0.75:
                            result['score'] += 20
                        else:
                            result['issues'].append(f"헤더 불일치: 일치하는 헤더 {len(matching_headers)}/{len(expected_headers)}")
            
            result['is_valid'] = result['score'] >= 60
            return result
            
        except Exception as e:
            result['issues'].append(f"내용 검증 오류: {str(e)}")
            return result
    
    def _validate_download_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """다운로드 파라미터의 유효성을 검증합니다."""
        result = {
            'is_valid': False,
            'issues': [],
            'metadata': params
        }
        
        try:
            required_params = ['publicDataPk']
            optional_params = ['publicDataDetailPk', 'atchFileId', 'fileDetailSn']
            
            # 필수 파라미터 확인
            missing_required = [p for p in required_params if not params.get(p)]
            if missing_required:
                result['issues'].append(f"필수 파라미터 누락: {missing_required}")
                return result
            
            # publicDataPk 검증 (15123287 같은 숫자 ID)
            public_data_pk = params.get('publicDataPk', '')
            if not re.match(r'^\d{7,9}$', public_data_pk):
                result['issues'].append(f"잘못된 publicDataPk 형식: {public_data_pk}")
            else:
                # 알려진 ID와 비교
                known_ids = ['15123287']  # 행정안전부 법정동코드
                if public_data_pk in known_ids:
                    result['is_valid'] = True
                else:
                    result['issues'].append(f"알려지지 않은 데이터 ID: {public_data_pk}")
            
            return result
            
        except Exception as e:
            result['issues'].append(f"파라미터 검증 오류: {str(e)}")
            return result
    
    def _validate_data_integrity(self, file_data: bytes) -> Dict[str, Any]:
        """데이터 무결성을 검증합니다."""
        result = {
            'is_valid': True,
            'issues': [],
            'metadata': {}
        }
        
        try:
            # 파일 해시 계산
            file_hash = hashlib.sha256(file_data).hexdigest()
            result['metadata']['file_hash'] = file_hash
            
            # 기본 바이너리 검증
            if b'\x00' in file_data[:1000]:
                result['issues'].append("바이너리 데이터 감지 - CSV 파일이 아닐 가능성")
                result['is_valid'] = False
            
            # 파일 시작과 끝 확인
            start_bytes = file_data[:100]
            end_bytes = file_data[-100:]
            
            # BOM 확인
            if file_data.startswith(b'\xef\xbb\xbf'):
                result['metadata']['has_bom'] = True
            elif file_data.startswith(b'\xff\xfe') or file_data.startswith(b'\xfe\xff'):
                result['issues'].append("UTF-16 인코딩 감지 - 예상치 못한 형식")
                result['is_valid'] = False
            
            return result
            
        except Exception as e:
            result['issues'].append(f"무결성 검증 오류: {str(e)}")
            result['is_valid'] = False
            return result
    
    def _record_validation_history(self, source_url: str, validation_result: Dict[str, Any]):
        """검증 이력을 기록합니다."""
        try:
            history_entry = {
                'timestamp': datetime.now().isoformat(),
                'source_url': source_url,
                'is_valid': validation_result['is_valid'],
                'confidence_score': validation_result['confidence_score'],
                'issues_count': len(validation_result['issues']),
                'warnings_count': len(validation_result['warnings'])
            }
            
            self.validation_history.append(history_entry)
            
            # 이력이 너무 길어지면 정리
            if len(self.validation_history) > 100:
                self.validation_history = self.validation_history[-50:]
                
        except Exception as e:
            # 이력 기록 실패는 중요하지 않으므로 로그만 남김
            logger.warning(f"검증 이력 기록 실패: {e}")


class WebsiteChangeDetector:
    """웹사이트 변경 감지를 위한 클래스"""
    
    def __init__(self):
        self.baseline_patterns = {}
        self.change_history = []
    
    @log_function(LogCategory.WEB_SCRAPING, "웹사이트_변경_감지")
    def detect_website_changes(self, url: str, current_html: str) -> Dict[str, Any]:
        """
        웹사이트의 변경사항을 감지합니다.
        
        Args:
            url: 검사할 URL
            current_html: 현재 HTML 내용
            
        Returns:
            변경 감지 결과
        """
        result = {
            'changes_detected': False,
            'change_types': [],
            'severity': 'low',  # low, medium, high, critical
            'recommendations': [],
            'fallback_options': []
        }
        
        try:
            soup = BeautifulSoup(current_html, 'html.parser')
            
            # 기준선이 없으면 현재 상태를 기준선으로 저장
            if url not in self.baseline_patterns:
                self.baseline_patterns[url] = self._extract_patterns(soup)
                result['recommendations'].append("기준선 패턴이 저장되었습니다.")
                return result
            
            baseline = self.baseline_patterns[url]
            current_patterns = self._extract_patterns(soup)
            
            # 변경사항 비교
            changes = self._compare_patterns(baseline, current_patterns)
            
            if changes:
                result['changes_detected'] = True
                result['change_types'] = list(changes.keys())
                result['severity'] = self._calculate_severity(changes)
                result['recommendations'] = self._generate_recommendations(changes)
                result['fallback_options'] = self._suggest_fallback_options(changes)
                
                # 변경 이력 기록
                self._record_change_history(url, changes, result['severity'])
            
            return result
            
        except Exception as e:
            result['recommendations'].append(f"변경 감지 중 오류: {str(e)}")
            return result
    
    def _extract_patterns(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """HTML에서 패턴을 추출합니다."""
        patterns = {
            'download_buttons': [],
            'javascript_functions': [],
            'form_elements': [],
            'url_patterns': [],
            'css_selectors': []
        }
        
        try:
            # 다운로드 버튼/링크 패턴
            download_elements = soup.find_all(['a', 'button'], 
                text=re.compile(r'다운로드|download|내려받기', re.I))
            for element in download_elements:
                patterns['download_buttons'].append({
                    'tag': element.name,
                    'class': element.get('class', []),
                    'id': element.get('id', ''),
                    'onclick': element.get('onclick', ''),
                    'href': element.get('href', '')
                })
            
            # JavaScript 함수 패턴
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'fn_fileDataDown' in script.string:
                    patterns['javascript_functions'].append({
                        'function_name': 'fn_fileDataDown',
                        'pattern_hash': hashlib.md5(script.string.encode()).hexdigest()[:16]
                    })
            
            # Form 요소 패턴
            forms = soup.find_all('form')
            for form in forms:
                patterns['form_elements'].append({
                    'action': form.get('action', ''),
                    'method': form.get('method', ''),
                    'id': form.get('id', ''),
                    'input_count': len(form.find_all('input'))
                })
            
            return patterns
            
        except Exception as e:
            return patterns
    
    def _compare_patterns(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, List[str]]:
        """패턴 변경사항을 비교합니다."""
        changes = {}
        
        # 다운로드 버튼 변경 확인
        baseline_buttons = len(baseline.get('download_buttons', []))
        current_buttons = len(current.get('download_buttons', []))
        
        if baseline_buttons != current_buttons:
            changes['download_buttons'] = [f"버튼 수 변경: {baseline_buttons} → {current_buttons}"]
        
        # JavaScript 함수 변경 확인
        baseline_js = set(f['pattern_hash'] for f in baseline.get('javascript_functions', []))
        current_js = set(f['pattern_hash'] for f in current.get('javascript_functions', []))
        
        if baseline_js != current_js:
            missing_js = baseline_js - current_js
            new_js = current_js - baseline_js
            
            js_changes = []
            if missing_js:
                js_changes.append(f"제거된 JS 함수: {len(missing_js)}개")
            if new_js:
                js_changes.append(f"추가된 JS 함수: {len(new_js)}개")
            
            if js_changes:
                changes['javascript_functions'] = js_changes
        
        # Form 요소 변경 확인
        baseline_forms = len(baseline.get('form_elements', []))
        current_forms = len(current.get('form_elements', []))
        
        if baseline_forms != current_forms:
            changes['form_elements'] = [f"폼 수 변경: {baseline_forms} → {current_forms}"]
        
        return changes
    
    def _calculate_severity(self, changes: Dict[str, List[str]]) -> str:
        """변경사항의 심각도를 계산합니다."""
        score = 0
        
        if 'javascript_functions' in changes:
            score += 40  # JS 함수 변경은 심각
        
        if 'download_buttons' in changes:
            score += 30  # 다운로드 버튼 변경도 중요
        
        if 'form_elements' in changes:
            score += 20
        
        if score >= 60:
            return 'critical'
        elif score >= 40:
            return 'high'
        elif score >= 20:
            return 'medium'
        else:
            return 'low'
    
    def _generate_recommendations(self, changes: Dict[str, List[str]]) -> List[str]:
        """변경사항에 대한 권장사항을 생성합니다."""
        recommendations = []
        
        if 'javascript_functions' in changes:
            recommendations.append("JavaScript 함수가 변경되어 다운로드 파라미터 추출 로직 업데이트가 필요합니다.")
            recommendations.append("디버그 모드를 사용하여 새로운 다운로드 패턴을 분석하세요.")
        
        if 'download_buttons' in changes:
            recommendations.append("다운로드 버튼이 변경되어 셀렉터 업데이트가 필요할 수 있습니다.")
        
        recommendations.append("수동 다운로드를 통해 데이터를 확보하고, 개발팀에 변경사항을 보고하세요.")
        
        return recommendations
    
    def _suggest_fallback_options(self, changes: Dict[str, List[str]]) -> List[str]:
        """대체 방안을 제안합니다."""
        options = [
            "수동 다운로드 후 CSV 업로드 기능 사용",
            "다른 데이터 소스 검색 (예: 행정안전부 직접 다운로드)",
            "이전에 저장된 데이터 파일 사용 (임시 방안)",
            "개발팀에 웹사이트 변경사항 대응 요청"
        ]
        
        if 'javascript_functions' in changes:
            options.insert(0, "디버그 모드로 새로운 다운로드 파라미터 패턴 분석")
        
        return options
    
    def _record_change_history(self, url: str, changes: Dict[str, List[str]], severity: str):
        """변경 이력을 기록합니다."""
        try:
            history_entry = {
                'timestamp': datetime.now().isoformat(),
                'url': url,
                'changes': changes,
                'severity': severity,
                'change_count': sum(len(change_list) for change_list in changes.values())
            }
            
            self.change_history.append(history_entry)
            
            # 이력 정리
            if len(self.change_history) > 50:
                self.change_history = self.change_history[-25:]
                
        except Exception as e:
            logger.warning(f"변경 이력 기록 실패: {e}")


# 전역 인스턴스 생성
file_validator = FileSourceValidator()
website_detector = WebsiteChangeDetector()


def validate_downloaded_file(file_data: bytes, 
                           source_url: str, 
                           download_params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    다운로드된 파일을 검증합니다.
    
    Args:
        file_data: 파일 데이터
        source_url: 소스 URL
        download_params: 다운로드 파라미터
        
    Returns:
        검증 결과
    """
    return file_validator.validate_file_source(file_data, source_url, download_params)


def detect_website_changes(url: str, html_content: str) -> Dict[str, Any]:
    """
    웹사이트 변경사항을 감지합니다.
    
    Args:
        url: 검사할 URL
        html_content: HTML 내용
        
    Returns:
        변경 감지 결과
    """
    return website_detector.detect_website_changes(url, html_content)