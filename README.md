# kilo-kit

폐쇄망 Windows PC에서 사내 AI 모델로 [Kilo CLI](https://github.com/Kilo-Org/kilocode)(`kilo.exe`)를 사용할 수 있도록 필요한 파일을 모은 배포본입니다. ZIP을 내려받아 PC로 옮긴 뒤, `setup.ps1`에서 사내 API 주소와 키를 등록하면 됩니다. 대상 PC에서 인터넷으로 파일을 받거나 Node.js·Python을 따로 설치할 필요는 없습니다.

## 포함된 도구

- **Kilo CLI 7.8.18** — `bin\kilo\`에 실행 파일과 실행에 필요한 리소스가 들어 있습니다.
- **빌드센터 MCP** — 빌드센터 Redis에서 프로젝트·모듈·담당자별 빌드 및 시험 결과와 로그를 조회합니다. 전용 Python 런타임도 함께 제공합니다. 자세한 내용은 [빌드센터 MCP 안내](mcp/build-center/README.md)를 참고하세요.
- **rg(ripgrep) 15.2.0, fd 10.5.0** — 내용 검색과 파일 찾기에 사용하는 도구로, `bin\`에 들어 있습니다.

확장, Edge MCP, 언어 서버(LSP)는 포함하지 않습니다.

## 시작하기

**[최신 배포 ZIP 다운로드](https://github.com/junyeong-nero/kilo-kit/releases/latest/download/kilo-kit-win-x64.zip)**

[Releases 페이지](https://github.com/junyeong-nero/kilo-kit/releases)에서도 받을 수 있습니다. GitHub의 **Download ZIP**이나 **Source code (zip)**은 소스 코드만 담고 있어 바로 실행할 수 없습니다. 반드시 **kilo-kit-win-x64.zip**을 받아 주세요.

1. ZIP을 폐쇄망 PC로 옮기고 원하는 위치에 압축을 풉니다. 아래는 `D:\kilo-kit`에 푼 경우입니다.
2. PowerShell에서 다음 명령을 실행합니다. 관리자 권한 확인 창이 뜨면 **예**를 누릅니다.
   ```powershell
   cd D:\kilo-kit
   Set-ExecutionPolicy -Scope Process Bypass -Force
   .\setup.ps1
   ```
3. 안내에 따라 사내 API 주소(예: `http://10.0.0.1:8000/v1`)와 API 키를 입력합니다. 빌드센터 인증 정보는 묻지 않습니다. 모델이 여러 개면 기본으로 사용할 모델을 선택합니다.
4. 설정이 끝나면 터미널을 완전히 닫았다가 다시 엽니다. 이제 어느 폴더에서든 `kilo`를 실행할 수 있습니다.

옵션이나 문제 해결 방법이 필요하면 [설치와 설정](docs/installation.md)을 참고하세요.

## setup.ps1이 설정하는 것

셋업은 사내 API에서 모델 목록을 가져오고, Kilo 설정과 시스템 환경 변수를 등록합니다. API 키도 시스템 변수에 저장하므로 관리자 권한이 필요합니다.

| 항목 | 설정 내용 |
|---|---|
| 모델 프로바이더 | 입력한 주소의 `/models`에서 모델 목록과 컨텍스트 크기를 읽어 `config\models.json`을 만듭니다. 모델이 여러 개면 기본 모델을 선택할 수 있습니다. |
| Kilo 설정 | `%USERPROFILE%\.config\kilo\`에 `kilo.json`과 도구 사용 규칙인 `AGENTS.md`를 설치합니다. `kilo.json`에는 프로바이더·모델·빌드센터 MCP·권한·오프라인 설정이 들어갑니다. 기존 파일은 `.bak`으로 백업하고, 개인 설정용 `kilo.jsonc`는 덮어쓰지 않습니다. |
| ripgrep | Kilo가 인터넷에서 다운로드하지 않도록, 동봉된 rg를 `%USERPROFILE%\.cache\kilo\bin\rg.exe`에도 복사합니다. |
| 시스템 PATH | 어느 폴더에서든 `kilo`, `rg`, `fd`를 실행할 수 있도록 `bin\kilo`와 `bin`을 등록합니다. |
| 시스템 변수 | API 키(`CORP_LLM_API_KEY`), 실행 옵션으로 지정한 경우에만 빌드센터 Redis 인증 정보(`REDISCLI_AUTH`, `HSC_REDIS_USERNAME`), 배포 폴더 경로(`KILO_KIT_HOME`)를 등록합니다. |

외부 통신을 끄기 위해 `KILO_DISABLE_AUTOUPDATE`, `KILO_DISABLE_MODELS_FETCH`, `KILO_DISABLE_LSP_DOWNLOAD`, `KILO_DISABLE_SHARE`, `KILO_DISABLE_SESSION_INGEST`, `KILO_TELEMETRY_LEVEL=off`도 설정합니다. 모델을 사용하려면 사내 API에는 연결할 수 있어야 합니다.

## 배포본을 관리한다면

GitHub Actions(`.github/workflows/offline.yml`)가 [고정된 버전과 해시](config/offline-artifacts.lock.json)를 기준으로 Kilo·Python·rg·fd를 받고, [requirements.lock](config/redis/requirements.lock)에 지정된 빌드센터 MCP용 Python 패키지를 설치해 ZIP을 만듭니다. `v*` 태그를 푸시하면 Releases에 게시합니다.

- Kilo 설정 원본: [config/kilo.template.json](config/kilo.template.json)
- 모델에 전달하는 도구 사용 규칙: [config/AGENTS.md](config/AGENTS.md)
- [구성요소 버전과 라이선스](third_party/README.md)
