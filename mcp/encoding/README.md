# 인코딩 보존 MCP

CP949·EUC-KR·UTF-16·BOM 파일을 원래 인코딩 그대로 읽고 고치는 동봉 MCP 서버입니다. 동봉 Python 표준 라이브러리와 빌드센터 MCP와 같은 `mcp` 패키지만 사용하며, npm·확장은 필요 없습니다. Kilo 설정의 서버 이름은 `encoding`이고, 모델에는 `encoding_read`·`encoding_edit`·`encoding_write`로 보입니다.

- **실행:** `<배포 폴더>\runtime\python\python.exe -I -X utf8 -B -m encoding_mcp`. 항목은 `setup.ps1`이 [config/kilo.template.json](../../config/kilo.template.json)에서 만듭니다.
- **범위:** Kilo가 서버를 시작한 프로젝트 폴더(`kilo`를 실행한 폴더) 안의 파일만 다룹니다. 폴더 밖 파일은 거부하므로 내장 도구로 처리하며, 이때는 승인을 요청합니다.
- **승인:** `encoding_read`는 승인 없이 실행합니다. `encoding_edit`·`encoding_write`와 Kilo 내장 `edit`·`write`·`apply_patch`는 실행 전에 승인을 요청합니다. `kilo.jsonc`의 `permission`에서 바꿀 수 있습니다.

## 인코딩 판별

1. 프로젝트 폴더의 `encoding-rules.json` 규칙
2. UTF-8·UTF-16 BOM
3. 올바른 UTF-8
4. 올바른 CP949

규칙과 BOM이 충돌하거나, 위 방식으로 손실 없이 해석되지 않으면 읽기·쓰기를 거부합니다. 추측해서 고치지 않습니다. CP949는 UTF-8로 해석되지 않으므로, Kilo 내장 판별기가 틀리기 쉬운 짧은 한글 CP949 파일도 CP949로 읽습니다.

한글이 없는 ASCII 파일은 UTF-8과 CP949의 바이트가 같아서 UTF-8로 판별합니다. 이런 파일에 처음 한글을 넣거나 새 파일을 만들 때 CP949를 써야 한다면 규칙을 두세요. 규칙이 없으면 새 파일은 BOM 없는 UTF-8로 만듭니다.

```json
{
  "rules": [
    { "pattern": "legacy/**/*.cpp", "encoding": "cp949" },
    { "pattern": "legacy/**/*.h", "encoding": "cp949" },
    { "pattern": "resources/**/*.rc", "encoding": "utf-16-le" }
  ]
}
```

- 경로는 프로젝트 폴더 기준이며 `/`로 구분합니다. `*`는 경로 한 단계, `**`는 여러 단계와 일치하고, 대소문자를 구분합니다. 여러 규칙과 일치하면 마지막 규칙을 적용합니다.
- 지원 인코딩: `utf-8`, `cp949`, `euc-kr`, `utf-16-le`, `utf-16-be`. EUC-KR은 확장 한글(예: `똠`)을 담지 못하므로 CP949와 구분합니다.

## 저장 방식

- 원래 인코딩·BOM·줄바꿈(CRLF/LF)·권한 비트를 유지합니다. 줄바꿈이 섞인 파일에서 여러 줄을 바꾸는 작업은 거부합니다.
- CP949에 없는 이모지 같은 문자를 `?`로 바꾸지 않고 거부합니다.
- `old_string`이 없거나 여러 곳과 일치하면 거부합니다. 여러 곳을 바꾸려면 `replace_all`을 사용합니다.
- 같은 폴더의 임시 파일(`.kilo-kit-*`)에 저장한 뒤 원본을 교체합니다. 교체 직전에 원본이 바뀌었으면 쓰지 않습니다. 프로세스가 강제 종료되면 임시 파일이 남을 수 있으며, 자동으로 지우지 않습니다.
- 파일 한도는 8 MiB입니다. 읽기는 한 번에 최대 2000줄, 줄당 2000자까지입니다. symlink·hardlink·바이너리·UTF-32 파일은 지원하지 않습니다.

## 한계

- 모델이 이 도구 대신 내장 도구나 셸로 파일을 쓸 수도 있습니다. 내장 편집은 승인 단계에서 거절하고 `encoding_edit`를 쓰도록 지시하세요.
- 비 UTF-8 파일에서 한글을 검색하려면 `rg -E euc-kr`처럼 인코딩을 지정해야 합니다. ripgrep의 `euc-kr`는 CP949 확장 한글도 포함합니다.
- Visual Studio 같은 외부 편집기와 같은 파일을 동시에 쓰는 것을 막지는 못합니다.
