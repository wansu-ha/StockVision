# StockVision 문서 인덱스

`docs/` 안에 문서가 빠르게 늘어나고 있어서, 이 파일을 문서 진입점으로 사용합니다.
무엇을 먼저 읽어야 하는지, 어떤 문서가 최신 기준인지, 어떤 문서가 대화/검토 기록인지 한눈에 찾을 수 있게 정리했습니다.

최종 업데이트: 2026-03-11

## 먼저 읽으면 좋은 문서

프로젝트 전체 그림을 빠르게 잡고 싶다면 아래 순서로 읽으면 됩니다.

1. [project-blueprint.md](./project-blueprint.md) - 프로젝트가 최종적으로 어떤 모습이 되려는지 큰 그림
2. [architecture.md](./architecture.md) - 현재 기준 아키텍처
3. [roadmap.md](./roadmap.md) - 단계별 진행 방향
4. [development-plan-v2.md](./development-plan-v2.md) - Phase 3 전환 시점 7 Unit 구현 계획 (참고용)
5. [product/product-direction-log.md](./product/product-direction-log.md) - 최근 제품 판단과 대화성 의사결정 로그

## 문서 지도

### 핵심 문서

- [project-blueprint.md](./project-blueprint.md) - 프로젝트 완성 상태를 상정한 전체 청사진
- [architecture.md](./architecture.md) - 현재 채택한 시스템 구조와 역할 분리
- [architecture-diagram.md](./architecture-diagram.md) - 아키텍처를 도식 중심으로 보는 문서
- [roadmap.md](./roadmap.md) - 단계별 로드맵
- [development-plan-v2.md](./development-plan-v2.md) - Phase 3 전환 시점 7 Unit 구현 계획
- [future-improvements.md](./future-improvements.md) - 후속 개선 아이템 모음
- [log-system-improvements.md](./log-system-improvements.md) - 로그 시스템 개선 기록
- [legal.md](./legal.md) - 법적 근거 문서의 상위 요약

### 방향성과 대화 로그

대화에서 나온 판단, 제품 방향, 아이디어 메모를 모아 둔 영역입니다.

- [ideas.md](./ideas.md) - 초기 아이디어 노트
- [v2-ideas.md](./v2-ideas.md) - v2 확장 아이디어 모음
- [product/product-direction-log.md](./product/product-direction-log.md) - 제품 방향과 의사결정 로그
- [product/frontend-ux-priority-prd-2026-03-10.md](./product/frontend-ux-priority-prd-2026-03-10.md) - 프론트 UX 개편 우선순위 PRD
- [positioning/dual-audience-strategy.md](./positioning/dual-audience-strategy.md) - 초보/전문가 동시 대응 전략
- [positioning/key-storage-trust.md](./positioning/key-storage-trust.md) - 키 저장 신뢰 설계

### 제품

제품 기능 구조, 권한, 과금, 시스템 역할 정의 관련 문서입니다.

- [product/assistant-copilot-engine-structure.md](./product/assistant-copilot-engine-structure.md) - Assistant, Copilot, Trader 계층 구조
- [product/assistant-system-prompt-draft.md](./product/assistant-system-prompt-draft.md) - 비서 시스템 프롬프트 초안
- [product/free-pro-boundary.md](./product/free-pro-boundary.md) - 요금제 경계 정의
- [product/llm-permission-policy.md](./product/llm-permission-policy.md) - LLM 권한 정책
- [product/pricing-plan-draft.md](./product/pricing-plan-draft.md) - 과금 플랜 초안
- [product/remote-permission-model.md](./product/remote-permission-model.md) - 원격 권한 모델 표
- [product/system-trader-definition.md](./product/system-trader-definition.md) - System Trader 정의
- [product/system-trader-state-model.md](./product/system-trader-state-model.md) - System Trader 상태 모델
- [product/system-trader-benchmark.md](./product/system-trader-benchmark.md) - System Trader 벤치마크 조사

### 리서치

리서치와 검토 문서입니다. 성격이 달라서 몇 가지 묶음으로 나눠 봅니다.

검토와 정합성 리뷰:

- [research/cross-review-summary.md](./research/cross-review-summary.md) - 교차 리뷰 종합 보고서
- [research/cross-review-api-contract.md](./research/cross-review-api-contract.md) - API 계약 정합성 리뷰
- [research/cross-review-sv-core.md](./research/cross-review-sv-core.md) - `sv_core` 정합성 리뷰
- [research/cross-review-security-quality.md](./research/cross-review-security-quality.md) - 보안/품질 교차 리뷰
- [research/cross-review-legal.md](./research/cross-review-legal.md) - 법률 문서와 아키텍처 일치성 검토
- [research/spec-review-result.md](./research/spec-review-result.md) - 전체 스펙 검토 결과
- [research/code-analysis-result.md](./research/code-analysis-result.md) - 코드 분석 결과
- [research/security-audit-report.md](./research/security-audit-report.md) - 보안 점검 보고서
- [research/p0-re-review.md](./research/p0-re-review.md) - P0 재검토 메모

브로커/API/법률 리서치:

