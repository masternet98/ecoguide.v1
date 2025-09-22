"""
Prompt Admin UI Wrapper for Legacy Compatibility

Phase 2에서 추가된 호환성 래퍼
기존 import 경로를 유지하면서 새 도메인 경로로 리다이렉트
"""

# 새 경로에서 모든 것을 re-export
try:
    from src.domains.prompts.ui.prompt_admin_ui import *
    print("[INFO] PromptAdminUI loaded from new domain path")
except ImportError:
    # fallback to legacy path
    from src.components.prompt_admin_ui import *
    print("[WARNING] PromptAdminUI loaded from legacy path")