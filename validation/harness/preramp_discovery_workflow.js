export const meta = {
  name: 'preramp-discovery',
  description: '사전(pre-ramp) 발굴 채널 — 아직 안 터진 A~F 셋업을 하위유형별로 사냥(리드타임 확보)',
  phases: [
    { title: 'Hunt', detail: '하위유형별 미발화 셋업 스윕' },
    { title: 'Dossier', detail: '신규 후보 도시에·발화창·트리거' },
  ],
}

const cfg = (typeof args === 'string' ? JSON.parse(args) : args) || {}
const EX_NAMES = cfg.exclude_names || []
const EX_SYMS = cfg.exclude_syms || []
const DISC = "교육·연구용 회피 관찰. 조작·작전 단정 금지(모니터링 후보). 매수/매도 신호 아님. 공개 데이터만. 목표는 '아직 급등하지 않은(pre-ramp)' 셋업을 미리 잡아 리드타임을 확보하는 것 — 이미 상한가/급등한 종목이 아니라 발화 전 매집·셋업 단계 종목 우선."

// 사전 발화 셋업 하위유형(발견된 것 포함)
const ANGLES = [
  { key: "조합3자배정", hint: "최근 3~6개월 내 투자조합/SPC 대상 소규모 3자배정 유상증자로 최대주주가 바뀐 저가권(수백~수천원) 코스닥 소형주 중, 아직 급등하지 않은 종목. DART 최대주주변경·3자배정 유증 공시 위주." },
  { key: "임박감자역병합", hint: "무상감자·주식병합(역병합)으로 거래정지 예정이거나 막 재개돼 유통주식이 얇아졌으나 아직 발화하지 않은 코스닥 소형주. 재개 임박 = 발화 대기." },
  { key: "연쇄CB사명변경", hint: "최근 1년 연쇄 CB/BW 발행 + 사명변경(AI·로봇·양자·2차전지) + 최대주주 고비율 주식담보를 동반했으나 아직 급등 전인 코스닥 종목." },
  { key: "크립토트레저리셸", hint: "상폐위기·관리종목 셸을 인수해 사명변경 후 '코인(BTC/ETH/SOL 등) 트레저리'로 피벗한 국내 상장 주식(코인 아님) 중, 아직 대형 발화 전이거나 냉각 국면인 종목. 예: 파라택시스이더리움 유형. 순자산↔주가 반사루프." },
  { key: "중국계외국셸", hint: "중국계·외국기업 KOSDAQ 홀딩스(900번대 등) 중 주식병합+외국계 3자배정+현물출자 M&A+AI/신소재 테마 전환을 진행했으나 아직 발화 전인 종목. 마스터비프·HCHL 아시아 마이크로캡 인접." },
  { key: "관리종목해제후", hint: "2026년 관리종목/투자주의환기 지정해제 직후 최대주주 교체+신사업 IR이 붙었으나 아직 급등 전인 코스닥 종목." },
  { key: "무자본MA순환조달", hint: "자기자본 대비 과대한 피인수사를 유증·CB 순환조달로 인수(무자본 M&A)했으나 아직 발화 전인 코스닥 종목." },
]

const HUNT_SCHEMA = {
  type: "object",
  properties: {
    candidates: { type: "array", items: { type: "object", properties: {
      name: { type: "string" }, symbol: { type: "string", description: "KR 6자리. 불명 UNKNOWN" },
      subtype: { type: "string" },
      setup_evidence: { type: "string", description: "셋업 근거(공시·날짜). A~F 시그니처 코드 포함" },
      not_surged: { type: "boolean", description: "아직 급등(상한가·+15%↑)하지 않은 pre-ramp 상태인가" },
      approx_price: { type: "string", description: "대략 주가·시총" },
      source: { type: "string" },
    }, required: ["name", "symbol", "subtype", "setup_evidence", "not_surged"] } },
  },
  required: ["candidates"],
}

const DOSSIER_SCHEMA = {
  type: "object",
  properties: {
    name: { type: "string" }, symbol: { type: "string" }, subtype: { type: "string" },
    verified: { type: "boolean" },
    not_surged: { type: "boolean", description: "여전히 발화 전(pre-ramp)인가" },
    signatures: { type: "string", description: "부합 A~F 코드+근거" },
    setup_score: { type: "integer", description: "발화 전 셋업 완성도 0~100(보정 전 유사도, 확률 아님)" },
    ignition_window: { type: "string", description: "예상 발화창(확정 앵커 있으면 날짜, 없으면 개방형+사유)" },
    trigger: { type: "string", description: "발화 트리거(게이트B 촉발 구조 이벤트)" },
    falsify: { type: "string" }, counterview: { type: "string", description: "정상 기업일 반대해석" },
    sources: { type: "array", items: { type: "string" } },
  },
  required: ["name", "symbol", "subtype", "verified", "not_surged", "signatures", "setup_score", "ignition_window", "trigger", "falsify", "counterview"],
}

