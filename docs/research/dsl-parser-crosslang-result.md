# DSL 파서 크로스랭귀지 생성 조사 결과

**작성일**: 2026-03-29 | **담당**: Agent
**질문**: Python 파서 유지하면서 동등한 JS 파서를 만드는 가장 현실적인 방법?

---

## Executive Summary

**답**: **Lark.js가 최선**, 하지만 기존 Python 파서와의 호환성을 위해 **마이그레이션 비용 고려 필수**.
즉시 실행 가능한 방안: **수동 포팅 (직접 구현)**

---

## 1. 크로스랭귀지 파서 생성기 비교

### 1.1 유일한 선택지: Lark.js (Lark Python + Lark.js)

| 특성 | Lark |
|------|------|
| **상황** | Python 3.10+, JavaScript (Node.js) |
| **문법** | EBNF (선언형, 코드 없음) |
| **생성 방식** | 같은 `.lark` 파일 → Python & JS 파서 자동 생성 |
| **언어 지원** | Python, JavaScript, Julia |
| **알고리즘** | LALR(1) (Earley 계획 중) |
| **실행 시간** | O(n) 보장 |
| **성숙도** | 매우 높음 (GitHub 활발) |
| **한국어 키워드** | ✅ 지원 (EBNF는 유니코드 허용) |

**장점**:
- 문법 작성 후 자동으로 Python + JS 파서 생성
- Tree 구조, Transformer 클래스 모두 지원
- `import lark` (Python) vs `import lark` (JS) 동일 인터페이스

**단점**:
- 기존 Python 파서(`sv_core/parsing/parser.py` 804줄)를 **완전히 다시 작성해야 함**
- 현재 재귀 하강 방식 → LALR(1) 변경 (의미론적으로 동일하지만 구조 변경)
- 마이그레이션 테스트 비용 (~2-3일)

---

### 1.2 다른 선택지 (추천 안 함)

| 도구 | 상황 | 이유 |
|------|------|------|
| **Berp** | C#, Java, Ruby, JS, Go, Python | 주로 C# 생태. Python 지원 약함 |
| **Syntax** | JS, Python, PHP, Ruby, C#, Rust, Java | 정보 부족. 활성도 낮음 |
| **UniCC** | C, C++, Python, JavaScript 등 | LALR(1) 전용. DSL에는 과도함 |
| **Peggy** | JavaScript 전용 | Python 생성 불가 |
| **Chevrotain** | JavaScript 전용 (API 방식) | Python 생성 불가 |
| **Ohm** | JavaScript/TypeScript | Python 생성 불가 |

---

## 2. 현실적인 구현 방안 3가지

### 방안 A: Lark.js 마이그레이션 (Best Case 중장기)

```
비용: 2-3일
위험도: 중간 (기존 테스트 재검증 필요)
이득: 향후 "같은 파일로 양쪽 생성" 가능

단계:
1. grammar.md → .lark 파일로 변환
   - 재귀 하강 규칙 → LALR(1) 호환 EBNF로 재작성
   - 한국어 키워드 (매수, 매도, AND, OR, NOT) EBNF에 정의

2. lark-parser 설치 (Python) + lark (npm, JS)

3. 기존 parser.py 테스트 스위트 실행하여 동등성 검증

4. 새 ast_nodes.py 생성 (Lark Tree → 기존 Dataclass 변환)

5. evaluator.py 는 그대로 유지 (AST 형식만 같으면 됨)

6. 프론트엔드: lark JS 포팅 코드 사용
```

**체크리스트**:
- [ ] grammar.md를 EBNF로 변환 (재귀 제거, LALR(1) 호환성 확인)
- [ ] Python Lark 설치 및 테스트
- [ ] lark.js npm 패키지 설치 및 TS 타입 확인
- [ ] Round-trip 테스트: dsl → Lark Tree → 기존 AST → 평가 결과 동일성 확인
- [ ] 기존 파서 테스트 스위트 (test_parser.py, test_parser_v2.py) 모두 통과

---

### 방안 B: 수동 포팅 (가장 실용적, 즉시 가능)

```
비용: 1-2일 (이미 시작한 상태)
위험도: 낮음
이득: 기존 Python 파서 유지, 독립적인 JS 파서 완성

현황: 프론트엔드에 이미 dslParser.ts (255줄) 존재
```

**구조**:
```
┌─ sv_core/parsing/parser.py (804줄, 재귀 하강)
│   - Lexer → Tokens 변환
│   - Parser.parse() → AST (Script/Rule/Condition/Action)
│   - 의미 제약 검증 (타입, 함수 존재성 등)
│
├─ frontend/src/utils/dslParserV2.ts (89줄, 불완전)
│   - 간단한 토크나이저만 존재
│   - AST 생성 로직 없음
│
└─ 해야 할 일:
    - dslParserV2.ts → dslParser.ts와 기능 동등하도록 작성
    - 토크나이저 강화
    - 재귀 하강 파서 구현 (Python과 동일 규칙)
    - TypeScript 타입 정의
    - 테스트
```

**구체적 파일 구조**:
```
frontend/src/utils/
  ├─ dslParser.ts (기존: 간단한 조건 파서)
  ├─ dslParserV2.ts (기존: 불완전)
  ├─ dslTokens.ts (NEW: TokenType, KEYWORDS 정의)
  ├─ dslLexer.ts (NEW: Lexer 클래스)
  ├─ dslAst.ts (NEW: AST 노드 인터페이스)
  ├─ dslParserCore.ts (NEW: Parser 클래스, 핵심 로직)
  └─ __tests__/
      ├─ dslParser.test.ts (기존)
      └─ dslParserCore.test.ts (NEW)
```

