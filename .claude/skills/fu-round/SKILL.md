---
name: fu-round
description: 작전주 코호트 F/U 라운드를 재현 가능하게 실행한다. 사용자가 "F/U 돌려줘", "/fu-round", "팔로업 라운드"를 요청하면 이 절차를 그대로 따른다. 판단은 워크플로우(opus 고정)가 하고, 드라이버 모델은 아래 명령을 순서대로 실행만 한다 — 모델이 소넷이어도 결과가 동일해야 한다.
---

# F/U 라운드 하네스 (재현 절차)

⚠️ **드라이버 규약**: 아래 단계를 그대로 실행한다. 프롬프트를 새로 쓰거나, 대상을 임의 추가/제외하거나, 로그 포맷을 손으로 쓰지 않는다. 판단·판정·포맷은 전부 하네스(워크플로우 스크립트 + 후처리기)가 수행한다.

## 절차

1. **args 생성** (레지스트리에서 active 대상만):
   ```bash
   python3 validation/harness/build_args.py
   ```
   stdout의 JSON 배열을 그대로 다음 단계의 `args`로 사용한다. active 0건이면 사용자에게 보고하고 중단.

2. **워크플로우 실행** — Workflow 도구를 다음 인자로 호출:
   - `scriptPath`: `<repo>/validation/harness/fu_workflow.js` (절대경로)
   - `args`: 1단계 stdout JSON (그대로, 수정 금지)
   - 완료 알림을 기다린다(백그라운드). 실패 시 오류를 보고하고 임의 재작성하지 않는다(스크립트 수정이 필요하면 사용자에게 먼저 보고).

3. **후처리(결정론적)** — 완료 알림의 output-file 경로로:
   ```bash
   python3 validation/harness/postprocess_fu.py <output-file>
   ```
   이 스크립트가 라운드 번호 산정, `validation/daily_followup.md` 블록 삽입, `cohort_registry.json` 상태 전이(VOID/MISS/EARLY→closed, preramp HIT→collapse-watch)까지 전부 수행한다. **로그를 손으로 편집하지 않는다.**

4. **커밋·푸시** (고정 형식):
   ```bash
   git add validation/daily_followup.md validation/harness/cohort_registry.json
   git commit -m "validation: F/U Round N — <판정 분포 요약>"   # N·분포는 3단계 stdout에서
   git push -u origin <현재 브랜치>
   ```

5. **사용자 보고**: 3단계 stdout(판정 분포·전이·잔여 active)과 HIT/VOID/MISS 건의 학습노트 요지만 전달한다. 과장·재해석 금지.

## 불변 규칙 (하네스가 강제하지만 드라이버도 준수)
- 조작·작전 단정 금지(모니터링 후보), 매수/매도 권유 금지, 교육·연구용.
- 과거 라운드 블록 수정 금지(as-of 동결). 코호트 변경은 `cohort_registry.json` 편집+커밋으로만.
- 신규 대상 추가는 이 스킬의 범위 밖 — 별도 스캔 파이프라인(사용자 요청 시)으로만.
