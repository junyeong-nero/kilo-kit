# kilo-kit

폐쇄망 Windows PC에서 사내 AI 모델로 [Kilo CLI](https://github.com/Kilo-Org/kilocode)(`kilo.exe`)를 쓰기 위한 배포본입니다. 들어 있는 것은 이것뿐입니다.

- **Kilo CLI** 7.8.18 (`bin\kilo\`)
- **빌드센터 MCP**: 빌드센터 Redis의 프로젝트·모듈·담당자별 빌드·시험 결과와 로그 조회 ([안내](mcp/build-center/README.md)). 전용 Python 런타임 동봉
- **rg**(ripgrep 15.2.0), **fd** 10.5.0 (`bin\`)

확장, Edge MCP, 언어 서버(LSP)는 넣지 않습니다.

## 설치

완성 ZIP은 Releases에서 배포합니다. GitHub의 소스 코드 **Download ZIP**은 실행 파일이 없어 동작하지 않습니다.

1. [GitHub Releases](https://github.com/junyeong-nero/kilo-kit/releases)에서 최신 `v*` 릴리스의 **kilo-kit-win-x64.zip**을 받아 폐쇄망 PC로 옮기고 원하는 위치(예: `D:\`)에 풉니다.
2. 배포 폴더에서 PowerShell을 열고 실행합니다. 관리자 권한 확인 창이 뜨면 **예**를 누릅니다.
   ```powershell
   cd D:\kilo-kit
   Set-ExecutionPolicy -Scope Process Bypass -Force
   .\setup.ps1
   ```
   사내 API 주소(예: `http://10.0.0.1:8000/v1`)와 API 키를 물어봅니다. 나머지는 자동입니다.
3. 터미널을 완전히 닫았다가 다시 열고, 아무 폴더에서 `kilo`를 실행합니다.

단계별 설명, 옵션, 문제 해결은 [설치와 설정](docs/installation.md)에 있습니다.

## setup.ps1이 하는 일

| 항목 | 내용 |
|---|---|
| 모델 프로바이더 | 입력한 주소의 `/models`에서 모델 목록과 컨텍스트 크기를 읽어 `config\models.json`을 완성. 모델이 여러 개면 기본 모델을 고름 |
| Kilo 설정 | `%USERPROFILE%\.config\kilo\`에 `kilo.json`(프로바이더·모델·빌드센터 MCP·권한·오프라인 설정)과 `AGENTS.md`(도구 사용 규칙) 설치. 기존 파일은 `.bak`으로 백업. 개인 설정용 `kilo.jsonc`는 덮어쓰지 않음 |
| ripgrep | Kilo가 인터넷에서 받으려는 rg를 `%USERPROFILE%\.cache\kilo\bin\rg.exe`에 복사 |
| 시스템 PATH | `bin\kilo`(kilo), `bin`(rg, fd) |
| 시스템 변수 | API 키(`CORP_LLM_API_KEY`), 빌드센터 Redis 인증(`REDISCLI_AUTH`, `HSC_REDIS_USERNAME`, 입력한 경우), 외부 통신 차단 스위치(`KILO_DISABLE_AUTOUPDATE`, `KILO_DISABLE_MODELS_FETCH`, `KILO_DISABLE_LSP_DOWNLOAD`, `KILO_DISABLE_SHARE`, `KILO_DISABLE_SESSION_INGEST`, `KILO_TELEMETRY_LEVEL=off`), `KILO_KIT_HOME` |

## 개발자용

- GitHub Actions(`.github/workflows/offline.yml`)가 [고정된 버전·해시](config/offline-artifacts.lock.json)로 Kilo·Python·rg·fd를 받고, 빌드센터 MCP용 Python 패키지([requirements.lock](config/redis/requirements.lock))를 설치해 ZIP을 만듭니다. `v*` 태그를 푸시하면 Releases에 게시합니다.
- Kilo 설정 원본은 [config/kilo.template.json](config/kilo.template.json), 모델에 주는 규칙은 [config/AGENTS.md](config/AGENTS.md)입니다.
- [구성요소 버전과 라이선스](third_party/README.md)
