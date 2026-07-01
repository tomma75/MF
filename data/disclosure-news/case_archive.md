# 사례 근거 아카이브 (Case Evidence Archive) — 실데이터 시드

> 공개 웹 검색으로 수집한 **실제 사례**의 근거. 모두 공개 기록(검찰 기소·법원 판결·규제/수사 발표).
> `observed_at`: 2026-07-01(수집시점). `published_at`: 각 원천 공개시점(개별 표기).
> ⚠️ **윤리**: 사실만 중립 기술(적발/기소/유죄 취지, 출처 귀속). **개인은 익명화**(주범→"주도자"). 기업/사건명은 광범위 공개기록이라 출처와 함께 기재하되, **교육 산출물 단계에서는 일반화/익명화**(CLAUDE.md §2). 투자자문 아님.
> ⚠️ 외부 콘텐츠(뉴스·위키) 기반 → 수치·날짜는 **1차 출처(법원/규제)로 교차검증 필요**. 미검증 항목은 `추정`으로 표기.

---

## CASE-1 · SG증권발 하한가 사태 (kr_stock) — REG-ENF 앵커
- **t0(터진 날)**: 2023-04-24 (SG증권 창구 대량매도 → 8개 종목 동시 하한가, 시총 약 8.2조원 증발).
- **대상 8종목**: 대성홀딩스, 선광, 삼천리, 서울가스, 세방, 다올투자증권, 하림지주, 다우데이타.
- **수법(공소사실 기준)**: 2019-05~2023-04 약 3년간 900명 이상 투자자 모집, 매수·매도가 사전 통정 + CFD(차액결제거래) 계좌 활용해 **은밀·완만 매집·부양** → 부당이득 약 7,305억원(적발 사상 최대).
- **사전 상승(04-21 기준)**: 하림지주 +113%, 다올투자증권 +85%, 세방 +44%, 다우데이타 +40%(지수 대비 초과).
- **처벌**: 주도자 자본시장법·범죄수익은닉규제법 위반 유죄 취지(1심 징역25년→2심 8년→대법 파기환송).
- **★ PCR-MS 정합성 노트 (연구적으로 중요)**: 이 사건은 **홍보/저품질 촉매(게이트 A) 없이** CFD 은밀 매집으로 이뤄진 **완만 다년 램프**. → PCR-MS 코어(게이트 A 필수)로는 **미검출 가능성** = REG-ENF 양성이지만 PCR-MS 음성일 수 있는 **C3(silent) 후보/불일치 사례**. 변별력의 진짜 축이 `flow-actors`(창구/CFD 집중)임을 시사(BCI/APS 가설 지지).
- **출처(published_at≈기사일)**:
  - 나무위키 "SG증권발 하한가 사태" https://namu.wiki/w/SG%EC%A6%9D%EA%B6%8C%EB%B0%9C%20%ED%95%98%ED%95%9C%EA%B0%80%20%EC%82%AC%ED%83%9C
  - 서울경제 "삼천리 등 중견 8개사 하한가 쇼크" https://www.sedaily.com/NewsView/29OFFH6L59
  - 대한경제 "[특징주] 다우데이타 등 8종목 하한가" (2023-04-24) https://www.dnews.co.kr/uhtml/view.jsp?idxno=202304241508091730184
  - 머니투데이 "쭉쭉 오르던 8개 종목 하한가 폭탄…7300억" https://www.mt.co.kr/society/2026/05/09/2026050810363097542
  - 파이낸셜뉴스(대법 파기환송) https://www.fnnews.com/news/202605201405026321

