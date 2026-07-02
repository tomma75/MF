export const meta = {
  name: 'opstock-daily-fu',
  description: 'F/U 라운드 — 코호트 레지스트리 active 대상 재조회 → 판정 → 학습노트 (모델 고정 하네스)',
  phases: [
    { title: 'Recheck', detail: '대상별 최신 상태 웹 재조회 (opus 고정)' },
    { title: 'Adjudicate', detail: '판정 + 학습노트 종합 (opus 고정)' },
  ],
}

// ⚠️ 하네스 규약: 이 스크립트는 validation/harness/의 정본이다.
// - agent model은 'opus'로 고정 — 드라이버(메인 루프) 모델이 무엇이든 동일 품질.
// - 프롬프트/판정코드/스키마 변경은 이 파일 수정으로만(재현성). 변경 시 커밋 필수.
// - args = build_args.py 출력(JSON 배열). 후처리는 postprocess_fu.py가 결정론적으로 수행.

const CTX = `프로젝트: 작전주 선행 시그널 연구(방어적·교육용). F/U(follow-up) = 사전 예측/셋업 대비 실제 대조.
⚠️ 규칙: 조작·작전 단정 금지(모니터링 후보). 매수/보유/매도 권유 절대 금지. 공개 사실만·출처 URL 필수. 정직성: 지어내지 말 것, 확인 불가는 NO_DATA/unresolved로.
판정 코드(정확히 이 중 하나로 시작할 것): HIT / MISS / EARLY / VOID / PENDING / NO_DATA
- HIT: 예측 트리거로 예측창 내 발생(collapse=붕괴/디스트리뷰션, preramp=게이트B 발화 or 촉매 점화, collapse-watch=디스트리뷰션 개시)
- MISS: 창 경과·미발생 또는 예측과 반대
- EARLY: 창 이전에 이미 발생 완료(사후 확인)
- VOID: 반증조건(falsify) 충족 → 예측 무효
- PENDING: 창 이전·촉매 미도래, 미발생
- NO_DATA: 실시간 확인 불가로 판정 불능
층 정의: collapse=붕괴/디스트리뷰션 관찰, preramp=급등 발화 관찰, collapse-watch=발화 완료 후 오버행 출회·디스트리뷰션 관찰.`

const RC = { type:'object', properties:{
  name:{type:'string'}, symbol:{type:'string'},
  current_status:{type:'string'},
  change_since_baseline:{type:'string'},
  trigger_fired:{type:'string'},
  falsifier_hit:{type:'string'},
  verdict:{type:'string'},
  learning_note:{type:'string'},
  sources:{type:'array', items:{type:'string'}} },
  required:['name','current_status','verdict'] }

const SYN = { type:'object', properties:{
  rows:{type:'array', items:{type:'object', properties:{
    name:{type:'string'}, layer:{type:'string'}, verdict:{type:'string'}, one_line:{type:'string'} },
    required:['name','verdict','one_line'] }},
  hits:{type:'array', items:{type:'string'}},
  misses_or_voids:{type:'array', items:{type:'string'}},
  learning:{type:'array', items:{type:'string'}},
  next_priorities:{type:'array', items:{type:'string'}},
  metrics_note:{type:'string'} },
  required:['rows'] }

const cohort = (typeof args === 'string' ? JSON.parse(args) : args)
if (!Array.isArray(cohort) || cohort.length === 0) { throw new Error('args must be a non-empty JSON array from build_args.py') }

phase('Recheck')
const rc = (await parallel(cohort.map(c => () =>
  agent(`${CTX}\n\n대상: ${c.name} (${c.symbol}, ${c.mkt}) — 층=${c.layer}\n예측/셋업: window=${c.window} · trigger=${c.trigger}\n반증조건: ${c.falsify}\n\nWebSearch(필요시 WebFetch)를 ToolSearch로 불러와 **오늘 기준 최신 상태**를 조사하라: 현재가·최근 등락, 시장경보/거래정지 단계 변화, 신규 공시(CB 전환·유증 납입·최대주주 변경·상폐심사), (US)정지 해제·상폐 진행, 수사·소송 보도.\n산출: current_status, change_since_baseline(직전 라운드 대비; 없으면 '변동 없음'), trigger_fired(yes/no/부분+근거), falsifier_hit(yes/no+근거), verdict(판정 코드로 시작), learning_note(HIT/MISS/VOID/EARLY면 근거·교훈, PENDING이면 다음 관찰 포인트), sources(URL). 확인 불가 항목은 정직하게 NO_DATA.`,
    { label:`rc:${(c.name||'').slice(0,12)}`, phase:'Recheck', model:'opus', schema:RC })
    .then(v => v ? {...v, layer:c.layer} : null)
))).filter(Boolean)

phase('Adjudicate')
const syn = await agent(
  `${CTX}\n\n재조회 결과:\n${JSON.stringify(rc)}\n\n종합: rows(각 name/layer/verdict(코드만)/one_line), hits(HIT·EARLY 목록+근거 요약), misses_or_voids(MISS·VOID+이유), learning(이번 라운드 교훈 — 트리거 모델 강화/약화점, 없으면 빈 배열), next_priorities(다음 라운드 관찰 우선순위 3~6개), metrics_note(판정 분포·NO_DATA 비율 한 단락). 한국어.`,
  { label:'adjudicate', phase:'Adjudicate', model:'opus', effort:'high', schema:SYN })

return { rc, syn }
