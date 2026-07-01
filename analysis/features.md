# 선행 시그널 카탈로그 (Feature / Signal Catalog)

> 라벨 PCR-MS(→ `labeling/label_definitions.md`) 위에서 **우도비(LR)/lift로 검증할 선행 시그널** 정의서.
> 도출: 오푸스 멀티에이전트(axis별 생성 → 적대검증 → 순위 → 종합). 상태: **사전등록 후보(v0.2)**.
> ⚠️ 아직 데이터로 검증되지 않은 **가설**이다. 검증은 `validation/pre_registration.md` 규칙을 따른다.

## 최상위 규칙 — 축 분리 & 순환 봉쇄 (위반 시 해당 fold 시그널 무효)

1. **라벨 축(게이트 B = price-volume 모멘텀) 기반 시그널은 그 fold LR에서 제외.**
2. **disclosure-sequence 시그널**은 게이트 A에 실제 채택된 촉매를 **leave-one-out(LOO)** 제외 후 LR 산출 — LOO 미시행 시 무효.
3. **REG-ENF 보조축으로는 flow-actors/모멘텀/price-volume LR 산출 금지**(동일 관찰축 순환).
4. 저품질 촉매 ↔ 매집 시그널(BCI 등) 사전상관 `|r|>0.5` → 해당 촉매 게이트 A에서 제외(개정규칙3).
5. **자산군별 개별 LR, pooling 금지.** crypto는 별도 fold.

---

## 1차 시그널 (Primary — confirmatory 검정 대상, 5개)

사전등록되어 홀드아웃 성공/실패 판정에 포함되는 시그널만.

### P1. BCI — Broker Concentration Index (창구 순매수 집중도) · `flow-actors` · rank 1
- **정의**: t_start 이전 폐쇄 pre-window `[t_start-D, t_start-1]`(D∈{20,40,60}영업일, kr)에서 거래원별 순매수 집중도. `share_i = net_buy_i / Σ|net_buy|`(양의 순매수 창구만), **BCI = Σ share_i²**(HHI) 또는 상위3창구 순매수 점유율. 동일 자산군·시총·섹터 매칭군 내 횡단면 백분위 상위 tail(90/95pct, 사전등록).
- **가설**: 양성은 소수 창구가 지속·일관 순매수 → BCI가 C1·C2 대비 우측 편향. 대조군은 다수 창구 분산.
- **데이터**: `data/flow-actors/`. crypto는 broker 부재 → 별도 fold에서 **P3(WCI)** 로 대체.
- **축 분리**: 라벨과 미공유(최우선 후보). 단 GATE-V(거래량)와 부분 공선 가능 → 필요 시 잔차화.

### P2. 촉매 케이던스 군집화 (Catalyst Clustering / Burstiness) · `disclosure-sequence` · rank 2
- **정의**: 관측창 `[t_start-L, t_start-1]`(L∈{60,90,120}영업일)에서 disclosure+news 도착간격(inter-arrival) 기반 **burstiness B=(σ_τ−μ_τ)/(σ_τ+μ_τ)**(Goh-Barabási) + 이벤트수 baseline(expanding median) 정규화 count-z. 둘 다 leave-one-out·rolling 참조분포 정규화, 상위 백분위 이진화.
- **가설**: 양성은 준비기에 촉매가 짧은 기간 몰림(리듬 압축) → B↑·count-z↑. 대조군은 산발·저빈도.
- **데이터**: `data/disclosure-news/`. **LOO 필수**(규칙 2).

### P3. WCI — Wallet Concentration & Exchange-Inflow (crypto 전용) · `flow-actors` · rank 3
- **정의**: crypto fold 전용. pre-window `[t_start-D, t_start-1]`(D∈{14,30,45}일)에서 (i) 상위 보유지갑 집중도 변화 Δ(top-N holder share), (ii) 소수 클러스터로의 CEX 순출금(조용한 축적). **WCI = z(Δtop_holder_share) ⊕ z(net_exchange_outflow to few clusters)**.
- **가설**: 양성 토큰은 t0 이전 소수지갑 집중↑ + 거래소→소수 클러스터 순유출 → WCI↑. 대조군은 홀더 분산 유지.
- **데이터**: `data/flow-actors/`(온체인). **공개 온체인·집계 클러스터만, 개인지갑 지목 금지**(윤리).

