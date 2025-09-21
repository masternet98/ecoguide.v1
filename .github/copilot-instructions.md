# EcoGuide AI Agent Instructions

This guide helps AI agents understand the EcoGuide codebase for effective contributions.

## Architecture Overview

EcoGuide is a Streamlit web application that uses computer vision to analyze images of waste. It combines OpenAI's Vision API for general analysis with a local computer vision pipeline for tasks like object detection and size estimation. The primary goal is to identify waste items and provide information for proper disposal.

The application follows a modular, service-oriented architecture where UI components are separated from business logic.

## Key Project Structure

- **`app_new.py`**: The main entry point for the Streamlit application (used by Docker). `app.py` is also an entry point.
- **`src/`**: Contains the core application logic.
  - **`core/`**: Application factory, configuration (`config.py`), logging, and session state management. `src/core/config.py` is the central hub for application settings.
  - **`services/`**: Business logic decoupled from the UI. This is where integrations with OpenAI (`openai_service.py`), local vision models (`vision_service.py`), and other external services reside.
  - **`components/`**: Reusable Streamlit UI components (e.g., `measure_ui.py`, `log_viewer.py`). These files should contain UI code only.
- **`pages/`**: Defines the different pages (routes) in the Streamlit multipage app.
- **`test/`**: Pytest unit and integration tests.
- **`models/`**: Pre-trained machine learning models (e.g., YOLO).

## Core Concepts & Data Flow

### Dual Analysis Pipeline

1.  **OpenAI Vision Analysis**: An image is sent to `OpenAIService` which calls the OpenAI Vision API for a high-level description and identification of objects.
2.  **Local Vision Pipeline**: `VisionService` orchestrates a local pipeline for more specific tasks:
    - Background removal (`rembg`)
    - Hand detection for scale (`MediaPipe`)
    - Object detection (`YOLOv8`)
    - Size estimation based on the detected hand as a reference.

### Configuration Management

- **Central Config**: The `Config` dataclass in `src/core/config.py` defines all major settings. An instance of this config is loaded via `load_config()` and passed explicitly to services and components. Do not access global config objects.
- **Secrets**: API keys (`OPENAI_API_KEY`, etc.) are managed via `.streamlit/secrets.toml` for deployment or a local `.env` file. Use `src/core/utils.resolve_api_key()` to access them. Never hardcode secrets.

### State Management

- The app relies heavily on Streamlit's Session State (`st.session_state`).
- A helper function, `get_app_state()` in `src/core/utils.py`, provides a structured way to access and initialize session state variables. Use this to ensure consistency.

## Developer Workflow

### Running the Application

- **Local Development**:
  - Set up the environment: `python -m venv venv && venv/Scripts/activate`
  - Install dependencies: `pip install -r requirements.txt`
  - Run the app: `streamlit run app_new.py` (or `run.bat` on Windows)

### Running Tests

- **Run all tests**: `pytest -q`
- **Run specific tests**: `pytest -k vision -q` (runs tests with "vision" in their name)
- **Testing Strategy**: Tests should be fast and deterministic. Use `monkeypatch` to mock network calls and heavy model loading. See `test/test_vision_pipeline.py` for examples.

## Coding Conventions

- **Separation of Concerns**: Keep service logic (`src/services`) free of Streamlit imports (`import streamlit as st`). UI code belongs in `src/components` and `pages/`.
- **Type Hinting**: Use Python 3.11+ type hints for all function signatures and variables.
- **Dependency Injection**: Pass configuration and services as arguments to functions and classes rather than using globals.
