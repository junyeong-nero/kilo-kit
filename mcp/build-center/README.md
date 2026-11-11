# 빌드센터 MCP

Redis에 저장된 빌드센터 결과(빌드·동적시험·정적시험, 로그)를 Kilo에서 조회하는 동봉 MCP 서버입니다. Kilo 설정(`%USERPROFILE%\.config\kilo\kilo.json`)의 서버 이름은 `build_center`입니다.

- **실행:** Kilo가 `kilo.json`의 `mcp.build_center` 항목을 보고 동봉 Python으로 이 서버를 stdio로 실행합니다. 항목은 `setup.ps1`이 [config/kilo.template.json](../../config/kilo.template.json)에서 만듭니다. Python·pip를 따로 설치하거나 서버를 직접 띄울 필요가 없습니다.
- **조회 전용:** Redis에는 프로젝트별 연결 풀을 재사용하고, 조회만 합니다.
- **도구 이름:** 모델에는 `build_center_<도구>` 이름으로 보입니다. 조회 전용이라 `kilo.json`의 `permission`에서 승인 없이 실행되도록 허용합니다.
- **실행 조건:** `<배포 폴더>\runtime\python\python.exe -I -X utf8 -B -m main`을 절대 경로로 실행하므로 PATH의 다른 Python과 섞이지 않습니다. 동봉 Python의 `python313._pth`가 이 폴더를 모듈 경로에 넣고, `-I`라서 프로젝트 폴더의 `main.py`가 대신 실행되지 않습니다. 인증 환경 변수는 Kilo의 환경을 물려받습니다.

## 사내 설정

### 프로젝트와 담당자

`config/redis/server_IP_mappings.json`에 프로젝트 이름과 Redis IP를 적습니다.

```json
{
  "ProjectA": "10.0.0.10",
  "ProjectB": "10.0.0.20"
}
```

`config/redis/owners.json`에는 담당자 ID와 표시 이름을 적습니다.

```json
{
  "example.user": "홍길동"
}
```

- `setup.ps1`은 두 파일이 없을 때만 빈 객체로 만들고, 있는 파일은 덮어쓰지 않습니다.
- 매핑 파일은 요청마다 다시 읽으므로 pi를 재시작하지 않아도 됩니다. 서버 IP·포트·DB·인증·TLS가 바뀌면 해당 연결과 검색 캐시를 새로 만듭니다.
- 실제 매핑은 Git과 배포 ZIP에서 빠지고 `.example.json`만 배포됩니다. 배포본을 다른 폴더로 바꿀 때는 실제 매핑 파일을 새 배포본의 같은 위치로 옮기세요.

### 연결과 인증

`config/redis/settings.json`의 기본값은 포트 6379, DB 0, 표시 시간대 `Asia/Seoul`입니다. 연결 설정은 모든 프로젝트에 공통이고, 프로젝트별로 다른 것은 매핑 파일의 IP뿐입니다.

- **인증:** 비밀번호는 `REDISCLI_AUTH`, ACL 사용자 이름은 `HSC_REDIS_USERNAME` 환경 변수에서 읽습니다. 변수 이름은 `password_env`·`username_env`로 바꿀 수 있습니다. 비밀번호를 설정 JSON에 넣지 마세요. `setup.ps1`에서 입력하거나 `-RedisPassword`·`-RedisUsername`으로 넘기면 시스템 변수로 등록합니다.
- **TLS:** `tls: true`와 `ca_file`로 켭니다. 상대 CA 경로는 `config/redis/` 기준이고, 인증서와 호스트 검증은 그대로 유지합니다.

## 도구

| 도구 (`build_center_` 뒤 이름) | 용도 |
| --- | --- |
| `list_projects` | 등록된 프로젝트 이름과 서버 IP(`servers` 맵). Redis에 접속하지 않습니다. |
| `find_modules` | 프로젝트의 모듈을 이름·경로·담당자 이름/ID로 검색 |
| `resolve_owner` | 담당자 ID ↔ 한글 이름. `project_name`을 주면 Redis 메타데이터도 확인하고, 생략하면 매핑만 봅니다. |
| `get_results` | 모듈 1~100개의 빌드·동적·정적 결과를 한 번에 조회 |
| `get_log` | 모듈 하나의 작업 로그 하나를 조회 |

"ProjectA에서 홍길동 담당 모듈 중 정적시험 실패한 것과 로그 보여줘"는 `find_modules` → `get_results` → `get_log` 순서로 처리합니다.

### 모듈과 담당자 검색

- 담당자는 `itemid.owner` 기준입니다. 다른 참여자나 과거 참여 이력은 추측하지 않습니다.
- 검색 필터는 대소문자를 무시한 부분 일치이고, 여러 개를 주면 모두 만족해야 합니다(AND).
- 이름이 같은 모듈은 경로와 module ID로 구분하고, 이후 조회에는 module ID를 씁니다.
- 담당자 표시 이름은 `owners.json` → Redis `owner_kr` → `owner` 순으로 고릅니다. 검색은 ID·표시 이름·Redis 원본 이름을 모두 봅니다. 동명이인은 owner ID별로 따로 돌려줍니다.

