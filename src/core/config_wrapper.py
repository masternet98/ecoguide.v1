"""
Core Config Wrapper for Legacy Compatibility

Phase 3에서 추가된 호환성 래퍼
기존 import 경로를 유지하면서 새 App 경로로 리다이렉트
"""

# 새 경로에서 모든 것을 re-export
try:
    from src.app.config import *
    print("[INFO] Config loaded from new app path")
except ImportError:
    # fallback to legacy path
    from src.core.config import *
    print("[WARNING] Config loaded from legacy path")