phase('Hunt')
const hunted = await parallel(ANGLES.map(a => () =>
  agent(
    `${DISC}\n\n임무: '${a.key}' 하위유형에 부합하는 **아직 안 터진(pre-ramp)** 코스닥 소형주를 웹검색으로 5~10개 찾아라.\n힌트: ${a.hint}\n\n`+
    `규칙:\n- 각 후보는 공개 공시/뉴스 근거(날짜)+출처. 근거 없는 추측 금지.\n- **이미 상한가·급등한 종목은 제외**(not_surged=true인 발화 전 셋업 우선). 이게 이 채널의 핵심.\n- 종목코드(6자리) 확인. 불명이면 UNKNOWN.\n- 아래 제외(이미 코호트/스캔됨): 이름 ${EX_NAMES.slice(0,60).join(", ")} / 코드 ${EX_SYMS.join(", ")}\n- 조작 단정 금지 — '구조가 부합하는 발화 전 관찰 후보'로만.\ncandidates 배열 반환.`,
    { label: `hunt:${a.key}`, phase: 'Hunt', schema: HUNT_SCHEMA }
  ).then(r => (r && r.candidates ? r.candidates.map(c => ({ ...c, angle: a.key })) : []))
))

// dedup + exclude
const norm = s => String(s || "").replace(/[^0-9A-Za-z가-힣]/g, "").toUpperCase()
const exSym = new Set(EX_SYMS.map(norm)), exName = new Set(EX_NAMES.map(n => norm(String(n).split("(")[0])))
const seen = new Map()
for (const c of hunted.flat().filter(Boolean)) {
  const ns = norm(c.symbol), nn = norm(String(c.name).split("(")[0])
  if (ns && ns !== "UNKNOWN" && exSym.has(ns)) continue
  if (exName.has(nn)) continue
  const key = (ns && ns !== "UNKNOWN") ? ns : nn
  if (!key) continue
  if (seen.has(key)) { const p = seen.get(key); p._hits = (p._hits || 1) + 1; if (!p.angle.includes(c.angle)) p.angle += "," + c.angle }
  else seen.set(key, { ...c, _hits: 1 })
}
let fresh = Array.from(seen.values())
// prefer not-surged + multi-hit
fresh.sort((a, b) => (Number(b.not_surged) - Number(a.not_surged)) || (b._hits - a._hits))
const CAP = 10
if (fresh.length > CAP) log(`신규 후보 ${fresh.length} → 상위 ${CAP} 도시에(나머지 목록만)`)
const toScore = fresh.slice(0, CAP)
log(`Hunt 완료: 원시 ${hunted.flat().filter(Boolean).length} → 신규 ${fresh.length}. 상위 ${toScore.length} 도시에.`)

phase('Dossier')
const dossiers = await parallel(toScore.map(c => () =>
  agent(
    `${DISC}\n\n아래 pre-ramp 후보를 웹검색으로 교차검증하고 도시에를 작성하라. 적대적으로 검토(counterview 필수).\n`+
    `후보: ${c.name} (${c.symbol}) / 하위유형: ${c.subtype} / 셋업근거: ${c.setup_evidence}\n\n`+
    `요구: 종목 정체·코드 확인(verified), 여전히 발화 전인지(not_surged), setup_score(발화 전 셋업 완성도 0~100 보정전유사도), ignition_window(확정 앵커 있으면 날짜), trigger, falsify, counterview, 출처 2개+. 조작 단정 금지.`,
    { label: `dos:${c.name}`, phase: 'Dossier', schema: DOSSIER_SCHEMA }
  ).then(d => d ? { ...d, angle: c.angle, hits: c._hits } : null)
))
const scored = dossiers.filter(Boolean).sort((a, b) => (b.setup_score || 0) - (a.setup_score || 0))
return { as_of: "PRERAMP-DISCOVERY", raw: hunted.flat().filter(Boolean).length, fresh: fresh.length,
  dossiers: scored, also_found: fresh.slice(CAP).map(c => ({ name: c.name, symbol: c.symbol, subtype: c.subtype, setup_evidence: c.setup_evidence, not_surged: c.not_surged })) }
