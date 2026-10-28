# 설치와 설정

배포 ZIP에는 실행에 필요한 파일이 들어 있습니다. 폐쇄망 PC에서는 압축을 풀고 `setup.ps1`을 한 번 실행하면 됩니다. Node.js·Python·Git을 별도로 설치할 필요는 없습니다.

## 시작하기 전에

다음을 준비해 주세요.

- **Windows 10 1903 이상 또는 Windows 11 (x64)**
- **사내 모델 API 주소와 API 키** — vLLM 같은 OpenAI 호환 API를 사용합니다. 모델 ID는 몰라도 됩니다. 셋업이 API에서 모델 목록을 가져옵니다.
- **PC의 관리자 권한** — 시스템 환경 변수를 등록할 때 필요합니다.

## 1. 배포 ZIP 받기

[Releases](https://github.com/junyeong-nero/kilo-kit/releases)에서 **kilo-kit-win-x64.zip**을 받습니다. **Source code (zip)**은 실행 파일이 없는 소스 코드이므로 설치용으로 사용할 수 없습니다.

파일이 온전히 받아졌는지 확인하려면 함께 제공되는 `.sha256` 파일도 받으세요. 다음 명령으로 나온 해시를 `.sha256` 파일의 값과 비교하면 됩니다.

```powershell
Get-FileHash .\kilo-kit-win-x64.zip -Algorithm SHA256
```

ZIP을 폐쇄망 PC로 옮겨 원하는 위치에 압축을 풉니다. `D:\`에 풀었다면 `D:\kilo-kit\setup.ps1`이 있는지 확인하세요. 설치 후 폴더를 다른 곳으로 옮겼다면, 새 위치에서 `setup.ps1`을 다시 실행해야 합니다.

## 2. 셋업 실행하기

PowerShell을 열고 다음 명령을 실행합니다. 관리자 권한 확인 창이 뜨면 **예**를 누르세요.

```powershell
cd D:\kilo-kit
Set-ExecutionPolicy -Scope Process Bypass -Force
.\setup.ps1
```

셋업에서 안내하는 순서대로 입력합니다.

1. **사내 API 주소** — 예: `http://10.0.0.1:8000/v1`. `/v1` 없이 입력하면 셋업이 `/v1`을 붙인 주소도 시도합니다.
2. **API 키** — 입력한 값은 화면에 표시되지 않습니다. 인증이 필요 없는 API라면 Enter를 누르세요.
3. **기본 모델 번호** — 모델이 여러 개일 때 사용할 모델을 고릅니다.

빌드센터 Redis 계정과 비밀번호는 묻지 않습니다. 인증 없이 접속하는 환경에서는 별도로 설정할 필요가 없습니다. 인증이 필요한 경우에만 아래 실행 옵션으로 지정하세요. 기존에 등록된 Redis 인증 환경 변수는 그대로 유지됩니다.

`Setup complete.`가 표시되면 설정이 끝난 것입니다. Windows Terminal이나 VS Code 등 사용 중인 터미널 프로그램을 **완전히 닫고 다시 연 뒤**, 어느 폴더에서든 `kilo`를 실행해 보세요.

### 설정을 바꾸고 싶다면

사내 API에 모델이 추가되거나 바뀌었을 때는 `setup.ps1`을 다시 실행하면 됩니다. 저장된 주소와 키로 모델 목록을 새로 가져와 설정을 갱신합니다.

주소·키·기본 모델을 다시 선택하려면 다음처럼 실행하세요.

```powershell
.\setup.ps1 -Reconfigure
```

필요한 값을 실행 옵션으로 넘길 수도 있습니다.

| 옵션 | 설명 |
|---|---|
| `-BaseUrl <주소> -ApiKey <키> -Model <ID>` | 주소·키·모델을 직접 지정합니다. `-ApiKey`로 입력한 키는 명령 기록에 남으므로, 가능하면 셋업의 숨김 입력창을 사용하세요. |
| `-RedisPassword`, `-RedisUsername` | 인증이 필요한 환경에서만 빌드센터 Redis 인증 정보를 지정합니다. 비밀번호를 옵션으로 입력하면 명령 기록에 남을 수 있습니다. |
| `-Reconfigure` | 주소·키·기본 모델을 다시 설정합니다. 빌드센터 인증 정보는 묻지 않습니다. |
| `-NonInteractive` | 입력을 묻지 않고 실행합니다. 자동화용 옵션이며, 필요한 값이 없으면 오류로 종료됩니다. |
| `-Check` | 설정을 바꾸지 않고 배포 파일이 갖춰져 있는지만 확인합니다. |

## 설정 파일은 어디에 있나요?

| 위치 | 용도 |
|---|---|
| `<배포 폴더>\config\models.json` | 프로바이더 주소, API 키를 저장한 환경 변수 이름, 모델 목록과 기본 모델을 담습니다. 셋업이 만들고 갱신하며, 직접 수정한 `contextWindow`·`maxTokens`·`name`은 다음 실행에서도 유지합니다. |
| `%USERPROFILE%\.config\kilo\kilo.json` | 셋업이 실행할 때마다 다시 만드는 Kilo 설정입니다. 개인 설정은 이 파일 대신 `kilo.jsonc`에 작성하세요. |
| `%USERPROFILE%\.config\kilo\kilo.jsonc` | 개인 설정을 넣는 파일입니다. `kilo.json`보다 나중에 읽혀 우선 적용되며, 셋업이 덮어쓰지 않습니다. |
| `%USERPROFILE%\.config\kilo\AGENTS.md` | 모든 프로젝트에 적용되는 도구 사용 규칙입니다. 배포본의 `config\AGENTS.md`를 복사한 파일입니다. |
| `<배포 폴더>\config\redis\` | 빌드센터 프로젝트별 Redis IP와 담당자 매핑을 두는 곳입니다. [빌드센터 MCP 안내](../mcp/build-center/README.md)를 참고하세요. |

셋업이 기존 설정 파일을 교체할 때는 `.bak`으로 백업합니다.

**API 키는 `kilo.json`에 저장하지 않습니다.** 기본적으로 시스템 환경 변수 `CORP_LLM_API_KEY`에 저장하고 여기서 읽습니다. 시스템 환경 변수는 이 PC의 다른 사용자도 읽을 수 있다는 점에 유의하세요.

## 사용하면서 알아 둘 점

### 명령 실행 승인

셸 명령은 기본적으로 실행 전에 승인을 요청합니다. 다만 `Get-ChildItem`·`Get-Content`·`rg`·`fd`·`git status/diff/log`·`svn status/diff/log` 같은 조회 명령은 승인 없이 실행합니다. 빌드센터 도구도 조회 전용이므로 별도 승인을 묻지 않습니다. 이 규칙은 `kilo.jsonc`의 `permission`에서 바꿀 수 있습니다.

### 언어 서버와 파일 인코딩

언어 서버(LSP)는 배포본에 포함하지 않으며, 설정에서도 `"lsp": false`로 꺼 둡니다.

Kilo의 편집 도구는 파일 인코딩을 자동으로 판별합니다. 다만 한글이 적은 짧은 CP949 파일은 잘못 판별해 한글이 깨질 수 있습니다. 중요한 레거시 파일을 수정했다면 `git diff`나 `svn diff`로 변경 내용을 확인하세요.

### 외부 통신

models.dev 모델 목록 조회, 자동 업데이트, 텔레메트리, LSP·ripgrep 다운로드, 세션 공유는 셋업이 등록하는 시스템 변수와 `kilo.json` 설정으로 끕니다. 모델 응답을 받으려면 사내 API 연결은 필요합니다.

## 문제가 생겼다면

| 증상 | 확인할 내용 |
|---|---|
| “스크립트를 실행할 수 없습니다” | 같은 PowerShell 창에서 `Set-ExecutionPolicy -Scope Process Bypass -Force`를 먼저 실행하세요. 그룹 정책으로 제한된 경우에는 IT 담당자에게 문의해야 합니다. |
| `Missing bundle file` / `Invalid executable` | 소스 ZIP을 받았거나 압축이 제대로 풀리지 않았을 수 있습니다. Releases의 **kilo-kit-win-x64.zip**을 받아 다시 풀어 주세요. |
| `Could not list models` / `rejected the API key` | API 주소·키·네트워크 연결을 확인하세요. `/models` 요청이 응답하는지도 확인하고, 인증이 필요한 API라면 요청에 인증 헤더를 포함해야 합니다. |
| `Administrator rights are required` | 시스템 환경 변수 등록에 필요한 권한을 얻지 못했습니다. 셋업을 다시 실행하고 관리자 권한 확인 창에서 **예**를 누르세요. |
| `kilo`를 찾을 수 없음 | 새 PATH가 적용되도록 터미널 프로그램을 완전히 닫고 다시 여세요. IDE 안의 터미널이라면 IDE도 다시 시작해야 합니다. |
| 다른 모델이나 프로바이더가 사용됨 | 셋업 경고에 나온 `kilo.jsonc`·`opencode.json` 등의 파일이 설정을 덮어쓰고 있는지 확인하세요. 셋업 설정을 사용하려면 해당 파일의 `model`·`provider`·`enabled_providers` 항목을 정리하세요. |
| 빌드센터 도구 오류 | `config\redis\server_IP_mappings.json`과 Redis 인증 변수를 확인하세요. `kilo mcp list`로 MCP 상태를 확인할 수 있습니다. |

## 등록한 설정 지우기

더 이상 사용하지 않는다면 **시스템 환경 변수 편집**에서 다음 항목을 제거하세요. 다른 프로그램에서도 사용 중인 변수는 지우기 전에 확인해 주세요.

- Path의 `<배포 폴더>\bin\kilo`, `<배포 폴더>\bin`
- `KILO_KIT_HOME`, 셋업이 등록한 `KILO_DISABLE_*`, `KILO_TELEMETRY_LEVEL`
- `CORP_LLM_API_KEY`, `REDISCLI_AUTH`, `HSC_REDIS_USERNAME`

마지막으로 `%USERPROFILE%\.config\kilo\`의 `kilo.json`과 `AGENTS.md`를 삭제합니다. 셋업 이전 설정으로 돌아가려면 `.bak` 백업 파일을 확인하세요.
