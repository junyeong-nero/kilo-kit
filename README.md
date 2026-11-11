# opencode-kit

폐쇄망 Windows PC에서 사내 AI 모델로 [OpenCode CLI](https://github.com/anomalyco/opencode)를 사용하는 배포본입니다. ZIP을 반입해 압축을 풀고 `setup.ps1`에서 API 주소와 키를 등록하면 됩니다. 대상 PC에서 Node.js·Python·npm/pip 설치나 인터넷 다운로드를 하지 않습니다.

> Kilo → OpenCode 전환 작업입니다. 로컬 폴더와 GitHub 저장소 이름은 아직 `kilo-kit`이며 기존 Kilo 릴리스는 그대로 유지합니다. **새 배포를 게시하기 전에는 기존 v0.1.3을 OpenCode 배포본으로 사용하지 마세요.**

## 배포 ZIP

[Releases 페이지](https://github.com/junyeong-nero/kilo-kit/releases)에서 **`opencode-kit-win-x64.zip`**이 첨부된 릴리스를 받으세요. 이 이름의 파일이 아직 없다면 OpenCode 전환본은 미배포 상태입니다. GitHub의 Download ZIP / Source code (zip)은 실행 가능한 배포본이 아닙니다.

## 포함된 도구

- **OpenCode 1.19.5** — 공식 Windows x64 `opencode.exe`. 본체는 포크하지 않습니다.
- **인코딩 보존 custom tools** — `read/edit/write`를 교체하고 `encoding_read/encoding_edit/encoding_write` 별칭도 제공합니다. CP949·EUC-KR·UTF-8·UTF-16LE/BE를 엄격하게 처리하며, 모르는 인코딩을 추측해서 쓰지 않습니다. [인코딩 안내](docs/encoding.md).
- **빌드센터 MCP** — Redis 빌드·시험 결과와 로그 조회. [안내](mcp/build-center/README.md).
- **Word MCP** — word-mcp-live 1.6.21. Word에 열린 문서를 읽고 편집합니다. [안내](mcp/word/README.md).
- **Windows-MCP 0.8.5** — Windows 앱 조작·UI 조회·스크린샷. 캡처와 조작은 승인 대상입니다. [안내](mcp/windows/README.md).
- **Python 3.13.16, rg 15.2.0, fd 10.5.0**, MCP·custom tool 의존성.

VS Code 확장·LSP·SVN·Redis 실행 파일은 포함하지 않습니다. 빌드에는 회사 PC의 기존 Visual Studio/MSBuild/SDK를 사용합니다.

## 시작하기

1. ZIP을 폐쇄망 PC로 옮기고, 예를 들어 `D:\opencode-kit`에 압축을 풉니다.
2. PowerShell에서 실행합니다.
   ```powershell
   cd D:\opencode-kit
   Set-ExecutionPolicy -Scope Process Bypass -Force
   .\setup.ps1
   ```
3. 사내 API 주소와 키, 기본 모델을 지정합니다. 시스템 PATH·API 키 등록 시 관리자 승인이 필요합니다.
4. 터미널 프로그램을 완전히 종료하고 다시 연 뒤 프로젝트 폴더에서 `opencode`를 실행합니다.
5. 레거시 파일을 편집한다면 먼저 프로젝트 루트에 `encoding-rules.json`을 설정합니다. [예시](docs/encoding.md#규칙-파일).

Qwen3.5-397B는 이미지 입력 가능 모델로 자동 등록합니다. 다른 모델은 `config/models.json`의 `imageInput`을 설정하세요. 모델·사내 API 모두 이미지 요청을 지원해야 합니다.

## 셋업이 설정하는 것

| 항목 | 내용 |
|---|---|
| 프로바이더 | `/models`로 목록을 조회하고 `config/models.json` 생성. 키는 시스템 환경 변수에 저장 |
| OpenCode 설정 | `%USERPROFILE%\.config\opencode\opencode.json`과 `AGENTS.md` 생성. 기존 파일은 `.bak` 백업. 사용자 `opencode.jsonc`는 보존 |
| 초기 의존성 | 동봉한 npm 의존성을 복사해 첫 실행 시 다운로드가 필요 없게 함. 기존 비관리 패키지가 충돌하면 덮어쓰지 않고 중단 |
| PATH | `bin` 등록. `opencode.cmd`, rg, fd 실행 가능 |
| 실행 진입점 | `bin/opencode.cmd`가 OpenCode 프로세스에만 npm offline·업데이트/모델 목록 조회 차단 등을 적용. 시스템 npm 설정은 변경하지 않음 |
| MCP | 기존 3개 서버를 동봉 Python으로 실행. 패키지 버전 충돌을 막도록 폴더 분리 |

개인·프로젝트에서 추가한 원격 플러그인, 도구, 외부 URL 지시는 별도로 검토해야 합니다. 이 설정은 네트워크 샌드박스가 아닙니다. 자세한 마이그레이션·오프라인 제약은 [설치와 설정](docs/installation.md)을 참고하세요.

## 배포본 관리

GitHub Actions가 [아티팩트 lock](config/offline-artifacts.lock.json), MCP requirements.lock, [custom tool package-lock](tools/encoding/package-lock.json)을 기준으로 ZIP을 만듭니다. 인코딩 회귀 테스트 후 ZIP 재배치·셋업·OpenCode 초기 설정/도구 로딩을 검사합니다. `v*` 태그를 푸시하면 Releases에 게시합니다.

CI는 사내 API 추론, 실제 MFC/WPF·Word 조작을 검증하지 않습니다. 테스트 결과와 실기 검증을 구분하세요.

- 설정 원본: [config/opencode.template.json](config/opencode.template.json)
- 모델에 전달할 규칙: [config/AGENTS.md](config/AGENTS.md)
- [라이선스](third_party/README.md)
