export const meta = {
  name: 'deep-verify',
  description: '단일 종목 다각도 최종검증 — 5개 독립 렌즈 교차검증 후 적대적 종합 판정',
  phases: [{ title: 'Lenses', detail: '5개 독립 렌즈 병렬 교차검증' }, { title: 'Synthesis', detail: '적대적 종합 판정' }],
}
const T = (typeof args === 'string' ? JSON.parse(args) : args) || {}
const NAME = T.name, SYM = T.symbol, MKT = T.mkt || 'kr_stock'
const DISC = "교육·연구용 회피 관찰. 조작 단정 금지(모니터링 후보만). 실존 인물·세력 단정 지목·비방 금지, 개인은 익명화·일반화. 매매신호 아님. 공개 데이터만. 반드시 웹검색으로 원문 교차확인 — 확인 못하면 confidence 낮추고 NO_DATA 정직 표기."

const LENSES = [
  { key: '정체·이력', ask: `현 사명·과거 사명 이력(사명변경 연혁)·시장(코스닥/코스피)·업종·시가총액·최대주주 변천을 웹검색으로 확인. 껍데기(셸) 재활용·잦은 사명변경·최대주주 연쇄교체 흔적이 있는가? 사실만, 날짜 포함.` },
  { key: '구조·시그니처', ask: `A~F 조작 시그니처(A 조합/SPC 3자배정 경영권이전+저가권+신테마, B 관리종목해제후 최대주주교체+신사업IR, C 무상감자·역병합후 얇은float, D 연쇄CB/BW+사명변경 AI/로봇+최대주주 고비율담보, E 무자본M&A 순환조달, F 셸 재활용·소셜펌프) 중 실제 공시로 확인되는 것만 코드+근거일자로. 확인 안 되면 '미확인'. 억지 부합 금지.` },
  { key: '가격·시장보정', ask: `현재 주가·52주 고저 대비 위치·최근 20거래일 등락·거래대금/회전율 추이. 시장보정: 최근 코스닥/코스피 지수수익·해당 테마섹터 수익 대비 초과수익(excess_ret)이 있었는가, 아니면 지수·테마 동반(베타)인가. 이미 급등했는지/아직 바닥권인지 판정. 거래정지·정리매매·단기과열/투자경고 지정 여부도 확인.` },
  { key: '촉매·앵커', ask: `수일~수주 내 확정 촉매(유상증자 납입일·거래재개일·감자 재상장일·CB 전환개시일·조합 최대주주 확정·주총 안건) 날짜 앵커가 실재하는가. 개방형 기대(테마 편승)와 확정 앵커를 구분. 각 촉매의 공시 근거일자.` },
  { key: '적대적 반증', ask: `이 종목이 '더 오를 여력 큰 pre-ramp 후보'라는 가설을 **깨는** 증거를 최대한 찾아라: 이미 충분히 급등함/펀더멘털 정당화(실적·수주)/거래정지·상폐 리스크/유통물량 과다/촉매 없음/과거 반복된 급등후 급락 패턴. 반증이 강하면 명확히 그렇게 보고.` },
]

const LSCHEMA = {
  type: "object",
  properties: {
    lens: { type: "string" },
    findings: { type: "string", description: "이 렌즈에서 웹검색으로 확인한 사실(날짜 포함). 확인 못한 항목은 NO_DATA 명기" },
    verified_facts: { type: "array", items: { type: "string" }, description: "원문 교차확인된 사실만 bullet" },
    red_flags: { type: "array", items: { type: "string" }, description: "이 렌즈에서 드러난 회피 신호(있으면)" },
    disconfirming: { type: "array", items: { type: "string" }, description: "가설을 약화·반증하는 증거(있으면)" },
    lens_score: { type: "integer", description: "이 렌즈 기준 '회피대상 유사도' 0~100(보정 전). 근거 부족하면 낮게" },
    confidence: { type: "string", enum: ["high", "med", "low"], description: "웹검증 충실도" },
    sources: { type: "array", items: { type: "string" } },
  },
  required: ["lens", "findings", "verified_facts", "lens_score", "confidence"],
}

phase('Lenses')
const lensRes = await parallel(LENSES.map(L => () =>
  agent(
    `${DISC}\n\n대상: ${NAME} (${SYM}, ${MKT})\n검증 렌즈: **${L.key}**\n\n${L.ask}\n\n`+
    `WebSearch/WebFetch를 ToolSearch로 로드해 실제 검색하라. 한국 사이트 403이면 다른 경로(뉴스·공시요약)로 우회하고, 그래도 못 찾으면 NO_DATA로 정직 표기. 추정으로 사실 단정 금지. 스키마대로 반환.`,
    { label: `lens:${L.key}`, phase: 'Lenses', schema: LSCHEMA }
  )
))
const lenses = lensRes.filter(Boolean)

phase('Synthesis')
const SYN = {
  type: "object",
  properties: {
    verdict: { type: "string", enum: ["STRONG_WATCH", "WATCH", "WEAK", "EXCLUDE"], description: "종합 판정: STRONG_WATCH(다렌즈 부합+확정촉매+바닥권), WATCH(부합하나 불확실), WEAK(근거약함), EXCLUDE(반증우세/이미급등/정지)" },
    upside_verdict: { type: "string", description: "'더 오를 여력' 최종 판단 1~2문장(현재위치+촉매임박 종합)" },
    consensus_facts: { type: "array", items: { type: "string" }, description: "여러 렌즈에서 일관되게 확인된 핵심 사실" },
    strongest_redflags: { type: "array", items: { type: "string" } },
    strongest_disconfirming: { type: "array", items: { type: "string" }, description: "가장 강한 반증(반드시 포함)" },
    confidence: { type: "string", enum: ["high", "med", "low"] },
    net_score: { type: "integer", description: "종합 회피대상 유사도 0~100(보정 전, 반증 반영). 정지/이미급등이면 강등" },
    keep_in_cohort: { type: "boolean", description: "코호트 pre-ramp로 유지할 가치가 있는가" },
    watch_anchor: { type: "string", description: "F/U에서 지켜볼 확정 날짜 앵커(있으면)" },
  },
  required: ["verdict", "upside_verdict", "consensus_facts", "strongest_disconfirming", "confidence", "net_score", "keep_in_cohort"],
}
const synth = await agent(
  `${DISC}\n\n대상: ${NAME} (${SYM}). 아래 5개 독립 렌즈 결과를 **적대적으로** 종합하라. 렌즈 간 모순은 드러내고, 약한 근거는 깎고, 반증을 반드시 정면으로 다뤄라. 확정 촉매 앵커 없으면 STRONG_WATCH 금지.\n\n`+
  `렌즈 결과 JSON:\n${JSON.stringify(lenses, null, 1)}\n\n조작 단정·인물 지목 금지. 스키마대로 반환.`,
  { label: 'synth', phase: 'Synthesis', schema: SYN }
)
return { target: { name: NAME, symbol: SYM, mkt: MKT }, lenses, synthesis: synth }
