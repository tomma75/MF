# 공개 데이터 소스 카탈로그 & 수집 런북 (Sources & Runbook)

> 실제 발굴을 위한 **공개 데이터 출처** 목록과 수집 순서.
> ⚠️ **윤리(위반 금지)**: 공개 데이터만·공식 API 우선·**각 사이트 이용약관(ToS) 준수**·비공개/내부정보/약관위반 스크래핑 금지. 개인식별정보 익명화.
> 아래 URL·가용성·약관은 **수집 착수 시 반드시 재확인**(변경될 수 있음).

## 소스 표 (데이터 종류 × 자산군)

### price-volume (가격·거래량)
| 자산군 | 공개 소스(예) | 비고 |
|---|---|---|
| kr_stock | KRX 정보데이터시스템(공식 시세/통계), 증권사 공개 시세 API | 상·하한/VI, 유통주식수 as-of |
| crypto | 거래소 public REST(예: 업비트/바이낸스 캔들 endpoint), CoinGecko/CMC 집계 | 24h·상한없음, 캔들 간격 통일 |
| global_stock | 거래소 공식 EOD, 공개 시세 제공처 | 거래소·시간대 분리, OTC 제외 |

### disclosure-news (공시·뉴스) — **as-of 동결 최우선**
| 자산군 | 공개 소스(예) | 비고 |
|---|---|---|
| kr_stock | **DART 전자공시**, KRX **KIND**(조회공시·시황변동), 공식 IR/보도자료 | published_at=공시시각. 조회공시=REG-ENF T1 |
| crypto | 프로젝트 공식 채널·거래소 공지(리스팅/유의종목), 재단 공지 | 저품질 토크노믹스/파트너십 이벤트 |
| global_stock | **SEC EDGAR**(8-K 등), 공식 PR | reverse merger·going-concern PR |

### flow-actors (수급 주체) — **가장 깨끗한 시그널 축**
| 자산군 | 공개 소스(예) | 비고 |
|---|---|---|
| kr_stock | KRX 투자자별/**거래원별** 매매, 공매도 종합포털 | BCI/APS 핵심. 기관/외인/창구 |
| crypto | 공개 온체인 익스플로러·집계 클러스터 지표 | WCI. **개인지갑 지목 금지** |
| global_stock | 13F(기관), 공매도잔고(short interest) | 지연 공시 주의 |

### sentiment (여론 심리) — **약관·생존편향·익명화 주의**
| 자산군 | 공개 소스(예) | 비고 |
|---|---|---|
| kr_stock | 공개 종목토론방·공개 SNS(공식 API 우선) | ToS 확인 필수, PII 제거 |
| crypto | 공개 텔레그램/X(공식 API), 커뮤니티 | 사후 삭제분=생존편향 → 실시간 스냅샷 |
| global_stock | Reddit/StockTwits 등 공식 API | 실시간 point-in-time 저장 |

## 수집 런북 (실행 순서 — 파이프라인 정합)

1. **유니버스 확정** (`labeling` Q2 기본값) — 자산군별 시총 하한·배제규칙 적용, as-of 스냅샷.
2. **price-volume 전수 수집** → 자산군별 횡단면 분포 구축(게이트 B 백분위용, expanding·leave-one-out).
3. **t_start/t0 후보 탐지** — 규칙기반(PVAR 1차 스크리너로 대량 후보 선별). 당국이벤트는 detection_time로만.
4. **사건창 주변 정밀 수집** — 각 후보의 `[t_start-L, t0+Wd]` 창에서 disclosure-news·flow-actors(·sentiment) 수집. **published_at 동결**.
5. **라벨링** — 게이트 A(촉매 taxonomy)·B(초과수익)·D(블라인드 2인+kappa) → `positives.csv`. 붕괴 층화(collapse_stratum).
6. **대조군 생성** — C1(매칭+placebo-t0)·C2(PVAR hype-matched)·C3(silent positives) → `controls.csv`.
7. **시그널 계산** — 1차 5개(BCI/촉매케이던스/WCI/APS/PV-1) → `signals_template.csv`. **누출 회귀테스트·LOO** 통과분만.
8. **우도비(LR) 측정** — `analysis/likelihood_table.md`: C1·C2 분모 각각, 자산군별 개별(pooling 금지), 부트스트랩 CI.
9. **검증** — 홀드아웃 개봉 + 1개월 전향적(`validation/pre_registration.md` 결정규칙).

> 자동화는 **검증 이후**. 현재는 혼합(수동+자동), 소량 파일럿으로 스키마·런북을 먼저 검증하는 것을 권장.

## 파일럿 권장
전수 수집 전, **소수 사건(예: 자산군별 3~5건)** 으로 2→7단계를 한 바퀴 돌려 스키마·누출테스트·라벨러 kappa를 점검(과적합·자유도 조기 발견).
