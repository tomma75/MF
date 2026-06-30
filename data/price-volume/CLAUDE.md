# data/price-volume/ — 가격·거래량 시계열 (Price & Volume)

> 목적: 작전 전 **수급 흔적이 가격/거래량에 남기는 정량 패턴** 보존.
> 해석·판정은 하지 않는다(→ `analysis/`). 여기서는 raw 시계열만.

## 다루는 데이터
- OHLCV(시·고·저·종·거래량), 호가 잔량, 회전율(turnover), 시가총액
- 변동성(ATR 등), 거래대금, 상·하한가/서킷 이벤트

## 관찰 후보 시그널 (가설 — 단정 금지)
- 저변동·횡보 중 **꾸준한 거래량 증가**(은밀한 매집 의심)
- 특정 가격대 반복 방어(매집 단가대), 종가 관리 패턴
- 회전율 급증 없이 점진적 상승(저유동 종목 누적)

> 위는 **검증 대상 가설**이다. 대조군과 비교해 우도비가 나오기 전엔 "신호"라 부르지 않는다.

## 스키마(추가 필드)
```
open, high, low, close, volume, turnover_rate, market_cap, interval(1d/1h/...)
```
+ 공통 필드(asset_class, symbol, observed_at, published_at, source, url)

## 자산군 주의
- `kr_stock`: 상·하한가(±30%), 동시호가, VI 발동 고려
- `crypto`: 24h 무정지, 상한 없음 → 정규화 기준 다름
- `global_stock`: 시간대·거래소별 분리
