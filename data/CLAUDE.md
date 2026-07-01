# data/ — 원천 데이터 레이어 (Raw Data Layer)

> 루트 `CLAUDE.md`의 방법론·윤리를 상속한다. 여기서는 **데이터 공통 규칙**만 다룬다.
> 하위 4개 디렉토리(데이터 종류별)는 각자의 `CLAUDE.md`를 따른다.

## 이 레이어의 목적
작전이 "터지기 전" 흔적을 **원형 그대로(raw)** 보존한다. 해석은 `analysis/`에서 한다.
여기서는 **수집·정규화·시점 동결**까지만.

## 절대 규칙
- **as-of 동결**: 모든 레코드에 `observed_at` + `published_at`. 사건 후 소급 편집 금지.
- **자산군 태그**: `asset_class ∈ {kr_stock, crypto, global_stock}`.
- **출처 필수**: `source`, `url`. 원본 캡처(텍스트/스냅샷) 권장.
- **원형 보존**: 가공본은 별도. raw는 덮어쓰지 않는다.

## 공통 스키마(최소 필드)
```
asset_class, symbol, name, observed_at, published_at, source, url, payload(원형)
```

## 하위 디렉토리 (데이터 종류별 = 트리 루트 분기)
- `price-volume/` — 가격·거래량·호가·회전율
- `disclosure-news/` — 공시·뉴스·테마 이벤트
- `sentiment/` — 커뮤니티·SNS·여론 심리
- `flow-actors/` — 기관·외인·창구 등 수급 주체

## 수집 모드
혼합(수동+자동) → 검증 후 자동화. 자동화 스크립트는 각 하위 디렉토리에 둔다.

## 규격·템플릿
- **데이터 사전**: `schema.md` (전 컬럼 정의)
- **수집 체크리스트**: `COLLECTION_CHECKLIST.md` (as-of 동결·윤리·진입조건)
- **템플릿**: 각 하위 디렉토리 `template.csv` (헤더 + 합성 예시 1행, `SYNTHETIC_EXAMPLE`)