- [research/kiwoom-rest-api-spec.md](./research/kiwoom-rest-api-spec.md) - 키움 REST API 리서치 명세
- [research/pykiwoom-analysis.md](./research/pykiwoom-analysis.md) - `pykiwoom` API 분석
- [research/kiwoom-legal-analysis.md](./research/kiwoom-legal-analysis.md) - 키움 관련 법적/약관 분석
- [research/legal-data-review.md](./research/legal-data-review.md) - 데이터 제공 관련 법적 검토 논의

제품/시장/기획 리서치:

- [research/ai-trading-platforms-comparison.md](./research/ai-trading-platforms-comparison.md) - AI 자동매매 서비스 비교
- [research/trading-platform-benchmark.md](./research/trading-platform-benchmark.md) - 자동매매 플랫폼 벤치마크
- [research/frontend-uxui-benchmark-mapping-2026-03-10.md](./research/frontend-uxui-benchmark-mapping-2026-03-10.md) - UX/UI 벤치마크 매핑
- [research/llm-feasibility-analysis.md](./research/llm-feasibility-analysis.md) - Custom LLM 도입 타당성 분석
- [research/rule-dsl-design.md](./research/rule-dsl-design.md) - 규칙 DSL 설계 리서치

데이터 정책과 자산:

- [research/collectible-data-inventory.md](./research/collectible-data-inventory.md) - 수집 가능 데이터 인벤토리
- [research/source-of-truth-policy.md](./research/source-of-truth-policy.md) - 데이터 정본 우선순위 정책

### 법률

법률/약관 문서는 별도 하위 디렉터리에 정리되어 있습니다.

- [legal/README.md](./legal/README.md) - 법률 문서 전체 안내
- [legal/terms-of-service.md](./legal/terms-of-service.md) - 이용약관
- [legal/privacy-policy.md](./legal/privacy-policy.md) - 개인정보처리방침
- [legal/disclaimer.md](./legal/disclaimer.md) - 투자 위험 고지
- [legal/broker-compliance.md](./legal/broker-compliance.md) - 증권사 약관 준수 확인

### 오픈소스

오픈소스 공개 범위, 운영 방식, 저장소 분리 전략을 다루는 문서입니다.

- [open-source/OPEN_SOURCE_SCOPE.md](./open-source/OPEN_SOURCE_SCOPE.md) - 공개 범위 초안
- [open-source/oss-license-strategy.md](./open-source/oss-license-strategy.md) - 라이선스 전략
- [open-source/repo-split-plan.md](./open-source/repo-split-plan.md) - 저장소 분리 계획
- [open-source/repo-mapping-table.md](./open-source/repo-mapping-table.md) - 저장소 매핑 표
- [open-source/phase-1-migration-checklist.md](./open-source/phase-1-migration-checklist.md) - 1단계 이동 체크리스트
- [open-source/github-organization-structure.md](./open-source/github-organization-structure.md) - GitHub 조직 구조 제안
- [open-source/CONTRIBUTING.md](./open-source/CONTRIBUTING.md) - 기여 가이드 초안
- [open-source/SECURITY.md](./open-source/SECURITY.md) - 보안 정책 초안
- [open-source/SUPPORT.md](./open-source/SUPPORT.md) - 지원 정책 초안
- [open-source/TRADEMARKS.md](./open-source/TRADEMARKS.md) - 상표/브랜드 정책 초안
- [open-source/solo-maintainer-rules.md](./open-source/solo-maintainer-rules.md) - 1인 유지보수 운영 규칙
- [open-source/README-license-section.md](./open-source/README-license-section.md) - README 라이선스 섹션 초안
- [open-source/LICENSE](./open-source/LICENSE) - 오픈소스 라이선스 초안 파일

## 지금 기준으로 보면 좋은 문서 vs 전환/과거 참고 문서

현재 기준 문서:

- [architecture.md](./architecture.md)
- [roadmap.md](./roadmap.md)
- [project-blueprint.md](./project-blueprint.md)
- [product/product-direction-log.md](./product/product-direction-log.md)

전환/과거 맥락 확인용 문서:

- [architecture-phase3.md](./architecture-phase3.md) - 제목상 `SUPERSEDED` 상태
- [development-plan-v2.md](./development-plan-v2.md) - Phase 3 시점 7 Unit 기술 전환 계획
- [development-plan.md](./development-plan.md) - 초기 상세 개발 계획
- [integrated-development-plan.md](./integrated-development-plan.md) - 통합 개발 계획의 이전 버전

## 이 문서를 어떻게 유지할지

앞으로 문서가 더 늘어날 때는 아래 규칙으로 관리하면 인덱스가 오래 버팁니다.

1. 새 문서를 만들면 이 파일에 한 줄 설명을 바로 추가합니다.
2. 대화나 검토를 바탕으로 만든 문서는 가능하면 제목이나 파일명에 날짜를 남깁니다.
3. 최신 기준 문서가 바뀌면 "현재 기준 문서" 목록을 먼저 갱신합니다.
4. 대체된 문서는 삭제하기보다 `superseded`, `legacy`, `draft` 같은 상태를 제목이나 상단에 명시합니다.
5. 구현 명세는 가능하면 `docs/`보다 `spec/`에 두고, 이 인덱스에서는 진입점만 연결합니다.

## 관련 폴더

- [`spec/`](../spec/) - 실제 구현 명세
- [`changeLog/`](../changeLog/) - 변경 이력 자산


