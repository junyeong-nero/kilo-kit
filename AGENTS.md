# 작업 원칙

- 요청받은 작업에 집중하고, 변경 후 검증한 사실만 보고한다.
- 저장소 이름은 `kilo-kit`다. 사용자의 명시적 요청 없이 변경하지 않는다.
- 이 저장소는 Kilo CLI(`kilo.exe`), 빌드센터 MCP·인코딩 보존 MCP·Word MCP(word-mcp-live, 동봉 Python)·Windows-MCP, rg·fd만 배포한다. 인코딩 보존 MCP(`mcp\encoding\`)는 표준 라이브러리와 빌드센터와 같은 mcp 1만 쓰며, 내장 edit·write는 삭제하지 않고 승인 대상으로 둔다. Word MCP 패키지는 mcp 2가 필요해 `runtime\word-mcp\`에 따로 두고, 빌드센터의 `config/redis/requirements.lock`과 합치지 않는다. Windows-MCP는 Python 3.13 호환 버전 0.8.5를 `config/windows/requirements.lock`에 고정하고 `runtime\windows-mcp\`에 분리한다. UI 테스트용 도구만 stdio로 제공하고 텔레메트리·업데이트 확인을 끈다. 캡처·조작은 모두 승인 대상이며 실제 Windows UI 검증 없이 동작 성공으로 보고하지 않는다. 확장·Edge MCP·언어 서버(LSP)·SVN·Redis 실행 파일은 다시 넣지 않는다.
- `grep`이나 `rg`로 검색할 때는 기본적으로 모든 깊이의 점(`.`)으로 시작하는 디렉터리를 제외한다. `grep` 재귀 검색에는 `--exclude-dir='.*'`를 사용하고, `rg`에서는 기본 숨김 경로 제외 동작을 유지하며 `--hidden`이나 `-uu` 등으로 해제하지 않는다. 숨김 디렉터리 검색은 사용자가 명시적으로 요청한 경우에만 수행한다.

## 반드시 지킬 배포 조건

**사용자는 GitHub에서 완성된 배포 ZIP 하나를 내려받아 폐쇄망 Windows 개발 PC로 옮기고, 압축을 풀어 `setup.ps1`에서 사내 모델 프로바이더(API 주소·키)만 등록하면 `kilo`를 실행할 수 있어야 한다.**

- GitHub Actions가 실행 파일과 의존성을 준비하고 완성된 ZIP을 만든다. 배포 ZIP에는 Kilo CLI(`bin\kilo\` 전체: `kilo.exe`, tree-sitter WASM, console 리소스), rg·fd(`bin\`), 빌드센터 MCP 코드, 인코딩 보존 MCP 코드(`mcp\encoding\`), Word MCP 런처(`mcp\word\`)와 패키지(`runtime\word-mcp\`), Windows-MCP 런처(`mcp\windows\`)와 패키지(`runtime\windows-mcp\`), MCP용 Python 런타임과 패키지, 설정 템플릿과 라이선스를 포함한다.
- 대상 PC에서 인터넷 다운로드, npm/pip 설치, Node.js/Python 설치, 수동 실행 파일 수집, 배포물 빌드를 요구하지 않는다. Kilo가 실행 중에 외부로 나가는 기능(models.dev 목록, 자동 업데이트, 텔레메트리, LSP·ripgrep 다운로드, 공유)은 `setup.ps1`의 시스템 변수와 설정으로 끈다.
- 사용자 절차는 ZIP 다운로드 → 폐쇄망 반입 → 압축 해제 → `setup.ps1` 1회 실행(사내 API 주소·키 입력 또는 `config\models.json`) → 어느 폴더에서나 `kilo` 실행으로 유지한다. 사내 모델 API 연결은 필요하다.
- `setup.ps1`이 사내 API의 `/models`에서 모델을 찾아 `config\models.json`을 완성하고, Kilo 설정을 `%USERPROFILE%\.config\kilo\`(Kilo 표준 전역 설정 위치)에 설치한다. 같은 이름의 기존 파일은 `.bak`으로 백업한 뒤 바꾼다. 사용자 변경용 `kilo.jsonc`는 덮어쓰지 않는다.
- README에서 바로 받을 완성 ZIP의 위치를 안내한다. GitHub의 소스 코드 Download ZIP을 실행 가능한 배포본으로 안내하지 않는다.
- `scripts/`에는 `setup.ps1`만 둔다. 이 파일이 필수 파일 확인, 프로바이더 등록·모델 탐색, Kilo 설정 설치와 1회 설정(시스템 PATH·변수)을 처리한다. 루트 `setup.ps1`은 이 파일을 호출하는 바로가기다. 사용자 환경 변수는 로그인 때 초기화되는 PC가 있으므로 Kilo 실행에 필요한 PATH·변수(API 키 포함)는 시스템 변수에 둔다.
- 사용자용 build-offline, 환경 설정, 실행, 검증 스크립트를 다시 분리해서 추가하지 않는다. 다운로드·패키징 자동화는 GitHub Actions에서 처리한다.
- 단순화를 이유로 자동 배포를 제거하거나 실행 파일 준비 책임을 사용자에게 넘기지 않는다.
- 테스트는 최소로 둔다. 배포 통합용 `.github/` 작업은 승인 범위다. CI는 키 처리·패키징 회귀 테스트, ZIP 재배치·실제 셋업·Kilo 시작을 확인한다. 사내 API 추론·UI 실기는 별도이며 CI 미실행 상태를 성공으로 보고하지 않는다.
- OpenCode 전환은 철회했다. 기존 OpenCode 설정·DB·환경 변수를 삭제하거나 이력을 Kilo로 자동 이동하지 않는다. OpenCode 전용 인코딩 custom tools·npm 의존성·DB 분리 진입점은 배포하지 않는다.
- `apiKeyEnv`에 잘못 넣은 `sk-...` 키는 시스템 등록 성공 후 변수 이름으로 정정한다. 원문 키를 오류·JSON 백업에 복제하지 않는다. 패키징은 라이브러리의 실제 `cache` 코드 폴더를 보존하고 `config/redis/cache`만 제외한다.
- 배포 ZIP에 실제 API 키, `config/models.json`, 빌드센터 실제 매핑(`server_IP_mappings.json`, `owners.json`), 세션·캐시를 포함하지 않는다.
