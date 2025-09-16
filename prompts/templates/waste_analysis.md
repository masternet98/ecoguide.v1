# 대형폐기물 분석 프롬프트

## 설명
대형폐기물 배출을 위한 제품 크기 및 분류 분석 프롬프트입니다.

## 카테고리
Waste Classification

## 템플릿
```
이 이미지에 있는 제품을 대형폐기물로 배출하려고 합니다. 

대형폐기물 배출 시 제품의 크기가 가격에 중요한 영향을 미치므로, 다음 정보를 JSON 형식으로 분석해 주세요:

{
  "item_name": "제품명",
  "category": "폐기물 분류 (가전제품/가구/기타)",
  "estimated_dimensions": {
    "width": "가로 (cm)",
    "height": "세로 (cm)", 
    "depth": "깊이 (cm)"
  },
  "size_category": "크기 분류 (소형/중형/대형/특대형)",
  "material": "주요 재질",
  "disposal_notes": "배출 시 주의사항",
  "estimated_fee": "예상 수수료 구간"
}

분석 시 다음 사항을 고려해 주세요:
- 제품의 실제 크기를 최대한 정확히 추정
- 대형폐기물 수수료 기준에 따른 분류
- 분해 가능 여부 및 특별 처리 필요성
```

## 사용 기능
- gallery_upload
- waste_classification

## 태그
- 폐기물
- 크기분석
- 수수료
- 대형폐기물
- JSON응답