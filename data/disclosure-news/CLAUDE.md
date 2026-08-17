# data/disclosure-news/ — 공시·뉴스·이벤트 아카이브 (Disclosure & News)

> 목적: 작전이 "터지기 전" 뿌려지는 **근거자료성 기사·공시**를 시점 동결해 아카이브.
> 사용자 가설의 핵심 소스. **소급 오염(look-ahead) 방지가 생명**이다.

## 다루는 데이터
- 공시(증자·CB/BW·최대주주 변경·테마 편입·실적), 정정공시
- 뉴스/보도자료/IR, 테마 키워드, 루머(출처 표기)

## 절대 규칙 (이 디렉토리 특히 중요)
- **published_at 정확히 기록**: 기사/공시의 *실제 공개 시각*. 내가 나중에 발견한 시각(observed_at)과 반드시 구분.
- **소급 해석 금지**: "지나고 보니 작전 신호였다"는 메모는 raw가 아니라 `analysis/`로.
- 루머·찌라시는 `credibility: rumor`로 라벨, 출처·확산경로 기록.

## 관찰 후보 시그널 (가설 — 단정 금지)
- 호재성 공시/기사의 **반복·점증**(분위기 조성)
- 자금조달(CB/BW/유증) 공시와 주가 흐름의 시점 관계
- 동일 테마 기사 클러스터링(언론 동원 의심)

## 스키마(추가 필드)
```
doc_type(disclosure/news/ir/rumor), headline, body_or_summary,
credibility(official/press/rumor), theme_tags[]
```
+ 공통 필드