---

### 방안 C: 하이브리드 (권장)

```
단기 (1주): 방안 B 진행
  - 프론트엔드 dslParserV2.ts 완성 (Python과 100% 동등)
  - 서버 추가 변경 안 함

중기 (2-3주 후): 방안 A로 마이그레이션 평가
  - Lark.js 프로토타입 만들어서 성능/안정성 테스트
  - 현재 규모에서 필요성 재평가
```

---

## 3. 우리 DSL의 특성 & 파서 생성기 호환성

| 특성 | Lark | 수동 포팅 | Peggy | Chevrotain |
|------|------|---------|-------|-----------|
| **한국어 키워드** | ✅ | ✅ | ✅ | ✅ |
| **재귀 하강** | ⚠️ LALR(1) | ✅ | ✅ | ✅ |
| **커스텀 함수 선언** | ✅ | ✅ | ✅ | ✅ |
| **중첩 괄호 / 복잡 식** | ✅ | ✅ | ✅ | ✅ |
| **내장 함수 / 필드 검증** | 부분 | ✅ | 부분 | ✅ |
| **Python 동시 생성** | ✅ | ❌ | ❌ | ❌ |
| **문법 파일 별도** | ✅ | ❌ | ✅ | ❌ |

**분석**:
- `매수:`, `매도:`, `AND`, `OR`, `NOT` 같은 한국어/영문 키워드: 모든 도구 지원
- 재귀 하강: 현재 Python 구현이 이미 재귀 하강인데, Lark는 LALR(1)로 변환 필요 → **의미론적으로 동등하지만 구조 달라짐**
- 내장 함수/필드 검증: 모두 "semantic 단계"에서 처리 (파서 생성기 아님) → 수동 구현

---

## 4. 핵심 결론

### 1안: 지금 당장 (1-2일)
**Python 파서 유지, JS 파서 수동 포팅**
- `frontend/src/utils/dslParserV2.ts` 완성
- Python `sv_core/parsing/parser.py`와 동일한 규칙을 TypeScript로 구현
- 비용 낮음, 위험도 낮음, 프론트엔드 독립성 높음

### 2안: 중기 (2-3주 후)
**Lark.js 마이그레이션 평가**
- 현재 마이그레이션 비용 > 이득 (작은 DSL이라 이득 별로)
- 향후 **큰 DSL 확장 계획 있으면** Lark.js 고려
- 프로토타입 만들어서 성능/테스트 시간 비교 후 결정

---

## 5. 기술 스택 조사 결과

### 유일한 크로스랭귀지 선택지: Lark

**Lark 특징**:
```python
# grammar.lark
start: rule+
rule: KW_BUY ":" condition
    | KW_SELL ":" condition

condition: comparison ((KW_AND | KW_OR) comparison)*

%import common.WORD
%import common.NUMBER
%import common.WS

KW_BUY: "매수"
KW_SELL: "매도"
KW_AND: "AND"

%ignore WS
```

```python
# Python 사용
from lark import Lark, Transformer, v_args

parser = Lark(grammar, start='start')
tree = parser.parse(dsl_text)
```

```javascript
// JavaScript 사용 (동일 인터페이스)
import { Lark, Transformer } from 'lark-parser';

const parser = new Lark(grammar, { start: 'start' });
const tree = parser.parse(dslText);
```

**주의**:
- `lark-parser` npm 패키지는 최신 업데이트 느림 → **GitHub 직접 사용 권장**
- Earley 알고리즘 계획 중이지만 아직 LALR(1) 전용

---

## 6. 최종 추천

**즉시 실행**: 방안 B (수동 포팅)
**타이밍**: 지금 당장
**근거**:
1. 이미 Python 파서가 완성됨 (단순 변환만)
2. Lark 마이그레이션 비용이 현재 이득보다 큼 (규모가 800줄 정도)
3. 프론트엔드에 부분 구현(`dslParserV2.ts`)이 이미 있음
4. Python 파서는 100% 신뢰할 수 있으므로 JS는 "동등성 검증만" 하면 됨

**마이그레이션 판단 기준** (6개월 후 평가):
- [ ] DSL 복잡도 대폭 증가했는가?
- [ ] 파서 규칙 변경이 빈번한가?
- [ ] 새 언어 지원 필요한가?
→ 모두 "예"면 Lark.js 마이그레이션 추진

---

## 참고 자료

- [Lark.js - Live port of Lark's standalone parser to Javascript](https://github.com/lark-parser/lark.js/)
- [Lark Parser Toolkit Documentation](https://www.lark-parser.org/)
- [Peggy - Parser Generator for JavaScript](https://peggyjs.org/)
- [Ohm - Parsing toolkit](https://ohmjs.org/)
- [Chevrotain - Parser for JavaScript](https://chevrotain.io/)
- [Comparison of parser generators - Wikipedia](https://en.wikipedia.org/wiki/Comparison_of_parser_generators)
- [GitHub - neogeny/TatSu: Parser generator for Python](https://github.com/neogeny/TatSu)
- [GitHub - DmitrySoshnikov/syntax: Language-agnostic parser generator](https://github.com/DmitrySoshnikov/syntax)
