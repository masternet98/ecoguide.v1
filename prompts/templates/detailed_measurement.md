# 정밀 크기 측정 프롬프트

## 설명
객체의 정밀한 크기 측정을 위한 고급 분석 프롬프트입니다.

## 카테고리
Size Estimation

## 템플릿
```
이미지에서 {target_object}의 크기를 최대한 정확히 측정해 주세요.

측정 방법:
1. 이미지 내 기준 객체(손, 동전, 카드 등)를 찾아 스케일 추정
2. 원근법과 촬영 각도를 고려한 보정
3. 객체의 3차원 형태를 고려한 부피 계산

결과를 다음 JSON 형식으로 제공해 주세요:

{
  "object_name": "{target_object}",
  "reference_objects": ["감지된 기준 객체들"],
  "measurements": {
    "width_cm": "가로 길이 (cm)",
    "height_cm": "세로 길이 (cm)",
    "depth_cm": "깊이 (cm)",
    "volume_liters": "부피 (리터)",
    "confidence": "측정 신뢰도 (1-10)"
  },
  "measurement_method": "측정 방법 설명",
  "limitations": "측정의 한계점",
  "recommendations": "더 정확한 측정을 위한 제안"
}

분석 시 다음을 포함해 주세요:
- 측정 불확실성 요인
- 촬영 조건이 측정에 미치는 영향
- 개선 방안
```

## 변수
- target_object: 측정할 대상 객체

## 사용 기능
- size_estimation
- object_detection

## 태그
- 정밀측정
- 크기분석
- 부피계산
- 변수사용
- 고급분석