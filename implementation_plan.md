# Implementation Plan

[Overview]
업로드된 사진에서 배경 제거, 손 검출, 객체 검출을 결합해 손등(또는 손 폭)을 기준으로 물체의 실제 크기(가로/세로, cm)를 추정하고 대형폐기물 수수료를 안내하는 기능을 앱에 통합한다.

이 변경은 Streamlit 기반의 기존 카메라/업로드 이미지 분석 플로우(app.py)에 배경 제거 → 손 검출 → 객체 검출 → 크기 추정 → 요금 산정의 하위 파이프라인을 추가하는 것을 목표로 한다. 우선 YOLOv8(객체 검출), MediaPipe Hands(손 검출), rembg(배경 제거)을 사용하며, GPU가 없는 환경에서도 CPU 모드로 동작하도록 폴백을 제공한다. 사용성 관점에서 기본 가정은 촬영 거리가 약 1m 전후라는 점이며, UI에서 사용자가 자신의 손 폭(cm)과 촬영 거리(cm)를 입력하여 보정할 수 있게 한다. 결과는 기존 LLM 분석 흐름과 병행 가능하도록 UI에 통합한다.

[Types]  
손/물체 검출과 측정 결과를 표현하는 데이터 클래스(타입)를 추가한다.

타입 정의 (새 파일: `src/services/vision_types.py`):
- dataclass HandDetection:
  - hand_px: float  # 검출된 손 폭(픽셀)
  - bbox: Tuple[int,int,int,int] | None  # (x1,y1,x2,y2) 손 bounding box (픽셀)
  - landmarks: List[Tuple[float,float]] | None  # 정규화된(0..1) landmark 좌표 리스트
  - confidence: Optional[float]  # 검출 신뢰도 (0..1)
- dataclass ObjectDetection:
  - label: str  # 검출된 클래스 이름 (YOLO 라벨)
  - cls_id: int  # 클래스 id
  - bbox: Tuple[int,int,int,int]  # (x1,y1,x2,y2) 픽셀 좌표
  - width_px: int  # 가로 픽셀 수 (x2-x1)
  - height_px: int  # 세로 픽셀 수 (y2-y1)
  - confidence: float  # 신뢰도 (0..1)
- dataclass MeasurementResult:
  - object_detection: Optional[ObjectDetection]
  - hand_detection: Optional[HandDetection]
  - obj_width_cm: Optional[float]
  - obj_height_cm: Optional[float]
  - cm_per_px: Optional[float]
  - perspective_scale: Optional[float]
  - category: Optional[str]
  - fee: Optional[int]
  - notes: List[str]  # 오류/경고/권장사항(예: 손 미검출, 거리 미입력)
- dataclass VisionConfig:
  - yolo_model_path: str
  - rembg_enabled: bool
  - avg_hand_width_cm: Dict[str, float]  # ex: {"남성":8.4, "여성":7.3}
  - default_hand_distance_cm: int
  - default_obj_distance_cm: int
  - use_gpu: bool

유효성 규칙:
- hand_px, width_px, height_px는 1 이상의 값이어야 함.
- confidence는 0..1 범위여야 하며, 낮을 경우 MeasurementResult.notes에 경고를 추가.

[Files]
파일 추가 및 기존 파일 수정을 통해 기능을 통합한다.

신규 파일:
- src/services/vision_types.py — 위 데이터 클래스 정의.
- src/services/vision_service.py — 배경 제거(rembg), 손 검출(MediaPipe), 객체 검출(YOLOv8), 크기 추정, 카테고리 매핑 및 고수준 파이프라인을 구현.
- src/components/measure_ui.py — Streamlit UI 구성요소(업로드, 성별/손크기/거리 입력, 옵션, 결과 렌더링).
- test/data/sample_hand_object.jpg — (옵션) 테스트용 샘플 이미지.
- test/test_vision_pipeline.py — 단위/통합 테스트(모델 의존 부분은 mock 사용).

수정할 기존 파일:
- app.py
  - 변경: 기존 카메라/갤러리 탭에 '크기 추정' 탭 또는 기존 분석 흐름에 통합 버튼 추가. `src.components.measure_ui`에서 제공하는 UI 컴포넌트를 임포트하고 연결한다.
- src/core/config.py
  - 변경: Config 데이터 클래스에 vision 관련 기본값 추가 (rembg_enabled, yolo_model_path, avg_hand_width_cm, default distances, use_gpu 플래그 등).

