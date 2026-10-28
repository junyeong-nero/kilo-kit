# third_party

배포 ZIP에 들어가는 외부 구성요소입니다. URL·버전·원본 해시는 [`config/offline-artifacts.lock.json`](../config/offline-artifacts.lock.json)에, Python 패키지는 [`config/redis/requirements.lock`](../config/redis/requirements.lock)에 고정합니다. GitHub Actions가 해시를 확인한 뒤 ZIP에 넣으며 실행 파일은 소스 저장소에 넣지 않습니다.

| 배포 경로 | 버전 | 출처 | 라이선스 |
|---|---|---|---|
| `bin/kilo/` | Kilo CLI 7.8.18 Windows x64 (공식 ZIP 전체: `kilo.exe`, tree-sitter WASM, console 리소스) | [Kilo-Org/kilocode release](https://github.com/Kilo-Org/kilocode/releases/tag/v7.8.18) | MIT ([`kilo/LICENSE`](kilo/LICENSE)) |
| `runtime/python/` | CPython 3.13.16 embeddable + mcp·redis·tzdata 등 | [python.org](https://www.python.org/ftp/python/3.13.16/) | PSF 및 각 패키지 라이선스 ([`python/NOTICE.md`](python/NOTICE.md)) |
| `bin/rg.exe` | ripgrep 15.2.0 | [BurntSushi/ripgrep](https://github.com/BurntSushi/ripgrep/releases/tag/15.2.0) | MIT / Unlicense ([`ripgrep/`](ripgrep/)) |
| `bin/fd.exe` | fd 10.5.0 | [sharkdp/fd](https://github.com/sharkdp/fd/releases/tag/v10.5.0) | MIT / Apache-2.0 ([`fd/`](fd/)) |

`setup.ps1`은 `bin/rg.exe`를 Kilo 캐시(`%USERPROFILE%\.cache\kilo\bin\rg.exe`)에도 복사합니다. Kilo가 Windows에서 PATH의 rg를 쓰지 않고 인터넷에서 받으려 하기 때문입니다.
