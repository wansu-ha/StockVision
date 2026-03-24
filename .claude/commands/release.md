# /release — 로컬 서버 릴리즈

## 브랜치 정책

- 릴리즈는 **main 브랜치에서만** 실행한다.
- main이 아닌 브랜치에서 실행하면 사용자에게 되묻고 중단한다.
- 개발은 dev/기타 브랜치에서. main에는 `__version__.py` 변경만 직접 커밋한다.

## 버전 원천

`local_server/__version__.py`가 유일한 버전 원천이다.

## 실행 절차

### Phase 0: 사전 확인
1. 현재 브랜치가 main인지 확인. 아니면 중단하고 되묻기.
2. dev → main 머지가 필요하면 `git merge --no-ff dev` 실행
3. `local_server/__version__.py`에서 현재 버전 읽기
4. 마지막 태그 이후 커밋 분석: `git log v{current}..HEAD --oneline`
5. 변경 규모에 따라 버전 제안 + 릴리즈 노트 초안 작성
6. 사용자에게 보여주고 확인 받기

### Phase 1: 버전 (main에 직접 커밋)
7. `__version__.py` 수정
8. 커밋: `v{new}`
9. 태그: `v{new}`

### Phase 2: 빌드
10. PyInstaller: `pyinstaller local_server/pyinstaller.spec --noconfirm`
11. Inno Setup: `iscc /DMyAppVersion={new} local_server/installer.iss`

### Phase 3: 배포
12. push: `git push origin main --follow-tags`
13. GitHub Release: `gh release create v{new} dist/installer/StockVision-Bridge-Setup.exe --title "v{new}" --notes "{릴리즈 노트}"`

## 주의사항
- `installer.iss`에 버전을 직접 수정하지 않는다 — iscc `/D` 인자로 주입
- 각 단계 실패 시 중단하고 원인 파악