삭제/이동:
- 없음(대체로 신규 파일 추가 및 최소한의 수정만 수행).

구성 파일 업데이트:
- requirements.txt에 새 패키지 및 권장 버전 추가:
  - rembg>=2.0.0
  - mediapipe>=0.10.0
  - ultralytics>=8.0.0
  - opencv-python>=4.7.0
  - numpy>=1.23
  - pillow>=9.0
  - (옵션) torch>=2.0, torchvision (GPU 사용 환경에서 설치 안내)
- README/GEMINI.md에 설치 및 모델다운로드(GPU/CPU 분기) 안내 추가.

[Functions]
서비스 계층에 이미지 처리·검출·측정 함수 및 통합 파이프라인을 추가하고 UI에서 호출한다.

신규 함수 (파일: `src/services/vision_service.py`):
- load_models(use_gpu: bool, yolo_model_path: str) -> None
  - 목적: ultralytics YOLO 모델 로드, MediaPipe 설정(필요 시), rembg 초기화 등. use_gpu에 따라 torch/cuda 사용 설정.
- remove_background_pil(pil_img: PIL.Image.Image) -> PIL.Image.Image
  - 목적: rembg를 사용해 배경 제거된 PIL 이미지 반환.
- detect_hand_mediapipe(image_cv: np.ndarray, max_num_hands: int = 1) -> Optional[HandDetection]
  - 목적: MediaPipe로 손 landmarks와 bbox를 추출하여 HandDetection 반환.
- detect_objects_yolo(image_cv: np.ndarray, conf_threshold: float = 0.3) -> List[ObjectDetection]
  - 목적: YOLOv8로 객체 검출(여러 객체 허용), confidence 필터링 후 ObjectDetection 리스트 반환.
- estimate_size_from_hand(hand: HandDetection, obj: ObjectDetection, hand_real_cm: float, dist_hand_cm: float, dist_obj_cm: float) -> Tuple[float,float,float]
  - 목적: cm_per_px 계산, 원근 보정(perspective_scale) 적용, 객체 크기(cm) 및 cm_per_px 반환.
- map_label_to_category(label: str) -> str
  - 목적: YOLO 라벨을 대형폐기물 카테고리(예: 정수기, 소형가전, 가구 등)로 매핑.
- calculate_fee(category: str, fee_table: Dict[str,int]) -> int
  - 목적: 수수료표에서 요금 반환.
- analyze_image_pipeline(pil_img: PIL.Image.Image, config: VisionConfig, user_hand_cm: Optional[float], user_hand_dist_cm: Optional[int], user_obj_dist_cm: Optional[int]) -> MeasurementResult
  - 목적: end-to-end 파이프라인 실행(배경 제거 옵션 → 손 검출 → 객체 검출 → 측정 → 카테고리/요금 산출) 및 MeasurementResult 반환.

수정 대상 함수:
- app.py: main() 내부 흐름을 확장하여 `src.components.measure_ui.render_measure_ui(...)`를 호출하거나 새로운 탭에서 파이프라인을 실행하도록 변경.

삭제되는 함수:
- 없음(기존 OpenAI 분석 흐름 및 함수는 병행 유지).

[Classes]
서비스 계층에 상태와 모델 인스턴스 재사용을 위한 VisionService 클래스를 추가할 수 있으며, 함수형 API도 병행 제공한다.

신규 클래스:
- class VisionService (src/services/vision_service.py)
  - __init__(self, config: VisionConfig)
  - load_models(self) -> None
  - analyze(self, pil_img: PIL.Image.Image, user_hand_cm: Optional[float]=None, user_hand_dist_cm: Optional[int]=None, user_obj_dist_cm: Optional[int]=None) -> MeasurementResult
  - 설명: YOLO 모델 인스턴스, MediaPipe 세션 등을 멤버로 보관하여 반복 호출 시 재사용. 단일 책임 원칙에 따라 모델 초기화와 분석 로직을 분리.

수정될 클래스:
- Config (src/core/config.py)
  - 필드 추가: rembg_enabled: bool, yolo_model_path: str, avg_hand_width_cm: Dict[str,float], default_hand_distance_cm: int, default_obj_distance_cm: int, use_gpu: bool

삭제된 클래스:
- 없음.

[Dependencies]
새 기능을 위해 rembg, mediapipe, ultralytics(YOLOv8), OpenCV 등을 `requirements.txt`에 추가하고 GPU 사용은 선택적으로 안내한다.

