export const meta = {
  name: 'control-signature-scan',
  description: '대조군 시그니처율 측정 — 안 터진 코스닥 소형주 표본의 A~F 보유율(LR 분모)',
  phases: [{ title: 'Sample', detail: '초성별 코스닥 소형주 표본 추출·시그니처 채점' }],
}

const cfg = (typeof args === 'string' ? JSON.parse(args) : args) || {}
const EXCLUDE = cfg.exclude || []
const SEEDS = cfg.seeds || ["ㄱ","ㄴ","ㄷ","ㄹ","ㅁ","ㅂ","ㅅ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ","가","나"]
const DISC = "교육·연구용. 조작 단정 금지. 대조군 표본추출 — 오늘 급등하지 '않은' 평범한 코스닥 소형주에서 우리 A~F 구조 시그니처의 기저 보유율(base rate)을 측정한다. 이것이 우도비(LR)의 분모다."

const SIG = "A 조합/SPC 3자배정 경영권 이전+저가권+신테마 · B 관리종목 해제 직후 최대주주 교체+신사업IR · C 무상감자·역분할 후 얇은 float · D 연쇄 CB/BW+사명변경(AI·로봇)+최대주주 고비율 담보 · E 무자본 M&A(과대 피인수사+유증·CB 순환조달) · F 조작 확정/의심 셸 재활용"

const SCHEMA = {
  type: "object",
  properties: {
    name: { type: "string" }, symbol: { type: "string", description: "KR 6자리. 불명 UNKNOWN" },
    verified: { type: "boolean", description: "실재 코스닥 상장사·시총·오늘 등락을 웹검색으로 확인했는가" },
    is_kosdaq_smallcap: { type: "boolean", description: "코스닥 상장 & 시총 약 300억~5000억 소형주인가(대조군 자격)" },
    market_cap: { type: "string", description: "대략 시가총액(억원)" },
    surged_recently: { type: "boolean", description: "오늘(2026-08-06) 또는 최근 급등(상한가·+15%↑)했는가. true면 대조군 부적격" },
    move_today: { type: "string", description: "오늘 대략 등락률" },
    classification: { type: "string", enum: ["SIGNATURE", "UNCLEAR", "LEGIT", "INVALID"], description: "SIGNATURE=A~F 구조 보유 / UNCLEAR=소프트플래그만 / LEGIT=정상 영업사(구조 없음) / INVALID=대조군 부적격(대형주·급등·상폐·비코스닥)" },
    signatures: { type: "string", description: "부합 시그니처 코드(A~F)+근거. 없으면 '없음'" },
    note: { type: "string", description: "1~2문장 요지" },
    sources: { type: "array", items: { type: "string" } },
  },
  required: ["name", "symbol", "verified", "is_kosdaq_smallcap", "surged_recently", "classification", "signatures"],
}

phase('Sample')
const rows = await parallel(SEEDS.map((seed, i) => () =>
  agent(
    `${DISC}\n\n`+
    `임무: 코스닥 상장 소형주(시총 약 300억~5,000억) 중 **오늘(2026-08-06) 급등하지 않은(상한가·+15%↑ 아님)** 종목 1개를 무작위성 있게 골라 A~F 시그니처를 채점하라.\n`+
    `표본 다양성 시드: 회사명이 '${seed}'(으)로 시작하거나 그 초성 계열인 코스닥 소형주 중에서 고른다(특정 유명주 편향 금지, 평범한 종목 우선).\n`+
    `검증 시그니처: ${SIG}\n\n`+
    `제외(이미 코호트/케이스): ${EXCLUDE.join(", ")}\n\n`+
    `규칙:\n`+
    `- 실재 코스닥 종목인지·시총·오늘 등락을 웹검색으로 확인(verified). 시총 대역 밖·대형주·오늘 급등·상폐·비코스닥이면 classification=INVALID(대조군 부적격).\n`+
    `- classification: SIGNATURE=조합3자배정/감자·역분할/셸사명변경/연쇄CB/무자본M&A 등 A~F 구조를 실제 보유 / UNCLEAR=소프트플래그(AI사명 등)만 / LEGIT=정상 영업사(구조 없음) / INVALID=부적격.\n`+
    `- 이건 대조군이므로 '급등 여부'와 무관하게 **구조 시그니처 유무만** 본다. 조작 단정 금지.\n`+
    `스키마대로 반환.`,
    { label: `ctrl:${seed}`, phase: 'Sample', schema: SCHEMA }
  )
))

const valid = rows.filter(Boolean).filter(r => r.is_kosdaq_smallcap && !r.surged_recently && r.classification !== "INVALID")
const sig = valid.filter(r => r.classification === "SIGNATURE").length
const unclear = valid.filter(r => r.classification === "UNCLEAR").length
const legit = valid.filter(r => r.classification === "LEGIT").length
return {
  as_of: "CONTROL-SCAN",
  drawn: rows.filter(Boolean).length,
  valid_controls: valid.length,
  signature: sig, unclear: unclear, legit: legit,
  strict_rate: valid.length ? sig / valid.length : null,
  soft_rate: valid.length ? (sig + unclear) / valid.length : null,
  rows: rows.filter(Boolean),
}
