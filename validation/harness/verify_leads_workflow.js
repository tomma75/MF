export const meta = {
  name: 'verify-leads',
  description: '사전발굴 리드 검증 패스 — 각 리드를 DART/KRX/뉴스로 교차검증(fresh 서치 예산)',
  phases: [{ title: 'Verify', detail: '리드별 정체·구조·미발화 교차검증' }],
}
const leads = (typeof args === 'string' ? JSON.parse(args) : args) || []
const DISC = "교육·연구용 회피 관찰. 조작 단정 금지. 매매신호 아님. 공개 데이터만. 반드시 웹검색으로 원문 교차확인 — 확인 못하면 verified=false로 정직 표기."

const SCHEMA = {
  type: "object",
  properties: {
    name: { type: "string" }, symbol: { type: "string" }, subtype: { type: "string" },
    verified: { type: "boolean", description: "종목 정체·핵심 셋업 공시를 웹검색으로 실제 교차확인했는가(추정 금지)" },
    identity: { type: "string", description: "현 사명·과거 사명·시장(코스닥/코스피)·업종 확인 결과" },
    not_surged: { type: "boolean", description: "아직 발화 전(최근 상한가·+15%↑ 없음)인가" },
    price_state: { type: "string", description: "대략 주가·시총·최근 등락(확인분). 불명 NO_DATA" },
    signatures: { type: "string", description: "실제 확인된 A~F 시그니처 코드+근거(날짜). 확인 안 되면 '미확인'" },
    setup_score: { type: "integer", description: "발화 전 셋업 완성도 0~100(보정 전 유사도). verified=false면 대폭 감점" },
    ignition_window: { type: "string", description: "예상 발화창(확정 앵커 날짜 있으면 명시)" },
    trigger: { type: "string" }, falsify: { type: "string" }, counterview: { type: "string" },
    add_to_cohort: { type: "boolean", description: "verified=true AND 구조 부합 AND 발화 전이면 true" },
    sources: { type: "array", items: { type: "string" } },
  },
  required: ["name", "symbol", "verified", "identity", "not_surged", "signatures", "setup_score", "ignition_window", "add_to_cohort"],
}

phase('Verify')
const rows = await parallel(leads.map(l => () =>
  agent(
    `${DISC}\n\n리드 검증: ${l.name} (${l.symbol}) — 하위유형 ${l.subtype}\n`+
    `웹검색(WebSearch/WebFetch를 ToolSearch로 로드)으로 확인하라:\n`+
    `1) 종목 정체(현 사명·과거 사명·코스닥/코스피·업종·시총) — identity.\n`+
    `2) 핵심 셋업 공시가 실재하는가(조합/SPC 3자배정·최대주주 변경·감자/역병합·연쇄 CB·사명변경·코인 트레저리·현물출자 M&A 등) — signatures에 확인된 것만, 날짜 포함.\n`+
    `3) 아직 발화 전(최근 상한가·+15%↑ 없음)인가 — not_surged, price_state.\n`+
    `4) 확정 발화 앵커(유증 납입일·거래재개일·CB 전환개시일·주총일) — ignition_window.\n`+
    `⚠️ 원문 확인 못하면 verified=false + setup_score 대폭 감점. 추정으로 verified=true 금지. add_to_cohort는 verified=true+구조부합+발화전일 때만.\n스키마대로 반환.`,
    { label: `vf:${l.name}`, phase: 'Verify', schema: SCHEMA }
  )
))
const r = rows.filter(Boolean)
const add = r.filter(x => x.verified && x.add_to_cohort)
return { as_of: "VERIFY-LEADS", n: r.length, verified: r.filter(x => x.verified).length, add_count: add.length, rows: r.sort((a, b) => (b.setup_score || 0) - (a.setup_score || 0)) }
