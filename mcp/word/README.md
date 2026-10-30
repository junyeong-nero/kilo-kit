# Word MCP

[word-mcp-live](https://github.com/ykarapazar/word-mcp-live) 1.6.21(MIT)을 Kilo에서 쓰도록 동봉한 MCP 서버입니다. Kilo 설정(`%USERPROFILE%\.config\kilo\kilo.json`)의 서버 이름은 `word`이고, 모델에는 `word_<도구>` 이름으로 보입니다.

- **실행:** `<배포 폴더>\runtime\python\python.exe -I -X utf8 -B -m word_mcp`를 절대 경로로 실행합니다. 항목은 `setup.ps1`이 [config/kilo.template.json](../../config/kilo.template.json)에서 만듭니다.
- **패키지 위치:** word-mcp-live는 fastmcp 4를 통해 mcp 2가 필요하고 빌드센터 MCP는 mcp 1을 씁니다. 그래서 Word용 패키지는 [config/word/requirements.lock](../../config/word/requirements.lock)으로 `runtime\word-mcp\`에 따로 설치합니다. [word_mcp.py](word_mcp.py)가 이 폴더만 모듈 경로에 두고 서버를 시작합니다.
- **외부 통신:** 서버는 stdio로만 실행합니다. 런처가 `MCP_TRANSPORT=stdio`, `FASTMCP_CHECK_FOR_UPDATES=off`를 고정하므로 프로젝트 폴더의 `.env`가 있어도 네트워크 포트를 열거나 업데이트를 확인하지 않습니다.
- **변경 추적 작성자:** 변경 내용 추적과 메모의 작성자는 Windows 사용자 이름(`%USERNAME%`)입니다. 다른 이름을 쓰려면 시스템 또는 사용자 환경 변수 `MCP_AUTHOR`(이니셜은 `MCP_AUTHOR_INITIALS`)를 지정하세요.

## 열린 문서 전용

word-mcp-live의 도구 중 실행 중인 Word에 COM(pywin32)으로 붙는 `word_live_*` 44개와 Word 창을 캡처하는 `word_screen_capture`만 켭니다(`word_word_live_*`, `word_word_screen_capture`로 보입니다). 이 도구들은 Word에 열린 문서만 찾고, 열려 있지 않으면 `is not open in Word` 오류를 냅니다. Word를 직접 띄우거나 닫힌 파일을 열지 않습니다. 변경은 화면에 바로 보이고 Word에서 `Ctrl+Z`로 되돌릴 수 있습니다.

python-docx로 `.docx` 파일을 직접 읽고 쓰는 나머지 도구(`get_document_text`, `add_table`, `create_document` 등)는 [word_mcp.py](word_mcp.py)가 서버 시작 때 `disable`로 숨깁니다. 모델 도구 목록에 나타나지 않고 이름으로 불러도 `Unknown tool`로 거절됩니다.

## 승인

읽기 전용 도구 15개(`word_live_get_*`, `word_live_find_text`, `word_live_list_*`, `word_screen_capture` 등 서버가 `readOnlyHint`로 표시한 것)는 승인 없이 실행하고, 문서를 바꾸는 나머지 도구는 실행 전에 승인을 요청합니다. 규칙은 `kilo.jsonc`의 `permission`에서 바꿀 수 있습니다.

## 큰 문서

- `word_live_get_text`는 문단이 200개를 넘으면 처음 3페이지만 돌려줍니다. `word_live_find_text`로 위치를 찾고 `word_live_get_page_text`로 페이지 범위를 지정해 읽습니다. 동봉한 `AGENTS.md`도 모델에 이렇게 안내합니다.
- 페이지 계산은 Word가 하므로 큰 문서에서는 느릴 수 있습니다. Word의 **보기 > 초안**으로 두면 화면을 그리는 부담이 줄어듭니다.
