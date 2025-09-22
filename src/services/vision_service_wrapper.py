"""
Vision Service Wrapper for Legacy Compatibility

Phase 0.5에서 추가된 호환성 래퍼
기존 import 경로를 유지하면서 새 도메인 경로로 리다이렉트
"""

# 새 경로에서 모든 것을 re-export
try:
    from src.domains.analysis.services.vision_service import *
    print("[INFO] VisionService loaded from new domain path")
except ImportError:
    # fallback to legacy path (should not happen in Phase 0.5)
    from src.services.vision_service import *
    print("[WARNING] VisionService loaded from legacy path")