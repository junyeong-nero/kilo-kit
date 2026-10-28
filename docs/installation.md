# 설치와 설정

## 준비할 것

- Windows 10 1903 이상 또는 Windows 11 (x64)
- 사내 모델 API의 **주소**와 **API 키** (OpenAI 호환 API, 예: vLLM). 모델 ID는 몰라도 됩니다. `setup.ps1`이 API에서 찾습니다.
- 이 PC의 **관리자 권한** (시스템 환경 변수 등록에 한 번 필요)
- (선택) 빌드센터 Redis 비밀번호·계정

Node.js·Python·Git 등 다른 프로그램은 설치하지 않아도 됩니다.

## 1. ZIP 받기와 풀기

[Releases](https://github.com/junyeong-nero/kilo-kit/releases)에서 **kilo-kit-win-x64.zip**과 `.sha256`을 받습니다. 해시 확인:

```powershell
Get-FileHash .\kilo-kit-win-x64.zip -Algorithm SHA256
```

폐쇄망 PC의 원하는 위치에 풉니다. `D:\`에 풀면 `D:\kilo-kit\setup.ps1`이 생깁니다. 폴더를 옮기면 `setup.ps1`을 다시 실행해야 합니다.

## 2. setup.ps1 실행

```powershell
cd D:\kilo-kit
Set-ExecutionPolicy -Scope Process Bypass -Force
.\setup.ps1
```

차례로 묻는 것:

1. 사내 API 주소 (`http://10.0.0.1:8000/v1` 형식. `/v1`을 빼고 입력해도 자동으로 찾아봄)
2. API 키 (화면에 표시되지 않음. 키가 없는 API면 Enter)
3. 빌드센터 Redis 비밀번호·계정 (없으면 Enter)
4. 모델이 여러 개면 기본 모델 번호

`Setup complete.`가 나오면 끝입니다. 터미널(Windows Terminal, VS Code 등)을 **완전히 닫고 다시 연** 뒤 아무 폴더에서 `kilo`를 실행합니다.

### 옵션

| 옵션 | 용도 |
|---|---|
| `-BaseUrl <주소> -ApiKey <키> -Model <ID>` | 묻지 않고 지정. `-ApiKey`는 명령 기록에 남으니 가능하면 입력창을 쓰세요 |
| `-RedisPassword`, `-RedisUsername` | 빌드센터 Redis 인증 |
| `-Reconfigure` | 주소·키·기본 모델을 다시 입력 |
| `-NonInteractive` | 묻지 않음(스크립트 설치용). 필요한 값이 없으면 오류 |
| `-Check` | 아무것도 바꾸지 않고 배포 파일만 확인 |

다시 실행하면 저장된 주소·키로 모델 목록을 새로 읽어 설정을 갱신합니다. 사내 API에 모델이 추가·변경됐을 때도 다시 실행하면 됩니다.

## 설정 파일

| 위치 | 내용 |
|---|---|
| `<배포 폴더>\config\models.json` | 프로바이더 주소, 키를 담은 변수 이름, 모델 목록과 기본 모델. setup이 만들고 갱신. `contextWindow`·`maxTokens`·`name`을 직접 고치면 다음 setup에서도 유지 |
| `%USERPROFILE%\.config\kilo\kilo.json` | setup이 매번 다시 만드는 Kilo 설정. 직접 고치지 마세요 |
| `%USERPROFILE%\.config\kilo\kilo.jsonc` | 개인 설정. `kilo.json` 뒤에 읽혀 우선 적용. setup이 덮어쓰지 않음 |
| `%USERPROFILE%\.config\kilo\AGENTS.md` | 모든 프로젝트에 들어가는 도구 사용 규칙(`config\AGENTS.md` 사본) |
| `<배포 폴더>\config\redis\` | 빌드센터 프로젝트별 Redis IP·담당자 매핑 ([안내](../mcp/build-center/README.md)) |

`kilo.json`에는 API 키가 들어가지 않습니다. 키는 시스템 변수 `CORP_LLM_API_KEY`에서 읽습니다. 시스템 변수는 이 PC의 다른 사용자도 읽을 수 있습니다.

## 사용할 때 알아 둘 것

- **명령 실행 승인:** 셸 명령은 기본으로 승인을 묻습니다. `Get-ChildItem`·`Get-Content`·`rg`·`fd`·`git status/diff/log`·`svn status/diff/log` 같은 조회 명령은 묻지 않습니다. 빌드센터 도구도 조회 전용이라 묻지 않습니다. 규칙은 `kilo.jsonc`의 `permission`에서 바꿀 수 있습니다.
- **LSP는 끔:** 언어 서버를 동봉하지 않고 `"lsp": false`로 둡니다.
- **CP949 파일:** Kilo의 편집 도구는 인코딩을 자동 판별하지만, 한글이 적은 짧은 CP949 파일은 잘못 판별해 한글이 깨질 수 있습니다. 중요한 레거시 파일은 수정 후 `git diff`/`svn diff`로 확인하세요.
- **외부 통신:** 모델 목록(models.dev), 자동 업데이트, 텔레메트리, LSP·ripgrep 다운로드, 세션 공유는 setup이 등록한 시스템 변수와 `kilo.json`으로 끕니다. 모델 응답에는 사내 API 연결이 필요합니다.

## 문제가 생길 때

| 증상 | 해결 |
|---|---|
| "스크립트를 실행할 수 없습니다" | 같은 창에서 `Set-ExecutionPolicy -Scope Process Bypass -Force`를 먼저 실행. 그래도 막히면 그룹 정책 제한이므로 IT 담당자에게 문의 |
| `Missing bundle file` / `Invalid executable` | 소스 ZIP을 받았거나 압축이 덜 풀림. Releases의 **kilo-kit-win-x64.zip**을 다시 풂 |
| `Could not list models` / `rejected the API key` | 주소·키·네트워크 확인. 브라우저나 `Invoke-RestMethod <주소>/models`로 응답이 오는지 확인 |
| `Administrator rights are required` | 관리자 확인 창에서 **예**를 누르지 않음. 다시 실행 |
| `kilo`를 찾을 수 없음 | 터미널 프로그램(IDE 포함)을 완전히 닫고 다시 열기 |
| 다른 모델·프로바이더가 쓰임 | setup 경고에 나온 `kilo.jsonc`/`opencode.json`의 `model`·`provider` 항목을 지우기 |
| 빌드센터 도구 오류 | `config\redis\server_IP_mappings.json`과 Redis 인증 변수 확인. `kilo mcp list`로 상태 확인 |

## 등록 해제

**시스템 환경 변수 편집**에서 Path의 `<배포 폴더>\bin\kilo`, `<배포 폴더>\bin` 두 항목과 `KILO_KIT_HOME`, `KILO_DISABLE_*`, `KILO_TELEMETRY_LEVEL`, `CORP_LLM_API_KEY`, `REDISCLI_AUTH`, `HSC_REDIS_USERNAME`을 지우고, `%USERPROFILE%\.config\kilo\`의 `kilo.json`·`AGENTS.md`를 지웁니다.
