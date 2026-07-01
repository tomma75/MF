# labeling/ — 양성 라벨 정의 + 대조군 매칭 (Labeling & Controls)

> 목적: "**무엇을 작전주(양성)로 볼 것인가**"를 정의하고, 각 양성에 **대조군**을 매칭한다.
> 이 디렉토리가 흔들리면 모든 분석이 무효가 된다.

## 라벨 정의 상태: v0.1 잠정 채택 (PROVISIONAL) — 개정 가능

**전체 정의·근거·임계값·개정규칙은 → `label_definitions.md`** (단일 정본). 여기선 요약만.

- 채택: **PCR-MS v0.2** (Promotion-Coupled Runup, Market-Adjusted, with Collapse-Stratification). 코어 불변.
- 도출: 오푸스 멀티에이전트. v0.2에서 3각도(price_quant/regulatory/cross_asset) 탐색 완료 → 모두 코어 fatal, 보조 재배치.
- **여전히 잠정이다.** 미해결 질문 8건은 **사전등록 기본값(잠정)** 부여됨(사용자 확정 시 `label_version`↑). 임계값·유니버스 경계 최종 확정 대기.
- 연계 산출물: 시그널 `analysis/features.md`, 사전등록 `validation/pre_registration.md`.
- 실데이터: `positives_seed.csv`(REG-ENF 앵커 실제 사례, 1차출처 검증 대기) + 근거 `../data/disclosure-news/case_archive.md`. `positives.csv`는 스키마 템플릿.

### 핵심 원칙 (반드시 준수)
1. **축 분리(construct separation)** — 라벨은 검증할 선행 시그널과 관찰축 공유 금지. `sentiment`/`flow-actors`/모멘텀은 라벨에서 빼고 **검증 대상 시그널로만** 둔다.
2. **붕괴는 라벨이 아니라 층화축** — `collapsed`/`uncollapsed`/`censored`. 우도비는 `{collapsed ∪ uncollapsed}` 대 대조군(종속변수 선택 편향 차단).
3. **사건 축은 알고리즘으로 사전확정** — t_start/t0 규칙 기반 + 누출 회귀테스트.
4. 정의 변경 시 **`label_version`을 올리고 `label_definitions.md` 결정 로그에 사유 기록.**

> ⚠️ 미탐색 각도(정량가격·제도적발·자산군일반화)나 미해결 질문을 다룰 땐 임의 확정 말고 **사용자에게 질문**한다.

## 대조군 매칭 (Case-Control) — 합의됨, 포함

각 양성 사례에 대해 **매칭된 음성(대조군)** 을 둔다. 매칭 기준(가설):
- 같은 **시기**(동일 윈도우), 비슷한 **시가총액**, 같은 **업종/섹터/체인**
- "안 터진" = 양성 정의의 사건이 발생하지 않은 종목
- 매칭 비율(1:1 / 1:k) 미정 → 표본 수 보고 결정

목적: `P(시그널)` 기저율과 **거짓양성**을 드러내, 시그널의 진짜 변별력(우도비)을 계산하기 위함.

## 산출 파일(권장)
```
labeling/
  label_definitions.md   # 채택된 정의 + 기각된 정의와 사유(결정 로그)
  positives.csv          # 양성 사례 (event_id, symbol, t0, 근거, 정의버전)
  controls.csv           # 대조군 (매칭된 positive_id, 매칭기준)
```
정의를 바꾸면 `label_version`을 올리고 결정 로그에 기록한다(재현성).
