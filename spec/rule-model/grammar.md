# StockVision DSL 정형 문법

> 작성일: 2026-03-07 | 표기법: EBNF (ISO 14977 기반)
>
> **정본**: 이 문서가 DSL 문법의 유일한 정형 명세. 파서 구현은 이 문법을 따른다.

---

## 1. 표기 규약

| 기호 | 의미 |
|------|------|
| `=` | 정의 |
| `,` | 순차 (concatenation) |
| `\|` | 택일 (alternation) |
| `{ }` | 0회 이상 반복 |
| `[ ]` | 선택 (0 또는 1회) |
| `( )` | 그룹 |
| `"..."` | 터미널 (리터럴) |
| `(*...*)`| 주석 |
| `;` | 규칙 끝 |

---

## 2. 구문 규칙 (Syntax)

### 2.1 최상위 구조

```ebnf
script = { top_stmt } ;

top_stmt = custom_func_def
         | buy_block
         | sell_block
         | comment
         | NEWLINE ;

buy_block  = "매수" , ":" , expression , TERMINATOR ;
sell_block  = "매도" , ":" , expression , TERMINATOR ;

custom_func_def = IDENT , "(" , ")" , "=" , expression , TERMINATOR ;

comment = "--" , { ANY_CHAR - NEWLINE } , TERMINATOR ;

TERMINATOR = NEWLINE | EOF ;
```

### 2.2 식 (Expressions) — 우선순위 오름차순

```ebnf
(* 레벨 1: 가장 낮은 우선순위 *)
expression = or_expr ;

(* 레벨 2 *)
or_expr = and_expr , { "OR" , and_expr } ;

(* 레벨 3 *)
and_expr = not_expr , { "AND" , not_expr } ;

(* 레벨 4 *)
not_expr = "NOT" , not_expr
         | comparison ;

(* 레벨 5: 비교 — 체이닝 금지 ([ ] = 최대 1회) *)
comparison = additive , [ comp_op , additive ] ;

(* 레벨 6 *)
additive = multiplicative , { ( "+" | "-" ) , multiplicative } ;

(* 레벨 7 *)
multiplicative = unary , { ( "*" | "/" ) , unary } ;

(* 레벨 8: 단항 음수 *)
unary = "-" , unary
      | primary ;

(* 레벨 9: 가장 높은 우선순위 *)
primary = NUMBER
        | BOOL_LIT
        | IDENT , "(" , [ arg_list ] , ")"    (* 함수 호출 *)
        | IDENT                                (* 필드 참조 *)
        | "(" , expression , ")" ;             (* 괄호 그룹 *)

arg_list = expression , { "," , expression } ;

comp_op = ">" | ">=" | "<" | "<=" | "==" | "!=" ;
```

### 2.3 우선순위 요약

| 레벨 | 연산 | 결합 방향 | 예시 |
|------|------|----------|------|
| 1 (최저) | `OR` | 좌→우 | `A OR B OR C` |
| 2 | `AND` | 좌→우 | `A AND B AND C` |
| 3 | `NOT` | 우→좌 (단항) | `NOT A` |
| 4 | 비교 | 없음 (체이닝 금지) | `A >= B` |
| 5 | `+`, `-` | 좌→우 | `A + B - C` |
| 6 | `*`, `/` | 좌→우 | `A * B / C` |
| 7 | 단항 `-` | 우→좌 | `-A` |
| 8 (최고) | 호출, 괄호 | — | `RSI(14)`, `(A)` |

---

## 3. 어휘 규칙 (Lexical)

