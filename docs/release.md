# 배포본 관리

GitHub Actions(`.github/workflows/offline.yml`)가 [고정된 버전과 해시](../config/offline-artifacts.lock.json)를 기준으로 Kilo·Python·rg·fd를 받고, 모든 MCP가 함께 쓰는 [lock 파일](../config/redis/requirements.lock)에 지정된 Python 패키지를 설치해 ZIP을 만듭니다. `v*` 태그를 푸시하면 Releases에 게시합니다.

- Kilo 설정 원본: [config/kilo.template.json](../config/kilo.template.json)
- 모델에 전달하는 도구 사용 규칙: [config/AGENTS.md](../config/AGENTS.md)
- [구성요소 버전과 라이선스](../third_party/README.md)
