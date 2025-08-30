# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
- **Start the Streamlit app**: `streamlit run app.py`
- **Alternative start method**: `run.bat` (Windows batch file)

### Testing
- **Run all tests**: `pytest` (tests located in `test/` directory)
- **Run specific test file**: `pytest test/test_vision_pipeline.py`
- **Run tests with verbose output**: `pytest -v`

### Package Installation
- **Install core dependencies**: `pip install -r requirements.txt`
- **Install vision dependencies** (optional, CPU-only): `pip install rembg mediapipe ultralytics opencv-python`
- **Install PyTorch for GPU support**: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu`

## Architecture Overview

This is a **Streamlit-based computer vision application** that combines OpenAI's Vision API with local computer vision models for object detection and size estimation. The app analyzes uploaded images to identify objects and estimate their physical dimensions using hand-based scale reference.

### Core Components

**Main Application Structure**:
- `app.py` - Main Streamlit application entry point with camera/gallery UI
- `pages/admin.py` - Admin interface for Cloudflared tunnel management
- `src/` - Modular source code organized by responsibility

**Service Layer** (`src/services/`):
- `openai_service.py` - OpenAI Vision API integration for image analysis
- `vision_service.py` - Local computer vision pipeline (YOLO, MediaPipe, rembg)
- `vision_types.py` - Data classes for vision pipeline results
- `tunnel_service.py` - Cloudflared tunnel management logic

**Core Layer** (`src/core/`):
- `config.py` - Centralized application configuration using dataclasses
- `utils.py` - Common utilities and state management functions
- `ui.py` - Shared UI components and installation guides

**Components Layer** (`src/components/`):
- `measure_ui.py` - Measurement tool UI for size estimation
- `tunnel_ui.py` - Tunnel management interface components

### Vision Pipeline Architecture

The application implements a dual-analysis approach:
1. **OpenAI Vision Analysis**: Cloud-based object identification and description
2. **Local Vision Pipeline**: Computer vision-based size estimation using:
   - Background removal (`rembg`)
   - Hand detection (`MediaPipe Hands`)
   - Object detection (`YOLOv8`)
   - Size calculation based on hand-to-object scale ratio

### Configuration Management

**Global Configuration**: Managed in `src/core/config.py` using the `Config` dataclass
- Vision models, default prompts, image processing settings
- Loaded via `load_config()` and passed explicitly to functions

**Page-Specific Configuration**: Set directly in individual page files using `st.set_page_config()`

**Environment Variables**: 
- `OPENAI_API_KEY` - Required for OpenAI Vision API
- Configuration loaded from `.env` file or Streamlit secrets

### State Management

**Session State Pattern**: Extensive use of `st.session_state` for:
- API key persistence
- Image data (camera/gallery)
- Analysis results caching
- Tab switching state management

**App State**: Centralized state management via `get_app_state()` function in `src/core/utils.py`

### Model Management

**Local Models**:
- `models/yolov8n.pt` - General object detection
- `models/yolov8n-hand-pose.pt` - Hand pose detection
- Models auto-downloaded by ultralytics on first use

**GPU/CPU Flexibility**: 
- Configurable GPU usage via `VisionConfig.use_gpu`
- Graceful fallback to CPU-only operation
- Mock implementations for testing without heavy model dependencies

## Development Practices

### Code Organization Principles
- **Separation of Concerns**: UI (components), business logic (services), configuration (core)
- **Dependency Injection**: Configuration objects passed explicitly rather than global access
- **Modular Design**: Each service handles a single responsibility
- **Type Safety**: Extensive use of dataclasses and type hints

### Testing Strategy
- **Mock Heavy Dependencies**: Vision models mocked in tests to avoid model downloads
- **Unit Tests**: Test individual functions with controlled inputs
- **Integration Tests**: Test complete pipelines with mocked external dependencies
- **Test Data**: Sample images in `test/` directory for manual verification

### Error Handling
- **Graceful Degradation**: Vision features disabled if models unavailable
- **User-Friendly Messages**: Clear error messages for missing API keys or model failures
- **Fallback Modes**: Application continues to function even if optional features fail

## Important Implementation Details

### Image Processing Flow
1. **Input**: Camera capture or file upload via Streamlit
2. **Preprocessing**: JPEG conversion with configurable quality/size limits
3. **Analysis Options**:
   - OpenAI Vision API call for semantic analysis
   - Local vision pipeline for dimensional measurement
4. **Results**: JSON-structured output with confidence scores and measurements

### API Key Security
- API keys never stored in code or version control
- UI removed for direct API key input (security improvement in recent commits)
- Keys loaded from environment variables or Streamlit secrets only

### Multi-Tab State Management
- Complex tab switching logic with state persistence
- Image data preserved across tab changes
- Analysis results cleared when switching tabs to prevent confusion

### Vision Pipeline Specifics
- Hand-based scale estimation assumes ~1m shooting distance
- User-configurable hand width and distance parameters
- Perspective correction applied for distance-based scaling
- Category mapping from YOLO labels to waste management categories