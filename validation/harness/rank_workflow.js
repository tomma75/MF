export const meta = {
  name: 'ignition-rank',
  description: '폭등(점화) 가능성 Top 랭킹 — active preramp 후보를 5팩터 루브릭으로 채점',
  phases: [{ title: 'Score', detail: '후보별 점화 가능성 팩터 채점' }],
}

const cohort = (typeof args === 'string' ? JSON.parse(args) : args) || []
const DISC = "교육·연구용 회피 관찰. 조작·작전 단정 금지, 매수/매도 신호 아님. 점수는 보정 전 유사도이지 확률·수익예측 아님. 대부분의 셋업은 급등하지 않는다."

const SCHEMA = {
  type: "object",
  properties: {
    name: { type: "string" },
    symbol: { type: "string" },
    verified: { type: "boolean", description: "최근(수주 내) 가격·거래대금·촉매를 웹검색으로 교차확인했는가" },
    current_state: { type: "string", description: "현재 가격·거래대금·발화 여부 국면 1문장. 데이터 없으면 NO_DATA 명기" },
    f_anchor: { type: "integer", description: "앵커 근접·확정성 0~25. 임박(수일~수주)+확정 일정(납입·청약·재개·상장)일수록 높게. 개방형·미확정은 낮게" },
    f_float: { type: "integer", description: "유통물량 얇기 0~20. 무상감자·역분할·낮은 유통주식·저가권일수록 높게" },
    f_structure: { type: "integer", description: "구조 완성도 0~25. 조합/셸 지배·순환조달(CB·유증)·신테마 부착·무자본M&A 결합도" },
    f_momentum: { type: "integer", description: "모멘텀 전조 0~15. 최근 거래대금·회전율 급증·선행 스파이크·동일세력 클러스터 발화 인접" },
    f_clean: { type: "integer", description: "반증 부재 0~15. 반증조건(정상화·상폐·미발화 소멸·실적정당화)이 관측되지 않을수록 높게" },
    ignition_score: { type: "integer", description: "위 5팩터 합(0~100). 반드시 합과 일치" },
    key_catalyst: { type: "string", description: "가장 임박한 발화 촉매와 예상 시점(날짜 있으면 명시)" },
    thesis: { type: "string", description: "왜 점화 유력인지 1~2문장(구조 근거)" },
    counter: { type: "string", description: "점화 실패/정상 기업 반대해석 1문장" },
    evidence: { type: "array", items: { type: "string" }, description: "날짜 포함 근거 2~4개(공시·뉴스)" },
    sources: { type: "array", items: { type: "string" } },
  },
  required: ["name", "symbol", "verified", "current_state", "f_anchor", "f_float", "f_structure", "f_momentum", "f_clean", "ignition_score", "key_catalyst", "thesis", "counter", "evidence"],
}

phase('Score')
const scored = await parallel(cohort.map(c => () =>
  agent(
    `당신은 작전주 회피·교육 연구의 '점화(폭등) 가능성' 심사관이다. ${DISC}\n\n`+
    `아래 preramp(발화 전) 후보 1건을 웹검색으로 최신 상태(가격·거래대금·촉매 진행)를 확인하고, 점화 임박도를 5팩터로 채점하라.\n`+
    `후보: ${c.name} (${c.symbol}, ${c.mkt})\n`+
    `등록 발화창: ${c.window}\n등록 트리거: ${c.trigger}\n등록 반증조건: ${c.falsify}\n등록 노트: ${c.note}\n\n`+
    `채점 규칙(각 팩터 상한 준수, ignition_score=5팩터 합):\n`+
    `- f_anchor(0~25): 확정 일정이 임박할수록 高. 이미 지난·개방형·무기한이면 低.\n`+
    `- f_float(0~20): 무상감자·역분할·얇은 유통주식·저가권일수록 高.\n`+
    `- f_structure(0~25): 조합/셸 지배 + 순환조달(CB·유증) + 신테마 부착 + 무자본M&A 결합도.\n`+
    `- f_momentum(0~15): 최근 거래대금·회전율 급증·선행 스파이크·동일세력 클러스터 발화 인접.\n`+
    `- f_clean(0~15): 반증조건(정상화·상폐·미발화 소멸·실적정당화) 미관측일수록 高.\n`+
    `한국 사이트가 403이면 공시·뉴스 텍스트로 구조를 평가하고 current_state에 가격 NO_DATA 명기(momentum 보수적으로).\n`+
    `조작 단정 금지 — '구조적으로 점화 셋업이 완성/미완성'으로만 기술. 스키마대로 반환.`,
    { label: `rank:${c.symbol}`, phase: 'Score', schema: SCHEMA }
  )
))

const rows = scored.filter(Boolean).sort((a, b) => (b.ignition_score || 0) - (a.ignition_score || 0))
return { as_of: "RANK", n: rows.length, ranked: rows }
