# 데이터 사전 (Data Dictionary) — 전 템플릿 공통

> 모든 `data/*/template.csv`·`labeling/*.csv`·`analysis/signals_template.csv`의 컬럼 정의.
> 원칙: **as-of 동결**(observed_at≠published_at), **출처 필수**, **원형 보존**. → 루트 `CLAUDE.md` §6.

## 공통 필드 (모든 data/* 레코드)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| `asset_class` | enum | `kr_stock` \| `crypto` \| `global_stock` |
| `symbol` | str | 표준코드(KR 6자리/ticker/거래소심볼). 미정 시 자유텍스트 + `id_unverified=true` |
| `name` | str | 종목/토큰명 |
| `observed_at` | ISO8601 | **내가 관측/수집한** 시각 |
| `published_at` | ISO8601 | **원천이 공개된** 시각 (as-of 동결의 핵심) |
| `source` | str | 출처 기관/플랫폼. 합성 예시는 `SYNTHETIC_EXAMPLE` |
| `url` | str | 근거 URL(원본). 없으면 레코드 무효 |
| `id_unverified` | bool | 심볼 미검증 시 `true` |

## price-volume 추가 필드
`interval`(1d/1h/…), `open`,`high`,`low`,`close`,`volume`, `turnover_rate`(회전율%), `market_cap`.
※ kr 상·하한(±30%)/VI, crypto 무정지, global 거래소·시간대 주의.

## disclosure-news 추가 필드
`doc_type`(disclosure/news/ir/rumor), `headline`, `body_or_summary`, `credibility`(official/press/rumor), `theme_tags`(`;`구분).
※ **published_at = 공시/기사 실제 공개시각**(사후 발견시각과 구분). 소급 해석 금지.

## sentiment 추가 필드
`platform`, `post_count`, `mention_count`, `sentiment_score`(−1~1), `keyword_freq`(`k:v;`), `sample_texts_anon`(익명화).
※ **개인식별정보 제거**. 상대값/표준화 권장(절대 게시글수는 종목 크기 종속).

## flow-actors 추가 필드
`actor_type`(inst/foreign/retail/broker/whale), `net_buy`, `broker_code`, `short_balance`, `onchain_flow`.
※ 공개 집계만. 특정 개인계좌/지갑 지목 금지(기관·클러스터 단위).

## labeling/positives.csv
| 컬럼 | 설명 |
|---|---|
| `event_id` | 사건 고유 ID (예: `KR-2023-0001`) |
| `label_version` | 라벨 버전 (현행 `v0.2`) |
| `t_start`,`t0` | 규칙기반 사전확정 사건축(급등 기점/종료) |
| `Wd` | 붕괴 관찰창(영업일) |
| `collapse_stratum` | `collapsed`\|`uncollapsed`\|`censored` (라벨 아님=층화축) |
| `gate_A_catalyst` | 게이트A 촉매 taxonomy 항목 (LOO 대상) |
| `gate_B_car_pct` | 게이트B 시장조정 누적초과수익(%) |
| `gate_D_verdict` | 펀더 무근거 블라인드 판정 (yes/no/gray) |
| `gate_D_kappa` | 판정자 간 Cohen's kappa |
| `gray_zone` | 경계/flip 과다 격리 여부 |
| `detection_time` | (REG-ENF) 당국이벤트 published_at — **t0로 미사용** |
| `evidence_url` | 근거 |

## labeling/positives_seed.csv (실데이터 — 확장 스키마)
`positives.csv` 컬럼에 **연구 필드 4개 추가**: `enforcement_status`(처벌 상태 서술), `pcr_ms_fit`(게이트 적합 + 사유), `manip_type`(**T1~T7** 조작 유형 → `labeling/manipulation_typology.md`), `anchor_grade`(**A1~A5, A0** 앵커 강도: A1 형사확정 > A2 plea > A3 기소 > A4 규제민사 > A5 시장경보 > A0 무혐의·무죄=대조). `gate_B_gain`은 상승폭 원문(정제 전).
⚠️ `anchor_grade=A0`(T6 등)은 양성 아님 — 대조(control-side) 표본. A3 이하는 pending, 판결 확정 시 갱신.

## labeling/controls.csv
`control_id`, `control_type`(C1 무조건부 / C2 hype-matched / C3 silent-positive), `matched_event_id`, `asset_class`, `symbol`, `name`, `placebo_t0`(C1 이식 t0), `match_market_cap`, `match_sector`, `match_period`, `notes`.

## analysis/signals_template.csv
`obs_id`, `event_id`, `asset_class`, `symbol`, `signal_name`(BCI/촉매케이던스/WCI/APS/PV1/…), `fold`(kr/crypto/global), `window`(예 `t_start-40~t_start-1`), `value`, `ref_percentile`, `asof_cutoff`(피처 계산 컷오프), `published_at_min`(관련 이벤트 최소 공개시각), `leakage_test_pass`(bool, 컷오프<published_at_min), `loo_applied`(bool, disclosure계열), `notes`.
※ **leakage_test_pass=false면 그 관측 폐기.** 라벨 축(게이트B) 공선 시그널은 해당 fold LR 제외.
