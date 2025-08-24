### Project Overview
This is a Streamlit web application that uses the OpenAI Vision API to analyze images. The application allows users to take a picture with their camera and get a description of the image from an AI model. It now focuses on identifying and classifying central objects in images using LLM, with future plans for pipeline expansion based on classification. It also includes an admin page to manage a Cloudflared tunnel, which can be used to expose the local Streamlit application to the internet.

### Building and Running
To run this project, you need to have Python and the required packages installed.

1.  **Install dependencies:**
    ```powershell
    pip install -r requirements.txt
    ```

2.  **Set up OpenAI API Key:**
    You need to provide an OpenAI API key. You can do this in one of the following ways:
    *   Set it as an environment variable named `OPENAI_API_KEY`.
    *   Create a `.env` file in the root of the project and add the following line:
        ```
        OPENAI_API_KEY="your-api-key"
        ```
    *   Enter the API key directly in the application's sidebar.

3.  **Run the application:**
    ```powershell
    streamlit run app.py
    ```

### Vision pipeline (rembg, ultralytics, mediapipe, PyTorch)
This project includes an optional vision measurement pipeline (hand-based size estimation) which uses rembg (U²-Net), MediaPipe Hands, and YOLOv8 (Ultralytics). These packages are optional and the app will gracefully degrade if they're not installed (a mocked/no-model flow is available for tests).

A pre-trained YOLOv8n-pose hand detection model (`yolov8n-hand-pose.pt`) is used for hand detection. This model is located in the `models/` directory.

Because some of these libraries depend on PyTorch and GPU builds, follow the platform-appropriate installation steps below. The examples use Windows PowerShell-compatible commands.

1.  **Install pure-Python dependencies (recommended first):**
    ```powershell
    pip install numpy rembg ultralytics mediapipe pillow
    ```

2.  **PyTorch (required by ultralytics and for GPU support)**
    - CPU-only (PowerShell example):
      ```powershell
      pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
      ```
    - GPU (CUDA) builds: choose the index URL matching your CUDA version (example for CUDA 11.8):
      ```powershell
      pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
      ```
    - Notes:
      * Check https://pytorch.org/get-started/locally/ for the correct index URL for your environment.
      * On Windows, ensure the correct CUDA toolkit / drivers are installed for GPU wheels to work.
      * If you don't install torch, ultralytics may still be importable but inference will fail; tests should mock model calls to avoid heavy downloads.

3.  **Remarks about rembg and mediapipe**
    * rembg may have native dependencies and can download models on first run. If you encounter issues, try installing with:
      ```powershell
      pip install rembg[u2net]
      ```
    * mediapipe provides prebuilt wheels for common platforms. If installation fails, consult the mediapipe docs for platform-specific instructions.

### Testing the Vision Pipeline (local, CPU-first)
- Unit tests are written to mock heavy model calls so CI doesn't need to download large models.
- Run tests with pytest:
  ```powershell
  pytest -q
  ```
- The new measurement UI is available in the Streamlit app under the "측정 도구" tab. If the models are not installed locally the UI will still run but detection features will be disabled and the app will show warnings or use defaults.

### Building and Running (recap)
1. Install dependencies (see Vision pipeline section for optional vision packages).
2. Provide `OPENAI_API_KEY`.
3. Run:
   ```powershell
   streamlit run app.py
   ```

### Project Structure Guidelines

이 프로젝트는 Streamlit 애플리케이션의 유지보수성과 확장성을 높이기 위해 다음과 같은 구조를 따릅니다.

```
C:\projects_vscode\env_ai\
├── app.py                 # 메인 애플리케이션 (홈 페이지)
├── pages/
│   └── admin.py           # Streamlit 페이지들 (파일 이름이 네비게이션에 표시됨)
├── src/
│   ├── __init__.py
│   ├── components/        # 여러 페이지에서 재사용되는 UI 컴포넌트
│   │   ├── __init__.py
│   │   └── tunnel_ui.py   # 터널 관리 UI 컴포넌트
│   ├── services/          # 외부 API 연동, 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── openai_service.py # OpenAI API 서비스
│   │   └── tunnel_service.py # 터널 관리 서비스 로직
│   └── core/
│       ├── __init__.py
│       ├── ui.py          # 공통 UI 유틸리티 (예: 설치 가이드)
│       └── utils.py       # 공통 유틸리티 및 상태 관리 (CONFIG, AppState, TunnelState)
├── tests/                 # 테스트 코드 (현재는 비어있음)
├── requirements.txt       # Python 종속성
└── .env                   # 환경 변수 (예: API 키)
```

**각 디렉터리의 역할:**

