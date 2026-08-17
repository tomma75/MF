export const meta = {
  name: 'candidate-scan',
  description: '작전주 신규 후보 다각도 스캔 — 검증 시그니처별 스윕 → 중복제거 → 신규 후보 도시에',
  phases: [
    { title: 'Scan', detail: '시그니처/시장별 병렬 스윕' },
    { title: 'Dossier', detail: '신규 후보 도시에·셋업점수·발화창' },
  ],
}

// args: { exclude_names:[], exclude_syms:[] }
const EX_NAMES = (args && args.exclude_names) || []
const EX_SYMS = (args && args.exclude_syms) || []

const DISCLAIMER = "교육·연구용 회피 관찰 후보. 조작·작전 단정 금지, 매수/매도 신호 아님. 공개 데이터만. 실존 개인·세력 단정 지목 금지(일반화). 대부분의 셋업은 급등하지 않는다(거짓양성 지배)."

const SIG = {
  A: "신설법인/투자조합/SPC 대상 소규모 3자배정으로 경영권 이전 + 저가권(페니) + 신테마(AI/로봇/2차전지 등) 부착",
  B: "관리종목 지정해제 직후 최대주주 교체 + 신사업 IR 릴레이",
  C: "무상감자 + 유상증자 후 거래재개 임박(얇은 유통주식/float)",
  D: "연쇄 CB/BW 발행 + 사명변경(AI·로봇 등) + 최대주주 고비율 주식담보",
  E: "과대 피인수사(자기자본 대비 큰 M&A) + 유증·CB 순환조달 무자본 M&A",
  F: "과거 시세조종·조작 확정/의심 이력 셸의 재활용(사명변경+조합 인수 체인) = 셸 리사이클링",
}

const SCAN_SCHEMA = {
  type: "object",
  properties: {
    candidates: {
      type: "array",
      items: {
        type: "object",
        properties: {
          name: { type: "string", description: "종목명(한글 또는 티커명)" },
          symbol: { type: "string", description: "KR 6자리 코드 또는 US 티커. 불명이면 UNKNOWN" },
          mkt: { type: "string", enum: ["KR", "US"] },
          signature: { type: "string", description: "매칭 시그니처 코드(A~F) 하나 이상, 예: 'A,D'" },
          evidence: { type: "string", description: "왜 이 시그니처인지 1~2문장 근거(공시/사건, 날짜 포함)" },
          approx_price_state: { type: "string", description: "대략적 가격 국면(저가권/횡보/1차팝후냉각/거래정지 등). 불명이면 UNKNOWN" },
          source: { type: "string", description: "대표 출처 URL 1개" },
        },
        required: ["name", "symbol", "mkt", "signature", "evidence"],
      },
    },
  },
  required: ["candidates"],
}

const DOSSIER_SCHEMA = {
  type: "object",
  properties: {
    name: { type: "string" },
    symbol: { type: "string" },
    mkt: { type: "string", enum: ["KR", "US"] },
    signature: { type: "string" },
    verified: { type: "boolean", description: "종목 정체·핵심 공시가 웹검색으로 교차확인됐는가" },
    setup_score: { type: "integer", description: "발화 전 셋업 완성도(0~100). 보정 전 유사도이며 확률 아님" },
    what: { type: "string", description: "무슨 회사/무슨 일이 벌어지는가 3~4문장" },
    why_matches: { type: "string", description: "검증 시그니처와 어떻게 부합하는가(구조 근거)" },
    ignition_window: { type: "string", description: "예상 발화창(날짜 앵커가 있으면 구체적으로, 없으면 개방형+사유)" },
    trigger: { type: "string", description: "발화 트리거(게이트B: 거래대금 급증+장대양봉을 촉발할 구조 이벤트)" },
    falsify: { type: "string", description: "반증조건(무엇이 관측되면 후보에서 탈락)" },
    counterview: { type: "string", description: "이 후보가 정상 기업일 반대 해석(적대적 검토)" },
    already_known: { type: "boolean", description: "널리 알려진 과거 확정 사건/코호트 종목과 사실상 동일한가" },
    sources: { type: "array", items: { type: "string" } },
  },
  required: ["name", "symbol", "mkt", "signature", "setup_score", "what", "why_matches", "ignition_window", "trigger", "falsify", "counterview", "sources"],
}

