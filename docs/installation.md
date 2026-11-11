# 설치와 설정

배포본은 Windows x64용입니다. 기존 배포 대상은 Windows 10 1903 이상/Windows 11이며, 새 OpenCode 전환본은 대상 OS에서 별도 실기 확인이 필요합니다. Node.js·Python·npm/pip를 대상 PC에 설치하지 않습니다. 사내 OpenAI 호환 API와 셋업 시 시스템 환경 변수를 등록할 관리자 권한은 필요합니다.

## 설치

1. [Releases](https://github.com/junyeong-nero/kilo-kit/releases)에서 `opencode-kit-win-x64.zip`이 첨부된 릴리스를 받습니다. 해당 파일이 없다면 아직 미배포 상태입니다. Source code (zip)은 설치용이 아닙니다.
2. 함께 제공되는 `.sha256`과 `Get-FileHash .\opencode-kit-win-x64.zip -Algorithm SHA256` 결과를 비교합니다.
3. ZIP을 반입해 예를 들어 `D:\opencode-kit`에 풉니다.
4. PowerShell에서 실행합니다.

   ```powershell
   cd D:\opencode-kit
   Set-ExecutionPolicy -Scope Process Bypass -Force
   .\setup.ps1
   ```

5. API 주소·키·기본 모델을 입력합니다. 관리자 승인 후 터미널 프로그램을 완전히 종료하고 다시 엽니다.
6. 프로젝트 폴더에서 `opencode`를 실행합니다. `opencode mcp list`로 MCP 상태를 확인할 수 있습니다.

설치 폴더를 이동했다면 새 위치에서 셋업을 다시 실행하세요. 실행은 `bin\opencode.cmd`를 거치는 `opencode` 명령으로 해야 합니다. 내부 EXE를 직접 실행하면 프로세스 전용 npm offline 설정을 우회합니다.

## 셋업 옵션

| 옵션 | 설명 |
|---|---|
| `-BaseUrl`, `-ApiKey`, `-Model` | 프로바이더와 모델 직접 지정. 키를 인자로 주면 명령 기록에 남으므로 숨김 입력을 권장 |
| `-RedisPassword`, `-RedisUsername` | 필요할 때만 빌드센터 인증 등록. 입력하지 않으면 기존 환경 변수 유지 |
| `-Reconfigure` | 주소·키·기본 모델 다시 선택 |
| `-NonInteractive` | 대화형 입력 없이 실행. 필수 값이 없으면 오류 |
| `-Check` | 필수 배포 파일이 있는지만 확인. 설정·환경 변경 없음 |

`/models`로 목록을 조회합니다. 이미 `config/models.json`에 등록된 모델이 있으면 API 조회 실패 시 경고 후 그 목록을 사용할 수 있습니다. 직접 지정한 contextWindow·maxTokens·name·imageInput은 유지합니다.

## 설정 위치

| 위치 | 내용 |
|---|---|
| `<배포 폴더>\config\models.json` | 사내 API 주소·모델 목록·API 키 환경 변수 이름. 실제 키는 저장하지 않음 |
| `%USERPROFILE%\.config\opencode\opencode.json` | 셋업이 생성하는 모델·MCP·권한·인코딩 플러그인 설정 |
| `%USERPROFILE%\.config\opencode\opencode.jsonc` | 사용자 설정. 셋업이 덮어쓰지 않으며 json보다 우선 |
| `%USERPROFILE%\.config\opencode\AGENTS.md` | kit 도구 사용 규칙 |
| `%USERPROFILE%\.config\opencode\node_modules` 등 | 초기 npm 설치를 피하기 위해 복사하는 동봉 의존성 |
| `<배포 폴더>\runtime\opencode-tools\` | 인코딩 플러그인·Python helper·고정 npm 의존성 |
| `<프로젝트 루트>\encoding-rules.json` | 레거시 파일 인코딩 명시. [인코딩 안내](encoding.md) |

XDG_CONFIG_HOME/XDG_CACHE_HOME이 설정되어 있으면 해당 위치를 따릅니다. 기존 파일 교체 시 `.bak`으로 백업합니다. 사용자 jsonc의 provider·plugin·permission·MCP 설정이 kit 설정을 변경할 수 있으니 경고를 확인하세요.

OpenCode는 기본 프로필 외에 기존 `~/.opencode`도 검색하므로, 해당 폴더가 있으면 셋업에서 초기 의존성을 확인합니다. 기존 패키지 설치가 정확한 동봉 버전과 호환되면 유지하고, 충돌하면 무단으로 덮어쓰지 않습니다. 기존 패키지 설치를 백업·분리하거나 깨끗한 XDG_CONFIG_HOME을 선택해야 합니다. 홈의 `.opencode`가 충돌 원인이라면 그 폴더도 별도 확인하세요.

kit가 소유한 의존성 디렉터리는 `opencode-kit-dependencies.json`으로 표시합니다. 그 디렉터리의 npm 패키지를 임의 변경하면 재셋업에서 덮어쓸 수 있으므로 별도 설치와 섞지 마세요.

## Kilo에서 전환

- 기존 Kilo 설정·인증·세션은 자동 이동하거나 삭제하지 않습니다. 대화 이력 호환성도 가정하지 않습니다.
- 기존 배포의 `config/models.json`, Redis 실제 매핑을 새 배포의 같은 위치로 복사한 뒤 셋업하면 사내 정보를 재사용할 수 있습니다. 키는 기존 시스템 변수를 사용합니다.
- `CORP_LLM_API_KEY`·Redis 인증 변수는 두 프로그램에서 공유할 수 있으므로 무조건 삭제하지 않습니다.
- 새 PATH는 `bin`입니다. 이전 Kilo PATH·`KILO_*` 변수는 롤백을 위해 보존합니다. 더 이상 쓰지 않을 때 사용자가 정리하세요.
- GitHub 저장소·로컬 폴더 리네임과 새 릴리스 게시 여부는 별도로 확인하세요.

## 이미지와 UI 테스트

Qwen3.5-397B 계열은 이미지 입력 가능 모델로 자동 등록합니다. 다른 모델은 `config/models.json`에 `"imageInput": true`를 지정하고 셋업을 다시 실행하세요. 모델뿐 아니라 사내 API도 이미지 입력을 처리해야 합니다.

Windows-MCP는 UI 트리와 이미지 결과를 제공합니다. 무관한 창을 닫고 테스트 앱이 있는 모니터의 캡처부터 확인하세요. 동봉 0.8.5는 특정 사각형 영역만 캡처하는 인자를 지원하지 않습니다. Windows 로컬의 로그인된 잠기지 않은 세션에서 사용하며, AI와 마우스·키보드를 동시에 사용하지 마세요. [Windows-MCP 안내](../mcp/windows/README.md).

## 외부 통신과 초기 의존성

- 진입점이 OpenCode 업데이트·모델 목록 조회·기본 플러그인·LSP 다운로드를 끄고, 상속된 OTLP 전송 설정을 비웁니다.
- 설정은 share/formatter/LSP를 끄고 웹 검색 도구를 거부합니다. rg는 PATH와 OpenCode 캐시에 동봉합니다.
- npm offline은 OpenCode 프로세스에만 적용합니다. 초기 필수 패키지는 CI에서 준비해 복사합니다. 사용자의 일반 npm 설정은 변경하지 않습니다.
- 프로젝트 `.opencode`에 추가 패키지나 원격 플러그인이 있다면 자동 설치가 실패할 수 있습니다. 그것까지 임의로 온라인 설치하지 않습니다. 필요한 추가 의존성은 별도의 사내 반입 검토가 필요합니다.
- 원격 MCP, 셸 명령, 사용자 플러그인, 외부 URL 지시까지 차단하는 샌드박스는 아닙니다. 업무 보안 정책과 네트워크 통제를 함께 사용하세요.
- 모델 API, Redis 등 업무용 사내 서비스 연결은 필요합니다. MCP 캡처·UI 텍스트도 모델 API로 전달되는 업무 데이터입니다.

## 문제 해결

| 증상 | 확인 |
|---|---|
| `Missing bundle file` | 소스 ZIP이 아닌 완성 배포 ZIP인지 확인 |
| `Existing npm dependencies ... not managed` | 기존 OpenCode 패키지를 덮어쓰지 않도록 중단한 것. 백업·분리 후 재시도 |
| `opencode`를 찾지 못함 | 터미널/IDE를 완전히 종료 후 재실행, PATH의 새 bin 확인 |
| 인코딩 오류 | [encoding-rules.json](encoding.md) 설정. 기본 도구·셸로 우회 금지 |
| 모델/도구가 예상과 다름 | 사용자·프로젝트 설정, OPENCODE_CONFIG* 변수와 추가 플러그인의 덮어쓰기 확인 |
| API 인증·조회 실패 | 주소, 키, `/models` 응답 확인 |
| MCP 연결·캡처 실패 | `opencode mcp list`, Windows 세션·권한, 사내 API 이미지 지원 확인 |

CI는 인코딩 테스트와 초기 로딩을 검사하지만 사내 API 추론·실제 MFC/WPF/Word 작업은 검증하지 않습니다.

## 제거

시스템 PATH의 이 배포본 `bin`, `OPENCODE_KIT_HOME`을 제거합니다. 다른 도구도 사용하는 API·Redis 변수는 삭제하지 마세요. OpenCode 설정은 `.bak`을 확인해 복원하고, kit 소유 의존성인지 확인한 뒤 제거합니다. 기존 Kilo 설정은 별도로 남아 있습니다.
