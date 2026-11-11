# 작업 원칙

- 요청받은 작업에 집중하고, 변경 후 검증한 사실만 보고한다.
- 배포 이름은 `opencode-kit`다. 로컬 폴더와 GitHub 저장소는 아직 `kilo-kit`이며 별도 승인 없이 이동·원격 리네임·커밋·푸시하지 않는다.
- OpenCode CLI, 인코딩 보존 custom tools, 빌드센터 MCP·Word MCP·Windows-MCP, rg·fd를 배포한다. VS Code 확장·Edge MCP·LSP·SVN·Redis 실행 파일은 포함하지 않는다.
- Word MCP(mcp 2)는 `runtime/word-mcp/`, Windows-MCP 0.8.5(Python 3.13 호환)는 `runtime/windows-mcp/`로 의존성을 분리한다. 기존 빌드센터 패키지와 합치지 않는다.
- `grep`·`rg` 검색은 기본적으로 모든 깊이의 숨김 디렉터리를 제외한다. 숨김 경로 검색은 사용자의 명시적 승인 범위에서만 한다. 배포 통합을 위한 `.github/` 작업은 승인되었다.

## 반드시 지킬 배포 조건

**완성 ZIP 하나를 폐쇄망 Windows PC로 옮기고, 압축을 풀어 `setup.ps1`에서 사내 모델 API를 등록하면 어느 폴더에서든 `opencode`를 실행할 수 있어야 한다.**

- GitHub Actions가 고정 버전·해시의 OpenCode·Python·rg·fd, MCP 패키지, custom tool 의존성을 준비한다. 대상 PC에 Node.js·Python 설치, npm/pip 설치, 다운로드·빌드를 요구하지 않는다.
- 배포 이름은 `opencode-kit-win-x64.zip`. README는 실제 배포 Release를 안내하며 소스 Download ZIP을 설치용으로 안내하지 않는다. 새 배포를 만들기 전에는 새 이름의 다운로드 링크가 유효하다고 주장하지 않는다.
- 모델 목록 조회·자동 업데이트·기본 플러그인·LSP 다운로드·공유를 비활성화하고 rg를 동봉한다. `bin/opencode.cmd`는 승인된 유일한 실행 진입점 예외로, npm offline을 해당 프로세스에만 적용한다. 시스템 전체 npm 설정은 바꾸지 않는다.
- `scripts/`에는 `setup.ps1`만 둔다. 루트 `setup.ps1`은 바로가기다. 필수 파일 확인·프로바이더 등록·모델 탐색·설정 설치·시스템 PATH/환경 변수 설정을 이 파일에서 처리한다.
- 생성 설정은 `%USERPROFILE%/.config/opencode/opencode.json`, 사용자 설정은 `opencode.jsonc`다. 교체 파일은 `.bak`으로 백업하고 사용자 jsonc는 덮어쓰지 않는다. 기존 Kilo 설정·세션은 삭제하지 않는다. 플러그인은 runtime/opencode-tools의 고정 의존성을 사용한다. OpenCode 초기화를 위한 의존성 복사는 kit 소유 마커가 있거나 비어 있는 설정 폴더에만 하며, 비관리 기존 설치는 호환성을 확인하거나 중단한다.
- API 키는 시스템 환경 변수에 보관한다. `apiKeyEnv`에 잘못 넣은 `sk-...` 키는 시스템 등록 성공 후 변수 이름으로 정정하며, 원문 키를 오류·JSON 백업에 복제하지 않는다. 실제 API 키·`config/models.json`·Redis 실제 매핑·세션·캐시는 ZIP에 넣지 않는다.
- 진입점은 OPENCODE_DB가 없으면 프로세스 전용 `opencode-kit.db`를 사용한다. 기존 opencode.db는 삭제·변환하지 않는다. 명시적 OPENCODE_DB는 존중하고 셋업은 실제 session 테이블 초기화까지 검사한다.
- 자동 배포를 제거하거나 실행 파일 준비 책임을 사용자에게 넘기지 않는다.

## 인코딩 및 검증

- OpenCode 본체는 포크하지 않는다. 플러그인의 동일 이름 `read/edit/write`와 별칭 도구가 동봉 Python의 엄격한 인코딩 I/O를 사용한다.
- 원본 파일을 임시 UTF-8로 바꾸지 않는다. 명시 규칙 → BOM/유효 UTF-8으로 결정하며, 미지정 비 UTF-8은 거부한다. 변환 손실·모호한 치환·승인 중 파일 변경은 쓰기 전에 중단한다.
- 승인·외부 디렉터리 확인을 우회하지 않는다. `apply_patch`는 차단한다. 셸 및 별도 플러그인은 샌드박스가 아니므로 파일 쓰기 우회를 허용하지 않도록 안내한다.
- 인코딩·도구 승인·오프라인 초기화의 회귀 테스트는 허용한다. CI는 테스트 후 ZIP을 만들고 다른 경로에 풀어 `setup.ps1 -Check`·OpenCode 버전·설정/도구 로딩을 검사한다. 실제 API·UI 검증과 구분하며 미실행 CI를 성공으로 보고하지 않는다.
- Windows UI MCP는 stdio와 UI 테스트용 도구만 노출한다. 텔레메트리·업데이트 확인을 끄고 캡처·조작 모두 승인받는다. 실제 Windows UI 검증 없이 동작 성공으로 보고하지 않는다.
