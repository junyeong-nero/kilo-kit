# kilo-kit

폐쇄망 Windows PC에서 사내 AI 모델로 [Kilo CLI](https://github.com/Kilo-Org/kilocode)(`kilo.exe`)를 사용할 수 있도록 필요한 파일을 모은 배포본입니다. 대상 PC에서 인터넷으로 파일을 받거나 Node.js·Python을 따로 설치할 필요는 없습니다.

## 설치

**[최신 배포 ZIP 다운로드](https://github.com/junyeong-nero/kilo-kit/releases/latest/download/kilo-kit-win-x64.zip)** — GitHub의 **Download ZIP**·**Source code (zip)**은 소스 코드만 담고 있어 실행할 수 없습니다.

1. ZIP을 폐쇄망 PC로 옮겨 원하는 폴더에 압축을 풉니다. 압축을 푼 폴더가 그대로 설치 위치가 되며, 나중에 옮기면 `setup.ps1`을 다시 실행해야 합니다.
2. PowerShell에서 실행합니다. 관리자 권한 확인 창이 뜨면 **예**를 누릅니다.
   ```powershell
   cd <압축을 푼 폴더>   # 예: cd C:\tools\kilo-kit
   Set-ExecutionPolicy -Scope Process Bypass -Force
   .\setup.ps1
   ```
3. 사내 API 주소(예: `http://10.0.0.1:8000/v1`)와 API 키를 입력하고, 모델이 여러 개면 기본 모델을 고릅니다.
4. 터미널을 완전히 닫았다가 다시 열면 어느 폴더에서든 `kilo`를 실행할 수 있습니다.

셋업 옵션, 설정 파일 위치, 이미지 입력, 문제 해결은 [설치와 설정](docs/installation.md)을 참고하세요.

## MCP

셋업이 다음 MCP를 Kilo에 자동 등록합니다. 모두 동봉된 Python으로 실행됩니다.

| MCP | 기능 |
|---|---|
| [빌드센터](mcp/build-center/README.md) | 빌드센터 Redis에서 프로젝트·모듈·담당자별 빌드·시험 결과와 로그를 조회합니다. |
| [인코딩 보존](mcp/encoding/README.md) | CP949·EUC-KR·UTF-16·BOM 파일을 인코딩과 줄바꿈을 유지한 채 읽고 고칩니다. |
| [Word VBA](mcp/word-vba/README.md) | Word에 열어 둔 문서에 VBA를 실행해 읽기·검색·편집합니다(Word 필요). 실행은 승인 후 합니다. |
| [Windows](mcp/windows/README.md) | Windows 앱의 UI 조회·클릭·입력을 제공합니다. 모든 도구가 승인을 요청합니다. |

## 더 보기

- [설치와 설정](docs/installation.md) — 셋업이 바꾸는 항목, 옵션, 문제 해결, OpenCode에서 복구
- [배포본 관리](docs/release.md) — GitHub Actions 패키징, 고정 버전, 설정 원본
- [구성요소 버전과 라이선스](third_party/README.md)
