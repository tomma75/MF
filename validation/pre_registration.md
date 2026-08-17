# 사전등록 (Pre-Registration) — 시그널 확증 검정

> 홀드아웃 개봉 **전에** 동결하는 확증 검정 계획. timestamp 고정, 사후 수정 금지.
> 대상: `analysis/features.md`의 1차 시그널 5개. 라벨: PCR-MS(→ `labeling/label_definitions.md`).
> 상태: **v0.2 사전등록 초안** — 임계값 범위·유니버스 경계는 사용자 확정 대기(§미해결 기본값).
> ⚠️ 교육·연구용. 최종 판정은 과거 적합이 아니라 **전향적 out-of-sample** 예측력으로 내린다.

## 결정규칙 (Decision Rules)

**[1] 주 시그널 확정** — confirmatory 대상은 primary 5개만: BCI(1), 촉매 케이던스 군집화(2), WCI(3, crypto fold), APS 잔차형(4), PV-1 잔차형(5). 나머지(secondary)는 exploratory로 분리, 성공/실패 판정 미포함.

**[2] 축 분리·순환 봉쇄 게이트** (위반 시 해당 fold 시그널 무효)
- (a) 라벨 축(게이트 B=price-volume 모멘텀) 기반 시그널은 그 fold LR에서 제외.
- (b) disclosure-sequence 시그널은 게이트 A 실채택 촉매 **LOO 제외 후** LR — 미시행 시 무효.
- (c) REG-ENF 보조축으로 flow-actors/모멘텀/price-volume LR 산출 금지(순환).
- (d) 저품질 촉매 ↔ 매집 시그널 사전상관 `|r|>0.5` → 해당 촉매 게이트 A에서 제외.

**[3] 사전 예측 방향·임계 동결** — 각 primary에 (i) 가설 방향(우측 tail), (ii) 이진화 임계는 '범위'로 등록하되 홀드아웃 밖 재튜닝 금지, (iii) LR **자산군별 개별(pooling 금지)**, (iv) C1(무조건부 기저율)·C2(hype-matched 상한) 분모 각각 보고, (v) 부트스트랩 신뢰구간 첨부.

**[4] 다중비교 보정** — primary 5 × 자산군(kr/crypto/global) × 창 파라미터의 확증 검정에 **Benjamini-Hochberg FDR q=0.10**. 감도분석(창폭·K·임계 범위)은 robustness로 분리(FDR 모수 제외). 멀티-시그널 결합은 exploratory만(과적합 경계).

**[5] 홀드아웃 분리** — 시간 분할 train/holdout(walk-forward). train에서만 정의·임계·LOO·클러스터링 확정. holdout **1회 개봉, 재튜닝 금지**. 역류 시 검증 무효.

**[6] 성공/실패 기준 (사전 동결)** — 개별 시그널 '성공' = (a) holdout에서 C1 대비 LR 95% CI 하한 > **1.5** AND (b) train→holdout LR 붕괴율 < **50%** AND (c) C2 대비 LR > **1**(표면신호 초과 변별) AND (d) FDR 통과. C2 LR≈1이면 개정규칙4 발동(코어 게이트 재검토). primary 3개 이상 동시 실패 시 시그널 세트 재설계. flip rate(K∈{5,7,10}) 과다·gray zone>15% 시 사건축(t_start/t0) 수정.

**[7] 검출편향 계량** — C3(silent positives = PCR-MS 양성인데 당국이벤트 없음) 구성 → under-detection rate 보고 + REG-ENF concordance(외적 타당도). 확증과 별도 진단.

**[8] as-of 누출 회귀테스트** — 모든 primary에 '시그널 컷오프 < min(관련 이벤트/t_start의 published_at)' unit-test 통과를 등록 조건으로 강제. crypto/벤치마크/float는 published_at 스냅샷 동결, 재구성 불가 구간은 censored.

## 검증 계획 (Holdout & Prospective)

**[A] 과거 홀드아웃 (retrospective out-of-sample)**
- walk-forward 시간분할. train에서만 정의·임계·LOO·클러스터링 확정, holdout 1회 개봉·재튜닝 금지.
- 개봉 채점: 5 primary의 C1/C2 대비 LR(95% CI), train→holdout LR 붕괴율, 거짓양성률(대조군 시그널 발생률), 리드타임 분포(시그널→t_start/t0 며칠 전). → §결정규칙[6]으로 판정.
- 성공/실패 모두 `holdout_report.md`에 기록, 실패 폐기 로그 유지.

**[B] 전향적 1개월 모니터링 (prospective — 진짜 out-of-sample)**
- 진입 트리거: 게이트 A(진행형 촉매)+게이트 B(진행중 급등, t_start 확정·t0 미확정)만으로 실시간 코호트 편입. 보조=REG-ENF T1/T2(조회공시·투자경고) 실시간. **선행 시그널은 진입 조건 아님 → 진입 후 채점**(축 분리·순환 방지).
- 사전 예측: 각 종목 5 primary 값·방향을 timestamp 동결로 `prospective_log.md`에 기록. 사후 채점만 허용.
- 채점 시점: 진입 후 약 1개월(kr 20/crypto 14/global 30영업일 + 붕괴 관찰 연장). t0·붕괴 사후 확정, uncollapsed는 장기창(t0+6개월/2·Wd) 미완이면 censored.
- 지표: 정밀도/재현율, LR 유지, 거짓양성률, 리드타임.

**[C] 데이터 무결성 강제**
- 실시간 스냅샷 필수(S2 계정메타, 호가잔량, sentiment 삭제분): 저장 불가 항목/자산군은 신호 무효(소급 수집=생존편향). crypto 온체인은 블록높이 동결로 자동 확보.
- 누출 회귀테스트: 모든 피처 published_at < 컷오프 unit-test 통과 강제.

**[D] 최종 판정** — 전향적 out-of-sample 예측력으로 채택 결정. 붕괴 시 개정규칙5(라벨이 '실패한/약한 조작' 편향인지 재평가). 통과 시그널만 `outputs/` 승격 → 이후 자동화.

## 산출 파일 (권장)
```
validation/
  pre_registration.md   # 본 문서 (동결)
  holdout_report.md      # train/holdout 성능
  prospective_log.md     # 전향적 사전 예측 + 실제 결과(날짜 동결)
```