*   **`app.py`**: Streamlit 애플리케이션의 메인 진입점입니다. 홈 페이지 역할을 하며, 애플리케이션의 전반적인 레이아웃과 데모 페이지의 핵심 UI 및 로직을 포함합니다.
*   **`pages/`**: Streamlit의 멀티페이지 기능을 활용하여 사이드바에 자동으로 표시될 페이지들을 포함합니다. 각 `.py` 파일이 하나의 독립적인 페이지를 구성합니다.
*   **`src/`**: 프로젝트의 모든 재사용 가능한 파이썬 모듈을 포함하는 최상위 소스 디렉터리입니다.
    *   **`src/components/`**: 여러 페이지에서 사용될 수 있는 UI 컴포넌트들을 모아둡니다. (예: `tunnel_ui.py`는 터널 관리 UI를 제공)
    *   **`src/services/`**: 외부 서비스(API, 데이터베이스 등)와의 통신 및 순수한 비즈니스 로직을 담당하는 모듈들을 포함합니다. UI와 직접적인 상호작용 없이 데이터를 처리하거나 외부 시스템과 연동하는 역할을 합니다. (예: `openai_service.py`는 OpenAI API 호출, `tunnel_service.py`는 Cloudflared 터널 제어 로직)
    *   **`src/core/`**: 애플리케이션의 핵심 설정, 전역 상태 관리, 공통 유틸리티 함수 등 프로젝트 전반에 걸쳐 사용되는 기반 코드를 포함합니다. (예: `utils.py`는 `CONFIG`, `AppState`, `TunnelState` 정의, `ui.py`는 공통 UI 유틸리티)

**소스 추가 시 기준:**

1.  **UI 페이지**: Streamlit 사이드바에 독립적인 페이지로 표시되어야 하는 경우 `pages/` 디렉터리에 `.py` 파일을 생성합니다.
2.  **재사용 가능한 UI 컴포넌트**: 여러 페이지에서 사용될 Streamlit 위젯 조합이나 UI 로직은 `src/components/`에 추가합니다.
3.  **비즈니스 로직/외부 연동**: UI와 분리된 순수한 비즈니스 로직, 외부 API 호출, 데이터 처리 등은 `src/services/`에 추가합니다.
4.  **공통 유틸리티/설정/상태**: 애플리케이션 전반에 걸쳐 사용되는 설정, 상태 관리 클래스, 범용 유틸리티 함수 등은 `src/core/`에 추가합니다.

### 설정 관리 기준: 전역 vs. 페이지별

애플리케이션의 설정은 그 사용 범위에 따라 명확히 구분하여 관리해야 합니다.

*   **전역 설정 (Global Configuration)**:
    *   **정의**: 애플리케이션 전체에 걸쳐 일관되게 적용되는 설정값들입니다. 예를 들어, 기본 LLM 모델, 이미지 처리 품질, API 키 관련 환경 변수 이름 등이 여기에 해당합니다.
    *   **관리 위치**: `src/core/config.py` 파일의 `Config` 데이터 클래스 내에서 중앙 집중적으로 관리됩니다. `load_config()` 함수를 통해 로드되며, 필요한 모듈이나 함수에 인수로 명시적으로 전달하여 사용합니다.
    *   **예시**: `default_model`, `vision_models`, `default_prompt`, `max_image_size`, `jpeg_quality`, `default_port` 등.

*   **페이지별 설정 (Page-Specific Configuration)**:
    *   **정의**: 특정 Streamlit 페이지에만 고유하게 적용되는 설정값들입니다. 대표적으로 `st.set_page_config()` 함수의 `page_title`과 `page_icon`이 있습니다. 이 값들은 각 페이지의 브라우저 탭 제목과 파비콘을 결정하며, 페이지마다 달라야 합니다.
    *   **관리 위치**: 해당 페이지를 정의하는 `.py` 파일 내에서 직접 설정합니다. `st.set_page_config()` 함수를 사용하여 페이지 파일의 최상단에서 정의하는 것이 Streamlit의 관용적인 방식입니다.
    *   **예시**: `st.set_page_config(page_title="내 페이지 제목", page_icon="✨")`와 같이 각 페이지 파일 내에서 직접 설정합니다.

**구분하는 이유:**

이러한 구분을 통해 설정 관리의 복잡성을 줄이고 코드의 명확성을 높일 수 있습니다. 전역 설정은 애플리케이션의 핵심 동작을 제어하며, 페이지별 설정은 각 페이지의 고유한 시각적 특성을 정의합니다. 이 둘을 혼합하여 관리하면 불필요한 의존성이 생기거나 설정의 의미가 모호해질 수 있습니다.

이러한 구조를 통해 코드의 응집도를 높이고 결합도를 낮춰, 더 효율적인 개발과 유지보수를 가능하게 합니다.