새 패키지 및 권장 버전:
- rembg>=2.0.0
- mediapipe>=0.10.0
- ultralytics>=8.0.0
- opencv-python>=4.7.0
- numpy>=1.23
- pillow>=9.0
옵션(GPU 환경):
- torch>=2.0 (CUDA 호환 버전, 사용 시 ultralytics가 GPU를 사용)
- torchvision

설치 안내(요약):
- CPU 환경: pip install rembg mediapipe ultralytics opencv-python numpy pillow
- GPU 환경: CUDA 설치 후, torch(적절한 CUDA 버전) + ultralytics 설치 권장(README에 예시 명령 추가)
- 모델 파일(yolov8n.pt 등)은 ultralytics가 런타임에 자동 다운로드 가능하나 네트워크가 제한된 환경에서는 사전 다운로드 및 로컬 배치 안내 필요.

[Testing]
단위 테스트 및 통합 테스트로 파이프라인 로직을 검증하되, 모델 의존 부분은 목(mock)으로 대체하여 CI에서 빠른 검증을 수행한다.

테스트 항목(파일: `test/test_vision_pipeline.py`):
- remove_background_pil: 배경 제거 후 이미지 모드/크기 확인(간단 검사).
- detect_hand_mediapipe: MediaPipe가 없을 때 mock으로 landmarks 반환되는지 확인.
- detect_objects_yolo: YOLO 모델이 없는 환경에서 mock으로 박스 반환 후 pipeline의 downstream 동작 확인.
- estimate_size_from_hand: 수치적 검증(입력 픽셀 값과 알려진 손 크기로부터 계산되는 cm 값이 기대값 범위에 있는지).
- analyze_image_pipeline: 전체 플로우의 MeasurementResult 필드가 올바르게 채워지는지(모든 의존성은 mock 주입).
- 통합 테스트(옵션): `test/data/sample_hand_object.jpg`로 end-to-end 수동 검증(로컬에서 권장).

CI 고려사항:
- 모델 다운로드/무거운 연산을 CI에서 직접 실행하지 않도록 하며, 테스트에서는 모델 호출을 mock으로 대체.
- 테스트 실행 스크립트(`pytest`) 및 requirements-dev(테스트용) 파일을 구성.

[Implementation Order]
모델 로더 및 타입 정의 → 서비스 구현(핵심 알고리즘) → UI 통합 → 테스트 및 문서화 순으로 단계별로 진행한다.

순서화된 단계:
1. `src/services/vision_types.py` 생성 — 모든 데이터 클래스 정의.
2. `src/core/config.py` 수정 — VisionConfig 및 기본값(예: rembg_enabled, yolo_model_path, avg_hand_width_cm, default distances, use_gpu) 추가.
3. `src/services/vision_service.py` 작성 (스텁부터 시작)
   3.1. `load_models()` 스텁 구현(모델 로더 및 use_gpu 처리)  
   3.2. `remove_background_pil()` 및 `detect_hand_mediapipe()` 구현(단위 테스트 가능)  
   3.3. `detect_objects_yolo()` 구현(ultralytics 결과 파싱 포함)  
   3.4. `estimate_size_from_hand()` 구현(공식 및 원근 보정 적용, 엣지케이스 처리)  
   3.5. `analyze_image_pipeline()` 통합 구현(전체 플로우)  
4. `src/components/measure_ui.py` 구현  
   - 업로드, 성별/손크기 수동 입력, 거리 입력, 배경 제거 토글, 결과 표시(이미지와 수치), 원시 정보(expander) 제공.  
5. `app.py` 통합  
   - 측정 탭 추가 또는 기존 분석 탭에 연동, 측정 결과를 LLM 분석과 병렬로 표시할 수 있게 구성.  
6. `requirements.txt` 및 `README/GEMINI.md` 업데이트(설치/환경 안내).  
7. 테스트 추가(`test/test_vision_pipeline.py`) 및 CI 설정(모델 호출은 목).  
8. 로컬 수동 검증(샘플 이미지 사용, CPU 환경에서 우선 검증).  
9. 선택적 개선: 전용 YOLO 재학습, 단안(depth) 추정 통합, 성능 최적화(GPU 활용) 등.

(끝 문서)

참고: 위 문서는 implementation_plan.md로 저장될 준비가 되어 있습니다. Act 모드로 전환되었으므로 제가 바로 파일로 기록하고 새 작업(new_task)을 생성하겠습니다.