### P4. APS(잔차형) — Accumulation Persistence Score · `flow-actors` · rank 4
- **정의**: pre-window `[t_start-D, t_start-1]` 내 상위K 창구군 순매수의 **지속성 = (순매수 +일수 비율) × (상위창구 net_buy 자기상관 ρ1)**. 은닉성 impact항(`|Σnet_buy|/Σ|return|`)은 return=게이트B 축이라 **primary에서 제거**(잔차형이 주버전), impact 포함형은 secondary 진단으로만.
- **가설**: 양성은 장기 일관 방향성 순매수(높은 +일수·자기상관)로 축적 → APS↑. 대조군은 산발·양방향 혼재.
- **데이터**: `data/flow-actors/`.

### P5. PV-1(잔차형) — 횡보 중 거래량 다이버전스 (Quiet-Range Volume Divergence) · `price-volume-microstructure` · rank 5
- **정의**: 관측창 `[t_start-60, t_start-6]`영업일(kr; crypto `[-42,-4]`, global `[-45,-5]`), 전/후반 절반 분할. (i) 가격 횡보(실현변동성 자기이력 하위40pct & 시장조정 |CAR|≤1σ), (ii) 거래량 상승(후반 median 거래대금 ≥ 1.5× 전반 & Mann-Kendall 추세 p<0.05). **거래대금 기준(가격무관)**. `-6d` 버퍼로 t_start 급등 누출 차단.
- **가설**: 양성은 가격 정지 × 거래량 은밀 우상향(조용한 매집→유통물량 흡수). 대조군은 횡보 시 거래량도 정체.
- **데이터**: `data/price-volume/`. 게이트 B와 공선 방지 위해 **급등 이전 창 + 스파이크 배제**.

---

## 2차 시그널 (Secondary — exploratory, 확증 검정 미포함)

탐색적. 승격 조건 충족 시에만 primary 후보로 이동.

| 시그널 | axis | 판정 | 핵심 조건/한계 |
|---|---|---|---|
| **SII** 스마트머니 괴리 | flow-actors | revise | 소형주는 기관/외인≈0이라 '괴리'가 size-proxy로 인위 제조. BCI와 공선 → BCI에 직교화한 **incremental LR**만, 시총·float 잔차화 후에만. |
| **PV-4** 회전율 점진 상승 | price-volume | keep(중복) | PV-1과 다중공선. float **as-of 동결** 강제 + PV-1과 조건부 독립성 검정 후 **조건부 LR**로 중복 할인. |
| **S2** 신규계정 유입 비중 | sentiment | revise | 구성개념 최상(동원 직접 프록시)이나 계정연령 **point-in-time 스냅샷 필수**. 사후조회=생존편향 → 실시간 아키텍처 실증 전 실효 변별력 0. **전향적 fold 후보**. |
| **FIN→PROMO** 자금조달 선행→테마보도 후행 | disclosure-seq | revise | look-ahead 안전. **LOO 필수 게이트 승격**. 정상 자금조달+IR에서도 발생(높은 기저율) → C2에서 lift≈1 수렴 가능(단독 Med). |
| **희석형 자금조달 반복성** | disclosure-seq | revise | 순환위험 최고(게이트A 자금조달과 동일 raw). LOO 강제·미처리 시 무효. 섹터·시총 매칭 대조군 필수. |
| **S4-Gini** 작성자 집중도 | sentiment | revise(Gini만) | top-k 작성자 게시글 점유율 Gini는 동원 프록시(변별 잠재 High, 작성자 스냅샷 동결 시). 감성분산·반론비중 성분은 **폐기**(분류기 재현성 미달 + 삭제분 생존편향이 신호 인위 제조). |
| **S1** 조용→급증 관심 레짐전환 | sentiment | revise | 관측창이 가격파생 t_start 앵커라 가격 공변. 촉매일 마스킹·잔차 관심·`t_start-δ` 절단 필요. |
| **S3** 과열언어 밀도 | sentiment | revise | 밀도 '수준'은 급등과 동어반복 → 강등. **상승속도(dz/dt)+리드타임**만 유지. lexicon 동결·언어별 개별. |
| **PV-2** 종가 관리 지수 | price-volume | 보류 | 축 분리 최청정이나 동시호가·마감10분 데이터가 **현 스키마에 없음**(스키마 확장 전 측정 불가). |

---

## 검증 연결
- 이 카탈로그의 primary 5개는 `validation/pre_registration.md`에 사전등록되어 홀드아웃/전향적으로 검정된다.
- LR 표 산출 시: **C1 분모(무조건부 기저율)** 와 **C2 분모(hype-matched 상한 진단)** 를 각각 보고. 신뢰구간(부트스트랩) 첨부.
- 검증 통과 시그널만 `outputs/`로 승격.