```ebnf
(* 식별자/키워드 *)
IDENT = ident_start , { ident_cont } ;
ident_start = UNICODE_LETTER | "_" ;
ident_cont  = UNICODE_LETTER | DIGIT | "_" ;

(* 키워드 — IDENT를 최장 일치로 추출한 뒤 아래 목록과 대조.
   일치하면 해당 키워드 토큰, 불일치면 IDENT 토큰으로 발행.
   예: "매수가" → IDENT, "매수" + ":" → KEYWORD_BUY + COLON *)
KEYWORD = "매수" | "매도" | "AND" | "OR" | "NOT" ;

(* 리터럴 *)
NUMBER = DIGIT , { DIGIT } , [ "." , DIGIT , { DIGIT } ] ;
BOOL_LIT = "true" | "false" ;
(* "true"/"false"는 BOOL_LIT 토큰으로 발행. 예약어이므로 IDENT로 사용 불가 *)

(* 구두점 *)
LPAREN  = "(" ;   RPAREN  = ")" ;
COMMA   = "," ;   COLON   = ":" ;
ASSIGN  = "=" ;   (* 커스텀 함수 정의 *)

(* 비교 연산자 — 최장 일치: ">=" > ">" *)
GE = ">=" ;  LE = "<=" ;  EQ = "==" ;  NE = "!=" ;
GT = ">" ;   LT = "<" ;

(* 산술 연산자 *)
PLUS = "+" ;  MINUS = "-" ;  STAR = "*" ;  SLASH = "/" ;

(* 주석 *)
COMMENT_START = "--" ;  (* 행 끝까지 무시 *)

(* 줄바꿈/종료 *)
NEWLINE = "\n" | "\r\n" ;
EOF = ? 입력 끝 ? ;

(* 공백 — 토큰 구분자, 무시 (NEWLINE 제외) *)
WS = " " | "\t" ;

(* 유니코드 문자: 한글(가-힣, ㄱ-ㅎ, ㅏ-ㅣ), 영문(a-z, A-Z) 등 *)
UNICODE_LETTER = ? Unicode category L ? ;
DIGIT = "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" ;
```

### 3.1 토큰화 규칙

1. **최장 일치**: `>=` > `>`, `==` > `=`, `매수가` > `매수` — 항상 가장 긴 토큰 우선
2. **키워드 판별**: IDENT를 최장 일치로 추출 → 키워드 목록과 대조 → 일치하면 키워드 토큰, 아니면 IDENT
3. **`true`/`false`**: 키워드 판별과 동일 과정, 단 BOOL_LIT 토큰으로 발행
4. **`--`**: 주석 시작 — 행 끝(`NEWLINE` 또는 `EOF`)까지 무시
5. **공백/탭**: 토큰 구분자, 토큰으로 발행하지 않음 (`NEWLINE` 제외)

---

## 4. 의미 제약 (Semantic Constraints)

EBNF로 표현할 수 없는 규칙. 파서 또는 타입 체커가 강제한다.

### 4.1 구조 제약

| 규칙 | 위반 시 에러 |
|------|------------|
| `매수:` 블록 정확히 1회 | `매수: 블록이 없습니다` / `매수: 블록이 중복됩니다` |
| `매도:` 블록 정확히 1회 | `매도: 블록이 없습니다` / `매도: 블록이 중복됩니다` |
| 커스텀 함수 후방 참조 금지 | `'이름'은 아직 정의되지 않았습니다` |
| 커스텀 함수 재귀 금지 | `'이름'이 자기 자신을 참조합니다` |
| 커스텀 함수 이름 중복 금지 | `'이름'이 이미 정의되었습니다` |
| 커스텀 함수 호출 시 인자 0개 | `'이름'은 인자를 받지 않습니다` |
| 비교 체이닝 금지 (`a > b > c`) | `비교 연산을 연속으로 사용할 수 없습니다` |

### 4.2 타입 제약

| 위치 | 허용 타입 | 위반 예시 |
|------|----------|----------|
| `매수:` / `매도:` 블록 결과 | boolean | `매수: RSI(14)` (숫자) |
| `AND`, `OR` 피연산자 | boolean | `3 AND true` |
| `NOT` 피연산자 | boolean | `NOT 50000` |
| 비교 (`>`, `<` 등) 양쪽 | 숫자 | `true > 30` |
| 산술 (`+`, `-`, `*`, `/`) 양쪽 | 숫자 | `true + 1` |
| 함수 인자 | 함수별 정의 참조 | `RSI("abc")` |

### 4.3 식별자 해석 순서

함수 호출/필드 참조에서 식별자를 만났을 때:

1. **커스텀 함수** (스크립트 내 선언) → 내장 이름과 동일해도 커스텀 우선 (오버라이드, spec §3)
2. **내장 패턴 함수** (`골든크로스`, `RSI과매도` 등, spec §3)
3. **내장 함수** (`RSI`, `MA`, `상향돌파`, `평균거래량` 등)
4. **내장 필드** (`현재가`, `거래량`, `수익률`, `보유수량` 등)
5. **미해석** → `'이름'은 정의되지 않은 식별자입니다` 에러

### 4.4 런타임 규칙

| 상황 | 동작 |
|------|------|
| null 발생 (결측치, 데이터 부족) | 해당 `매수:`/`매도:` 블록 전체 = false |
| `수익률` 미보유 시 | null (미보유 상태에서 수익률은 무의미 → null 전파) |
| `보유수량` 미보유 시 | 0 |
| null + AND/OR | 단락 평가 없음. 피연산자 중 하나라도 null → 블록 전체 = false |
| 0으로 나누기 | null → 블록 전체 = false |
| `상향돌파(A,B)` | 직전 평가에서 A < B 이고 현재 평가에서 A >= B 일 때 true |
| `하향돌파(A,B)` | 직전 평가에서 A > B 이고 현재 평가에서 A <= B 일 때 true |
| 상향돌파/하향돌파 첫 평가 (직전 값 없음) | false |
| `--`로 시작하는 토큰 | 항상 주석. 이중 부정은 `- -5` 또는 `-(-5)` 사용 |

---

## 5. 파싱 예시

### 입력

```
-- 골든크로스 + 과매도 진입
과매도() = RSI(14) <= 30
거래량확인() = 거래량 > 평균거래량(20) * 2

매수: 골든크로스() AND 과매도() AND 거래량확인()
매도: RSI(14) >= 70 OR 수익률 >= 3 OR 수익률 <= -5
```

### AST (개념적 구조)

```
Script
├── CustomFuncDef "과매도"
│   └── Comparison(<=)
│       ├── FuncCall "RSI" [NumberLit 14]
│       └── NumberLit 30
├── CustomFuncDef "거래량확인"
│   └── Comparison(>)
│       ├── FieldRef "거래량"
│       └── BinOp(*)
│           ├── FuncCall "평균거래량" [NumberLit 20]
│           └── NumberLit 2
├── BuyBlock
│   └── BinOp(AND)
│       ├── BinOp(AND)
│       │   ├── FuncCall "골든크로스" []
│       │   └── FuncCall "과매도" []
│       └── FuncCall "거래량확인" []
└── SellBlock
    └── BinOp(OR)
        ├── BinOp(OR)
        │   ├── Comparison(>=)
        │   │   ├── FuncCall "RSI" [NumberLit 14]
        │   │   └── NumberLit 70
        │   └── Comparison(>=)
        │       ├── FieldRef "수익률"
        │       └── NumberLit 3
        └── Comparison(<=)
            ├── FieldRef "수익률"
            └── UnaryOp(-) NumberLit 5
```

### 고급 예시

```
-- 볼린저밴드 역추세 + MACD 확인 전략
저가권() = 현재가 <= 볼린저_하단(20) * 1.02
거래량폭발() = 거래량 >= 평균거래량(20) * 3
추세전환() = MACD골든크로스() AND NOT 데드크로스()
적정가격() = 현재가 >= MA(5) - (MA(20) - MA(5)) / 2

매수: 저가권() AND 거래량폭발() AND (추세전환() OR 상향돌파(RSI(14), 30))
매도: 볼린저상단돌파() OR 수익률 >= 5 OR 수익률 <= -3
```

사용된 문법 기능: 커스텀 함수 4개, 내장 패턴 함수 (`MACD골든크로스`, `데드크로스`, `볼린저상단돌파`), `NOT`, 중첩 괄호 산술식, `상향돌파` 내 함수 호출 인자, `OR`/`AND` 혼합 + 괄호 우선순위.

---

## 참고

- `spec/rule-model/spec.md` §2–§3: DSL 개요, 내장 패턴 함수
- `docs/research/rule-dsl-design.md` §3: 설계 배경, 미결 사항

---

**마지막 갱신**: 2026-03-07
