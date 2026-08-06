export const meta = {
  name: 'gainer-reverse-scan',
  description: '오늘 급상승(상한가) 리스트 역스캔 — 작전 시그니처 보유·사전관측성·시장보정 초과수익 판정',
  phases: [{ title: 'Investigate', detail: '급등 종목별 시그니처·리드타임·초과수익 조사' }],
}

const items = (typeof args === 'string' ? JSON.parse(args) : args) || []
const DISC = "교육·연구용 회피 관찰. 조작·작전 단정 금지(모니터링 후보). 매수/매도 신호 아님. 공개 데이터만. 상한가=작전 아님 — 정상 급등(실적·뉴스)과 구조적 작전 시그니처를 반드시 구분."

const SIG = "A 조합/SPC 3자배정 경영권 이전+저가권+신테마 · B 관리종목 해제 직후 최대주주 교체+신사업IR · C 무상감자·역분할 후 얇은 float · D 연쇄 CB/BW+사명변경(AI·로봇)+최대주주 고비율 담보 · E 무자본 M&A(과대 피인수사+유증·CB 순환조달) · F 조작 확정/의심 셸 재활용·소셜 프로모션 펌프"

const SCHEMA = {
  type: "object",
  properties: {
    name: { type: "string" }, symbol: { type: "string", description: "KR 6자리/US 티커. 불명 UNKNOWN" },
    mkt: { type: "string", enum: ["KR", "US"] },
    verified: { type: "boolean", description: "종목 정체·오늘 급등을 웹검색으로 교차확인했는가" },
    move_today: { type: "string", description: "오늘 등락률(예: +30.0% 상한가)과 대략 거래대금/거래량" },
    index_ret: { type: "string", description: "같은 날 지수(코스닥/코스피/나스닥) 등락률" },
    excess_ret: { type: "string", description: "초과수익 ≈ 종목−지수(−섹터). 하락장이면 특히 크게 명시" },
    gate_b: { type: "string", description: "게이트B(거래대금·회전율 폭증+장대양봉) true/false/unknown+근거" },
    classification: { type: "string", enum: ["SIGNATURE", "LEGIT", "UNCLEAR", "NOT_TARGET"], description: "SIGNATURE=작전 시그니처 보유 / LEGIT=실적·정상뉴스 급등 / UNCLEAR=불명 / NOT_TARGET=레버리지·인버스 ETP 등 대상 아님" },
    signatures: { type: "string", description: "해당 시 부합 시그니처 코드(A~F)와 근거. 없으면 '없음'" },
    pre_observable: { type: "string", description: "오늘 터지기 전에 우리 시그니처로 사전 관측 가능했나? yes/no/부분 + 리드타임(며칠 전부터 셋업 존재)" },
    why_surged: { type: "string", description: "오늘 급등의 실제 촉매(공시·뉴스·테마)" },
    add_to_cohort: { type: "boolean", description: "SIGNATURE이고 사전관측 가능/재활용 가치가 있어 코호트 편입 권장인가" },
    note: { type: "string", description: "핵심 요지 2~3문장" },
    sources: { type: "array", items: { type: "string" } },
  },
  required: ["name", "symbol", "mkt", "verified", "move_today", "excess_ret", "classification", "signatures", "pre_observable", "why_surged", "add_to_cohort", "note"],
}

phase('Investigate')
const res = await parallel(items.map(it => () =>
  agent(
    `당신은 작전주 회피·교육 연구의 역스캔 조사관이다. ${DISC}\n\n`+
    `오늘 급상승(상한가) 리스트에 오른 종목 1건을 웹검색으로 조사하라: ${it.name} (${it.hint || ''}, ${it.mkt}).\n`+
    `검증 시그니처: ${SIG}\n\n`+
    `판정할 것:\n`+
    `1) 종목 정체·코드 확인. 레버리지/인버스 ETP·ETN이면 classification=NOT_TARGET.\n`+
    `2) 오늘 등락률·거래대금(move_today)과 같은 날 지수 등락(index_ret) → 초과수익(excess_ret). 오늘은 하락장(코스피 -4.5%/나스닥 -0.8%)이므로 상한가면 초과수익이 매우 큼(순수 알파).\n`+
    `3) gate_b(거래대금·회전율 폭증).\n`+
    `4) classification: SIGNATURE(우리 A~F 구조 보유) / LEGIT(실적·정상 뉴스) / UNCLEAR / NOT_TARGET.\n`+
    `5) pre_observable: 오늘 터지기 전에 조합 3자배정·감자·사명변경·CB·최대주주 교체 등 셋업이 이미 공시로 존재해 사전 관측 가능했는가 + 리드타임(며칠 전부터).\n`+
    `6) add_to_cohort: SIGNATURE + 사전관측 가치가 있으면 true.\n`+
    `조작 단정 금지 — '구조가 부합/불부합'으로만. 스키마대로 반환.`,
    { label: `gain:${it.name}`, phase: 'Investigate', schema: SCHEMA }
  )
))

const rows = res.filter(Boolean)
const order = { SIGNATURE: 0, UNCLEAR: 1, LEGIT: 2, NOT_TARGET: 3 }
rows.sort((a, b) => (order[a.classification] ?? 9) - (order[b.classification] ?? 9))
return { as_of: "GAINER-SCAN", n: rows.length, rows }
