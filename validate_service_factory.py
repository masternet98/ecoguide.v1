#!/usr/bin/env python3
"""
ServiceFactory 호환성 검증 스크립트

리팩토링 과정에서 ServiceFactory가 올바르게 동작하는지 검증합니다.
"""
import sys
import importlib
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """검증 결과"""
    service_name: str
    legacy_path: str
    new_path: Optional[str]
    legacy_success: bool
    new_success: bool
    error_message: Optional[str] = None


class ServiceFactoryValidator:
    """ServiceFactory 호환성 검증기"""

    def __init__(self):
        self.results: List[ValidationResult] = []

        # 현재 등록된 서비스들 (기존 경로)
        self.legacy_services = {
            'openai_service': 'src.services.openai_service',
            'vision_service': 'src.services.vision_service',
            'prompt_service': 'src.services.prompt_service',
            'district_service': 'src.services.district_service',
            'monitoring_service': 'src.services.monitoring_service',
            'notification_service': 'src.services.notification_service',
            'search_manager': 'src.services.search_manager',
            'tunnel_service': 'src.services.tunnel_service',
            'batch_service': 'src.services.batch_service',
        }

        # 새로운 도메인 매핑 (Phase 0.5 이후)
        self.new_domain_map = {
            'openai_service': 'analysis',
            'vision_service': 'analysis',
            'prompt_service': 'prompts',
            'district_service': 'district',
            'monitoring_service': 'monitoring',
            'notification_service': 'monitoring',
            'search_manager': 'infrastructure',
            'tunnel_service': 'infrastructure',
            'batch_service': 'infrastructure',
        }

    def validate_legacy_path(self, service_name: str, module_path: str) -> bool:
        """기존 경로에서 서비스 로딩 테스트"""
        try:
            module = importlib.import_module(module_path)
            return True
        except ImportError as e:
            print(f"[ERROR] Legacy path failed for {service_name}: {e}")
            return False
        except Exception as e:
            print(f"[WARNING] Legacy path error for {service_name}: {e}")
            return False

    def validate_new_path(self, service_name: str) -> tuple[bool, Optional[str]]:
        """새 경로에서 서비스 로딩 테스트"""
        if service_name not in self.new_domain_map:
            return False, f"Service {service_name} not in domain map"

        domain = self.new_domain_map[service_name]
        new_path = f"src.domains.{domain}.services.{service_name}"

        try:
            module = importlib.import_module(new_path)
            return True, None
        except ImportError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def validate_service_factory_loading(self) -> bool:
        """ServiceFactory 자체 로딩 검증"""
        try:
            from src.core.service_factory import ServiceFactory, ServiceRegistry
            print("[SUCCESS] ServiceFactory 모듈 로딩 성공")
            return True
        except ImportError as e:
            print(f"[ERROR] ServiceFactory 모듈 로딩 실패: {e}")
            return False
        except Exception as e:
            print(f"[WARNING] ServiceFactory 로딩 중 오류: {e}")
            return False

    def run_validation(self) -> bool:
        """전체 검증 실행"""
        print("[INFO] ServiceFactory 호환성 검증 시작")
        print("=" * 50)

        # 1. ServiceFactory 모듈 자체 로딩 테스트
        if not self.validate_service_factory_loading():
            return False

        print("\n[INFO] 서비스별 경로 검증:")
        print("-" * 30)

        all_success = True

        for service_name, legacy_path in self.legacy_services.items():
            print(f"\n- {service_name}:")

            # 기존 경로 검증
            legacy_success = self.validate_legacy_path(service_name, legacy_path)

            # 새 경로 검증 (아직 파일이 없으므로 실패 예상)
            new_success, error_msg = self.validate_new_path(service_name)

            # 결과 저장
            new_path = None
            if service_name in self.new_domain_map:
                domain = self.new_domain_map[service_name]
                new_path = f"src.domains.{domain}.services.{service_name}"

            result = ValidationResult(
                service_name=service_name,
                legacy_path=legacy_path,
                new_path=new_path,
                legacy_success=legacy_success,
                new_success=new_success,
                error_message=error_msg
            )
            self.results.append(result)

            # 출력
            legacy_status = "SUCCESS" if legacy_success else "FAILED"
            new_status = "FAILED" if not new_success else "SUCCESS"  # Phase 0에서는 새 경로 실패가 정상

            print(f"  기존 경로 ({legacy_path}): {legacy_status}")
            print(f"  새 경로 ({new_path}): {new_status} (Phase 0에서는 정상)")

            if not legacy_success:
                all_success = False

        return all_success

    def print_summary(self):
        """검증 결과 요약 출력"""
        print("\n" + "=" * 50)
        print("[SUMMARY] 검증 결과 요약")
        print("=" * 50)

        legacy_success_count = sum(1 for r in self.results if r.legacy_success)
        total_services = len(self.results)

        print(f"총 서비스 수: {total_services}")
        print(f"기존 경로 성공: {legacy_success_count}/{total_services}")
        print(f"새 경로 준비됨: 0/{total_services} (Phase 0 단계)")

        if legacy_success_count == total_services:
            print("\n[SUCCESS] Phase 0 검증 완료 - 기존 서비스 모두 정상 동작")
            print("[NEXT] 다음 단계: Phase 0.5에서 서비스 복사 진행")
        else:
            print("\n[ERROR] 기존 서비스에 문제가 있습니다. 리팩토링 전에 해결 필요")

        return legacy_success_count == total_services


def main():
    """메인 실행 함수"""
    validator = ServiceFactoryValidator()

    try:
        success = validator.run_validation()
        validator.print_summary()

        if success:
            print("\n[SUCCESS] ServiceFactory 호환성 검증 완료")
            return 0
        else:
            print("\n[FAILED] 검증 실패 - 문제 해결 후 재실행 필요")
            return 1

    except Exception as e:
        print(f"\n[ERROR] 검증 중 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())