phase('Scan')
const angles = [
  { key: "KR-A", mkt: "KR", sigs: ["A"], hint: "코스닥/코넥스 소형주 중 최근 3~6개월 내 투자조합·신설SPC 대상 소규모 3자배정 유상증자로 최대주주가 바뀐 저가권(수백~수천원) 종목. DART 최대주주변경·3자배정 유증 공시 위주로." },
  { key: "KR-B", mkt: "KR", sigs: ["B"], hint: "2026년 관리종목/투자주의환기 지정해제 직후 최대주주 교체와 신사업(AI·로봇·2차전지·바이오) IR이 붙은 코스닥 종목." },
  { key: "KR-C", mkt: "KR", sigs: ["C"], hint: "최근 무상감자+유상증자 병행 후 거래재개가 임박했거나 막 재개된, 유통주식이 얇은 코스닥 종목." },
  { key: "KR-D", mkt: "KR", sigs: ["D"], hint: "최근 1년 연쇄 CB/BW 발행 + 사명변경(특히 AI/로봇/우주/방산) + 최대주주 고비율 주식담보(질권)를 동반한 코스닥 종목." },
  { key: "KR-EF", mkt: "KR", sigs: ["E", "F"], hint: "무자본 M&A형(피인수사가 자기자본 대비 큰 딜, 유증·CB 순환조달) 및 과거 시세조종 확정/의심 이력 셸이 사명변경+조합 인수 체인으로 재활용된 코스닥 종목." },
  { key: "US-micro", mkt: "US", sigs: ["A", "F"], hint: "나스닥/NYSE American 초소형주 중 최근 소셜미디어 프로모션·역외 지배구조 변경·ATM 대량설정·SEC 12(k) 정지 또는 Nasdaq T12 halt가 있었던 pump-suspect 종목(2026년)." },
  { key: "US-reverse", mkt: "US", sigs: ["E", "C"], hint: "나스닥 초소형주 중 최근 역합병(reverse merger)/역분할(reverse split) 후 얇은 float + 신테마(AI·crypto treasury·quantum) 부착으로 급등 셋업이 잡히는 종목(2026년)." },
]

const scanResults = await parallel(angles.map(a => () =>
  agent(
    `당신은 작전주(시세조종 의심주) 회피·교육 연구의 신규 후보 스캐너다. ${DISCLAIMER}\n\n`+
    `임무: 아래 시그니처에 부합하는 ${a.mkt} 시장 신규 후보를 웹검색으로 폭넓게 찾아라(각 ${a.key} 앵글에서 5~12개 목표). 최신(2026년 상·하반기) 공시·뉴스 중심.\n`+
    `대상 시그니처:\n${a.sigs.map(s => `  (${s}) ${SIG[s]}`).join("\n")}\n`+
    `추가 힌트: ${a.hint}\n\n`+
    `규칙:\n`+
    `- 각 후보는 반드시 공개 공시/뉴스 근거(날짜)와 출처 URL을 가진다. 근거 없는 추측 금지.\n`+
    `- 종목코드(KR 6자리/US 티커)를 최대한 확인. 불명이면 symbol=UNKNOWN.\n`+
    `- 아래 '이미 코호트/시드'에 있는 종목은 제외(중복 스캔 낭비):\n  이름: ${EX_NAMES.join(", ")}\n  코드: ${EX_SYMS.join(", ")}\n`+
    `- 실존 개인 실명 단정 비방 금지. 조작 단정 금지 — '구조가 시그니처에 부합하는 관찰 후보'로만 기술.\n`+
    `- 한국 시세 포털이 403이면 공시(DART/KIND)·뉴스 텍스트만으로 구조를 기술하고 가격은 UNKNOWN.\n`+
    `candidates 배열로 반환.`,
    { label: `scan:${a.key}`, phase: 'Scan', schema: SCAN_SCHEMA }
  ).then(r => (r && r.candidates ? r.candidates.map(c => ({ ...c, angle: a.key })) : []))
))

