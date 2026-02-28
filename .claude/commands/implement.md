# /implement — 코드 구현

feature-name: $ARGUMENTS

`$ARGUMENTS`가 비어 있으면 대화 맥락과 프로젝트 상태를 분석하여 feature-name을 제안하고, 사용자 확인 후 진행한다.

## 실행 절차

1. **plan 확인**: `spec/{feature-name}/plan.md` 존재 여부 확인.
   - 없으면 경고: "plan이 없습니다. /plan $ARGUMENTS를 먼저 실행하세요." → 사용자 확인 후 계속 또는 중단.

2. **브랜치 확인**: 현재 브랜치명에 `$ARGUMENTS`가 포함되어 있으면 그대로 사용. 아니면 `feat/$ARGUMENTS` 브랜치로 체크아웃 (없으면 생성).

3. **코드 구현**: plan.md의 구현 순서에 따라 단계별로 구현한다.
   - 각 단계 완료 후 plan의 검증 방법으로 확인
   - 구현 중 spec/plan에 변경이 필요하면 함께 수정

4. **AI 자체 검증 루프**:
   - 빌드 실행 (`npm run build` / Python 테스트)
   - 브라우저 확인 (Playwright): 화면 렌더링, 기능 동작, 콘솔 에러 체크
   - 스크린샷 촬영 → `spec/$ARGUMENTS/reports/screenshots/`에 저장

5. **리포트 작성**: `spec/$ARGUMENTS/reports/{YYMMDD}-report.md` 생성.
   - 검증 결과 요약
   - 발견된 이슈 목록
   - 스크린샷 첨부 (`![설명](screenshots/파일명.png)`)
   - 다음 이터레이션 필요 여부

6. **커밋**: `git diff` 확인 후 스테이징.
   - 커밋 메시지: `feat: $ARGUMENTS 구현` (spec/plan 수정 + 리포트 포함)

7. **이터레이션**: 이슈가 있으면 반복.
   - 검증 → 리포트 → spec/plan 수정 → 구현 수정 → 커밋
   - 각 이터레이션마다 새 리포트 파일 생성

8. **머지 금지**: 구현 완료 후 사용자에게 보고. 머지는 사용자 허가 후에만 `--no-ff`로 실행. 브랜치는 삭제하지 않는다.

## 규칙

- plan 없이 구현하지 말 것 (경고 후 사용자 판단에 맡김)
- 커밋 전 반드시 `git diff` 확인
- 리포트에는 성공/실패 모두 기록
- 머지, 브랜치 삭제 금지 — 사용자 허가 필요
