# third_party

배포 ZIP에 들어가는 외부 구성요소입니다. URL·버전·원본 해시는 [`config/offline-artifacts.lock.json`](../config/offline-artifacts.lock.json)에, Python 패키지는 [`config/redis/requirements.lock`](../config/redis/requirements.lock), [`config/word/requirements.lock`](../config/word/requirements.lock), [`config/windows/requirements.lock`](../config/windows/requirements.lock)에 고정합니다. GitHub Actions가 해시를 확인한 뒤 ZIP에 넣으며 실행 파일은 소스 저장소에 넣지 않습니다.

| 배포 경로 | 버전 | 출처 | 라이선스 |
|---|---|---|---|
| `bin/opencode/` | OpenCode CLI 1.19.5 Windows x64 (`opencode.exe`) | [anomalyco/opencode release](https://github.com/anomalyco/opencode/releases/tag/v1.19.5) | MIT ([`opencode/LICENSE`](opencode/LICENSE)) |
| `runtime/opencode-tools/node_modules/` | @opencode-ai/plugin 1.19.5 및 고정 의존성 | [package-lock](../tools/encoding/package-lock.json) | 각 패키지의 LICENSE·package.json을 보존. CI가 lock을 `opencode/tools-package-lock.json`에도 복사 |
| `runtime/python/` | CPython 3.13.16 embeddable + mcp·redis·tzdata 등 | [python.org](https://www.python.org/ftp/python/3.13.16/) | PSF 및 각 패키지 라이선스 ([`python/NOTICE.md`](python/NOTICE.md)) |
| `runtime/word-mcp/` | word-mcp-live 1.6.21 + fastmcp·mcp 2·python-docx·pywin32 등 | [ykarapazar/word-mcp-live](https://github.com/ykarapazar/word-mcp-live) | MIT 및 각 패키지 라이선스 ([`python/NOTICE.md`](python/NOTICE.md)) |
| `runtime/windows-mcp/` | windows-mcp 0.8.5 + FastMCP 3·UIA·캡처 의존성 (Python 3.13 호환) | [CursorTouch/Windows-MCP](https://github.com/CursorTouch/Windows-MCP) | MIT 및 각 패키지 라이선스 ([`python/NOTICE.md`](python/NOTICE.md)) |
| `bin/rg.exe` | ripgrep 15.2.0 | [BurntSushi/ripgrep](https://github.com/BurntSushi/ripgrep/releases/tag/15.2.0) | MIT / Unlicense ([`ripgrep/`](ripgrep/)) |
| `bin/fd.exe` | fd 10.5.0 | [sharkdp/fd](https://github.com/sharkdp/fd/releases/tag/v10.5.0) | MIT / Apache-2.0 ([`fd/`](fd/)) |

`setup.ps1`은 `bin/rg.exe`를 OpenCode 캐시(`%USERPROFILE%\.cache\opencode\bin\rg.exe`)에도 복사합니다. OpenCode는 PATH의 rg를 우선 사용하고, 없으면 캐시·다운로드로 넘어가므로 둘 다 준비합니다.