// --- dedup + exclude cohort/seed (barrier justified: cross-scanner dedup) ---
const norm = s => String(s || "").replace(/[^0-9A-Za-z가-힣]/g, "").toUpperCase()
const exSym = new Set(EX_SYMS.map(norm))
const exName = new Set(EX_NAMES.map(n => norm(String(n).split("(")[0])))
const seen = new Map()
for (const c of scanResults.flat().filter(Boolean)) {
  const ns = norm(c.symbol), nn = norm(String(c.name).split("(")[0])
  if (ns && ns !== "UNKNOWN" && exSym.has(ns)) continue
  if (exName.has(nn)) continue
  const key = (ns && ns !== "UNKNOWN") ? ns : nn
  if (!key) continue
  if (seen.has(key)) {
    // merge signatures/angles
    const prev = seen.get(key)
    prev.signature = Array.from(new Set((prev.signature + "," + c.signature).split(/[,\s]+/).filter(Boolean))).join(",")
    prev._hits = (prev._hits || 1) + 1
    if (!prev.angle.includes(c.angle)) prev.angle += "," + c.angle
  } else {
    seen.set(key, { ...c, _hits: 1 })
  }
}
let fresh = Array.from(seen.values())
// rank: multi-signature / multi-scanner first
fresh.sort((a, b) => (b._hits - a._hits) || (b.signature.split(",").length - a.signature.split(",").length))
const CAP = 10
const dropped = fresh.length - CAP
if (dropped > 0) log(`신규 후보 ${fresh.length}건 중 상위 ${CAP}건만 도시에화(하위 ${dropped}건은 목록만 반환).`)
const toScore = fresh.slice(0, CAP)

log(`스캔 완료: 원시 후보 ${scanResults.flat().filter(Boolean).length} → 중복/코호트 제거 후 신규 ${fresh.length}건. 상위 ${toScore.length}건 도시에화 진행.`)

phase('Dossier')
const dossiers = await parallel(toScore.map(c => () =>
  agent(
    `당신은 작전주 회피·교육 연구의 후보 심사관이다. ${DISCLAIMER}\n\n`+
    `아래 신규 후보 1건을 웹검색으로 교차검증하고 도시에를 작성하라. 적대적으로 검토해 '정상 기업일 가능성'(counterview)도 반드시 채운다.\n`+
    `후보: ${c.name} (${c.symbol}, ${c.mkt}) / 매칭 시그니처: ${c.signature} / 스캔근거: ${c.evidence}\n\n`+
    `요구사항:\n`+
    `- 종목 정체(정확한 코드/현 사명/과거 사명)와 핵심 공시를 검색으로 확인(verified). 확인 안 되면 verified=false, setup_score 대폭 감점.\n`+
    `- setup_score(0~100)=발화 전 셋업 완성도의 '보정 전 유사도'(확률 아님). 저가권·얇은 float·조합/셸 지배구조·순환조달·신테마 부착·담보비율 등 구조 요소로 산정.\n`+
    `- ignition_window: 확정 일정 앵커(유증 납입일·거래재개일·CB 전환청구 개시일·상장일)가 있으면 구체적으로, 없으면 '개방형'+사유.\n`+
    `- falsify(반증조건)와 counterview(적대적 반대해석)를 구체적으로. already_known: 널리 알려진 확정사건/코호트와 동일하면 true.\n`+
    `- 조작 단정·매수신호 금지. 출처 URL 최소 2개.\n`+
    `도시에를 스키마대로 반환.`,
    { label: `dossier:${c.name}`, phase: 'Dossier', schema: DOSSIER_SCHEMA }
  ).then(d => d ? { ...d, angle: c.angle, hits: c._hits } : null)
))

const scored = dossiers.filter(Boolean)
scored.sort((a, b) => (b.setup_score || 0) - (a.setup_score || 0))

return {
  as_of: "SCAN",
  raw_count: scanResults.flat().filter(Boolean).length,
  fresh_count: fresh.length,
  scored_count: scored.length,
  dossiers: scored,
  also_found: fresh.slice(CAP).map(c => ({ name: c.name, symbol: c.symbol, mkt: c.mkt, signature: c.signature, evidence: c.evidence })),
}
