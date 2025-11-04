#!/bin/bash
source venv/bin/activate

# WSL2 IP 자동 감지 및 출력
WSL_IP=$(hostname -I | awk '{print $1}')
echo "========================================"
echo "Streamlit 서버 시작"
echo "========================================"
echo "Windows 브라우저에서 접속:"
echo "  http://${WSL_IP}:8501"
echo "========================================"

streamlit run app_new.py