## CASE-2 · 무자본 M&A + CB/BW 시세조종 (kr_stock) — 법원 유죄, PCR-MS 정합 표본
- **수법(판결문 기준)**: 무자본 M&A로 상장사 인수 → **최대주주 변경·대규모 유상증자·전환사채(CB) 발행 등 호재성 공시** + 허위 보도자료 → 약 **1개월간 6,000원→14,000원(약 +133%)** 급등 → 페이퍼컴퍼니 계좌로 고가매수·물량소진·시종가관여·허수 주문(시세조종) → CB/BW 전환주식 매도 차익.
- **★ PCR-MS 정합성 노트**: 게이트 A(저품질 촉매=최대주주변경/유증/CB)·게이트 B(약 +133% 급등)·게이트 D(허위 보도자료=펀더 무근거) **모두 충족**하는 **교과서적 PCR-MS 양성**. CASE-1과 대비되는 '홍보결합형'.
- **출처**:
  - CaseNote 서울남부지법 2021고합135(외 병합) https://casenote.kr/%EC%84%9C%EC%9A%B8%EB%82%A8%EB%B6%80%EC%A7%80%EB%B0%A9%EB%B2%95%EC%9B%90/2021%EA%B3%A0%ED%95%A9135
  - CaseNote 서울남부지법 2020고합177(외 병합) https://casenote.kr/%EC%84%9C%EC%9A%B8%EB%82%A8%EB%B6%80%EC%A7%80%EB%B0%A9%EB%B2%95%EC%9B%90/2020%EA%B3%A0%ED%95%A9177
  - 국가법령정보센터 판례 https://www.law.go.kr/LSW/precInfoP.do?precSeq=220037&mode=0
  - 녹색경제신문 "[작전주 X파일] 무자본 M&A" https://www.greened.kr/news/articleView.html?idxno=319963

## CASE-3 · Saitama 등 토큰 pump-and-dump (crypto) — DOJ/FBI, REG-ENF 앵커
- **수법(DOJ 기준)**: 2021-07경 leadership이 **다수 지갑에 분산된 소액 매수(은밀 매집)** 시작 → market maker 고용 wash trading으로 거래량·가격 인위 부양(pump) → 고점 분산 매도(dump). Saitama는 한때 수십억 달러 시총.
- **연계 사건**: FBI "NexFundAI" 함정수사(Lillian Finance, Robo Inu, Saitama, VZZN), market maker(Gotbit 등) 기소 — Gotbit 창업자 유죄 인정·$23M 몰수.
- **★ 노트**: '다수 지갑 분산 소액 매집'은 `flow-actors`(WCI: 지갑 집중·거래소 흐름) 시그널의 직접 대응. crypto fold 양성 시드.
- **출처**:
  - DOJ(매사추세츠) "Eighteen Individuals and Entities Charged…crypto markets" https://www.justice.gov/usao-ma/pr/eighteen-individuals-and-entities-charged-international-operation-targeting-widespread
  - DOJ(북부 캘리포니아) "Ten Foreign Nationals Charged…crypto market manipulation" https://www.justice.gov/usao-ndca/pr/ten-foreign-nationals-charged-international-operation-targeting-cryptocurrency-market
  - Phillips & Cohen "First Criminal Charges for Crypto Market Manipulation" https://www.phillipsandcohen.com/first-ever-criminal-charges-filed-cryptocurrency-market/
  - Arnold & Porter "Wash Trading and Pump and Dump" https://www.arnoldporter.com/en/perspectives/blogs/enforcement-edge/2024/10/remaking-the-classics

---

## 수집 메모 (다음 정밀화 필요)
- CASE-1: 8종목 각 **일별 OHLCV**(2019~2023)와 **거래원별/CFD 창구 순매수**를 `data/price-volume/`·`data/flow-actors/`에 as-of로 채우면 BCI/APS 실측 가능.
- CASE-2: 판결문에서 **정확한 종목명·공시일·t_start**를 특정하면 게이트 A/B/D 실측 가능(현재 판결문 요지 기반).
- CASE-3: 온체인(지갑 집중·거래소 유입)은 블록높이 동결로 재현 수집 가능.
- 모든 수치·날짜는 **1차 출처(법원 판결문·DART·규제 발표)** 로 교차검증 후 `id_unverified=false` 전환.
