export const meta = {
  name: 'upside-rank',
  description: '더 오를 여력(forward-upside) Top 랭킹 — 잔여상방·촉매임박·거래가능·float·구조 5팩터',
  phases: [{ title: 'Score', detail: '후보별 잔여 상방 채점' }],
}
const cohort = (typeof args === 'string' ? JSON.parse(args) : args) || []
const DISC = "교육·연구용 회피 관찰. 조작 단정 금지, 매수/매도 신호 아님. 점수는 보정 전 유사도이지 확률·수익예측 아님. 대부분의 셋업은 급등하지 않는다."

const SCHEMA = {
  type: "object",
  properties: {
    name: { type: "string" }, symbol: { type: "string" },
    verified: { type: "boolean", description: "최근 가격·거래정지·촉매를 웹검색으로 교차확인" },
    tradeable: { type: "boolean", description: "현재 거래 가능한가(거래정지·정리매매·상폐면 false → 폭등 불가)" },
    current_state: { type: "string", description: "현재 주가·52주 위치·최근 등락·정지여부 1문장. NO_DATA 명기 가능" },
    f_position: { type: "integer", description: "잔여 상방(현재 위치) 0~25. 52주 저점·바닥권·아직 미상승일수록 높게(더 오를 여지). 이미 급등·고점권이면 낮게" },
    f_catalyst: { type: "integer", description: "촉매 임박도 0~25. 수일~수주 내 확정 촉매(유증 납입일·거래재개일·감자 재상장·CB 전환개시·조합 최대주주 확정)일수록 높게. 개방형·미확정은 낮게" },
    f_tradeable: { type: "integer", description: "거래가능·반증부재 0~15. 거래정지·상폐 리스크·반증조건 충족이면 대폭 감점(정지면 0~3)" },
    f_float: { type: "integer", description: "얇은 float 0~15. 무상감자·역병합·조합 저지분·얇은 유통주식일수록 높게" },
    f_structure: { type: "integer", description: "A~F 구조 완성도 0~20. 조합3자배정·순환조달·셸·신테마 결합도" },
    upside_score: { type: "integer", description: "위 5팩터 합(0~100). 거래정지면 상한 20으로 강등" },
    key_catalyst: { type: "string", description: "가장 임박한 촉매와 예상 시점(날짜)" },
    thesis: { type: "string", description: "왜 '여기서 더 오를' 여력이 있는지 1~2문장" },
    counter: { type: "string", description: "더 못 오를/하락할 반대해석 1문장" },
    evidence: { type: "array", items: { type: "string" } },
    sources: { type: "array", items: { type: "string" } },
  },
  required: ["name", "symbol", "verified", "tradeable", "current_state", "f_position", "f_catalyst", "f_tradeable", "f_float", "f_structure", "upside_score", "key_catalyst", "thesis", "counter"],
}

phase('Score')
const scored = await parallel(cohort.map(c => () =>
  agent(
    `당신은 작전주 회피·교육 연구의 '더 오를 여력(forward upside)' 심사관이다. ${DISC}\n\n`+
    `아래 pre-ramp 후보의 **여기서 더 오를 여력**을 5팩터로 채점하라. 핵심 질문: "이미 오른 게 아니라, 아직 바닥이고 곧 촉매가 있어 앞으로 오를 여지가 큰가?"\n`+
    `후보: ${c.name} (${c.symbol}, ${c.mkt})\n등록창: ${c.window}\n트리거: ${c.trigger}\n반증: ${c.falsify}\n노트: ${c.note}\n\n`+
    `채점(합=upside_score):\n`+
    `- f_position(0~25): **현재 위치=잔여상방**. 52주 저점·바닥권·아직 미상승이면 高(더 오를 여지 큼). 이미 상한가/급등해 고점권이면 低.\n`+
    `- f_catalyst(0~25): 수일~수주 내 **확정** 촉매(유증 납입일·거래재개일·감자 재상장·CB 전환개시·조합 최대주주 확정)면 高. 개방형·미확정 低.\n`+
    `- f_tradeable(0~15): 거래정지·정리매매·상폐 리스크·반증조건 충족이면 대폭 감점(정지=0~3).\n`+
    `- f_float(0~15): 무상감자·역병합·조합 저지분 등 얇은 float일수록 高.\n`+
    `- f_structure(0~20): A~F 구조 완성도.\n`+
    `⚠️ **거래정지면 upside_score 상한 20으로 강등**(정지 중엔 폭등 불가). 이미 저가 대비 크게 오른 종목은 f_position 대폭 감점.\n`+
    `한국 403이면 current_state에 NO_DATA 명기하고 f_position/f_catalyst 보수적으로. 조작 단정 금지. 스키마대로 반환.`,
    { label: `up:${c.symbol}`, phase: 'Score', schema: SCHEMA }
  )
))
const rows = scored.filter(Boolean).sort((a, b) => (b.upside_score || 0) - (a.upside_score || 0))
return { as_of: "UPSIDE-RANK", n: rows.length, ranked: rows }