### 결과 읽는 법

작업 종류(`task`)는 `build`(빌드), `dynamic`(동적시험), `static`(정적시험)입니다. 결과 조회에서 생략하면 세 가지를 모두 읽습니다.

| 작업 | Redis 키 |
|---|---|
| 모듈 정보 | `itemid:` |
| 빌드 | `buildid:` |
| 동적시험 | `analysisid:` |
| 정적시험 | `analysisstaticid:` |

모든 값은 Redis String에 든 JSON 객체로 읽습니다.

- **돌려주는 필드:** `state`, `starttime`, `finishtime`, `checktime`, `meanbuildtime`, `builder`, `buildcount`만 돌려줍니다. 로그는 `get_log`로 따로 봅니다.
- **`state` 값:** 문자열 `"4"`는 성공, `"5"`는 실패, 그 밖의 값은 미확인입니다.
- **시각과 횟수:** 원본 값과 함께 Unix 초를 바꾼 시각, 계산한 소요 시간, 숫자로 바꾼 횟수를 줍니다.
- **추정한 필드:** `checktime`은 마지막 성공 시각, `meanbuildtime`은 소요 시간(초)으로 **추정**한 것입니다. 응답에도 가정이라고 표시합니다.
- **돌려주지 않는 것:** revision·버전·build_date는 돌려주지 않습니다. 키마다 저장된 최신 값일 뿐이라 실행 이력이나 세 작업을 같은 시점에 찍은 스냅샷이 아닙니다.

### 로그 페이지

- **기본값:** 마지막 100줄, 최대 12000자를 보여 줍니다.
- **줄 단위로 넘기기:** `offset`은 0부터 세는 줄 번호, `limit`은 줄 수입니다. 이전·다음 페이지는 응답의 `previous_offset`·`next_offset`을 씁니다.
- **글자 단위로 넘기기:** 긴 줄 때문에 글자가 잘리면 같은 `offset`·`limit`에 응답의 `previous_character_offset`·`next_character_offset`을 `character_offset`으로 넘깁니다. 위치는 그 줄 페이지 안의 Python 유니코드 문자 단위입니다.
- 로그가 갱신되면 같은 페이지라도 내용이 바뀔 수 있습니다.

## 오류와 조회 비용

- **일부 실패:** 키 누락(`missing`), JSON 손상(`invalid_json`), 로그 누락·타입 오류는 해당 모듈·작업에만 표시하고 정상 결과는 함께 돌려줍니다.
- **서버 시작 실패:** Kilo 화면 하단의 MCP 상태(`/status`)나 `kilo mcp list`에서 확인합니다. 자세한 내용은 `kilo --print-logs`로 봅니다.
- **연결 실패:** 접속·인증·TLS 실패는 MCP 오류로 돌려줍니다. 빈 결과나 성공으로 바꾸지 않습니다.
- **설정 오류:** 잘못된 매핑·설정은 파일 이름을 넣은 오류로 돌려줍니다.

Redis 부하를 줄이는 방식:

- **키 탐색:** `KEYS *` 대신 `SCAN MATCH itemid:*`를 씁니다. 중복 키를 걸러 내고, 빈 페이지가 와도 커서가 0이 될 때까지 계속합니다.
- **모듈 색인 캐시:** 기본 30초 동안 메모리에 둡니다. `refresh: true`로 새로 읽습니다. 한도를 넘으면 불완전한 색인을 성공으로 돌려주지 않습니다.
- **결과·로그:** 캐시하지 않고 요청마다 읽습니다. `batch_size` 기본값이 100이라 모듈 100개×키 4개는 MGET 4번입니다.
- **한도:** `max_scan_keys`·`max_scan_seconds`·소켓 타임아웃·연결 수에 한도가 있습니다.
- **재시도:** 네트워크 오류는 자동으로 재시도하지 않고, 다음 요청에서 다시 연결합니다.
- **동시 호출:** 서버 안에서 순서대로 처리해 설정 변경과 캐시 갱신이 부딪히지 않게 합니다. 느린 호출이 뒤 요청을 기다리게 할 수 있어서 타임아웃을 둡니다.

로그가 결과와 같은 Redis String에 들어 있어서, 결과 응답에서 로그를 빼도 네트워크로는 JSON 전체를 받습니다. 로그가 크면 `batch_size`를 줄여 메모리 사용을 조절하세요. Redis Cluster의 다중 슬롯 조회는 아직 지원하지 않습니다.

## 개발 메모

- MCP 클라이언트는 Kilo에 내장된 것을 씁니다. 이 폴더에는 서버만 둡니다.
- Python 패키지는 CI가 `config/redis/requirements.lock`의 버전·해시로 Windows wheel을 준비합니다. 대상 PC에서는 설치하지 않습니다.
