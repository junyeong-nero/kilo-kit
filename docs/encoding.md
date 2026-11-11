# 인코딩 보존 편집

OpenCode 1.19.5의 기본 파일 도구는 UTF-8을 전제로 합니다. 이 kit는 본체를 수정하지 않고 `read/edit/write`를 custom tool로 교체합니다. 도구는 동봉 Python으로 바이트를 읽고, 명시적 인코딩으로 해석한 뒤 메모리에서 수정합니다. **원본 파일을 임시 UTF-8로 변환하지 않습니다.**

## 규칙 파일

Git 프로젝트는 worktree 루트, Git이 아닌 프로젝트(SVN 포함)는 OpenCode를 실행한 폴더에 `encoding-rules.json`을 둡니다.

```json
{
  "rules": [
    { "pattern": "legacy/**/*.cpp", "encoding": "cp949" },
    { "pattern": "legacy/**/*.h", "encoding": "cp949" },
    { "pattern": "resources/**/*.rc", "encoding": "utf-16-le" },
    { "pattern": "legacy/new-module/**", "encoding": "utf-8" }
  ]
}
```

이것은 예시이지 모든 `.rc`가 UTF-16이라는 뜻은 아닙니다. 실제 파일을 Visual Studio 등에서 확인하고 설정하세요. CP949와 EUC-KR은 구분합니다.

- 경로는 루트 기준 `/` 구분자. `*`는 한 경로 구성요소, `**`는 여러 디렉터리, `?`·`[]`도 지원합니다. 대소문자를 구분합니다.
- 여러 규칙에 해당하면 마지막 규칙이 우선합니다. `*.cpp`는 루트 파일만, `**/*.cpp`는 하위 폴더도 포함합니다.
- 지원 인코딩: `utf-8`, `cp949`, `euc-kr`, `utf-16-le`, `utf-16-be`.
- 규칙이 있으면 그것을 사용합니다. BOM과 충돌하면 거부합니다.
- 규칙이 없으면 UTF-8/UTF-16 BOM을 확인하고, BOM도 없으면 유효한 UTF-8만 허용합니다. 나머지는 설정을 요구하며 쓰지 않습니다.
- 새 파일은 규칙의 인코딩, 없으면 BOM 없는 UTF-8입니다. 새 UTF-16 파일도 규칙만으로 BOM을 새로 추가하지 않습니다.
- 프로젝트 밖 파일에 프로젝트 인코딩 규칙을 적용하지 않습니다.

## 도구와 승인

- 모델은 보통 `read/edit/write`를 그대로 호출합니다.
- 일부 모델에서 OpenCode가 기본 edit/write 대신 apply_patch를 선택하므로 `encoding_read/encoding_edit/encoding_write` 별칭도 항상 제공합니다.
- `apply_patch`는 설정과 플러그인 hook에서 차단합니다. `encoding_edit` 또는 `encoding_write`로 작업합니다.
- 읽기 정책(`.env` 등)과 외부 경로 승인을 먼저 확인하고, 쓰기 전에 `edit` 권한으로 diff 승인을 요청합니다. 사용자의 별도 권한 설정에 따라 승인 방식은 달라질 수 있습니다.
- 승인 중 파일이 바뀌면 해시 비교로 중단합니다. 치환 문자열이 없거나 여러 번 나타나면 중단하고, 여러 곳을 바꾸려면 `replaceAll: true`가 필요합니다.
- 저장은 같은 폴더의 임시 파일에 완성한 원래 인코딩 바이트를 쓴 뒤 교체합니다. CP949에 없는 이모지 등을 `?`로 바꾸지 않고 거부합니다.
- 기존 BOM·일관된 줄바꿈·파일 권한 비트를 보존합니다. 혼합 줄바꿈 파일의 여러 줄 변경/전체 쓰기는 거부합니다. Windows ACL·대체 데이터 스트림 등 모든 메타데이터 보존을 보장하지 않습니다.

## 읽기와 검색의 범위

custom `read`는 텍스트와 디렉터리 목록을 지원합니다. 읽기는 기본/최대 2000줄, 줄당 2000자로 제한합니다. 파일 크기 한도는 8 MiB입니다. 이미지·PDF·Word 같은 바이너리 파일은 지원하지 않습니다. Word와 UI 스크린샷은 해당 MCP를 사용하세요.

기본 grep/ripgrep은 교체하지 않습니다. 비 UTF-8 파일에서 한글 검색이 실패하거나 잘못 보이면 인코딩을 보존하는 read로 범위를 좁혀 확인하세요. grep 결과만으로 문자열이 없다고 단정하지 않습니다. 셸에서 변환해서 파일에 덮어쓰지 마세요.

## 실패·동시 편집

- 저장 중 kit 도구끼리의 충돌을 막기 위해 `<파일명>.opencode-kit.lock`을 잠시 만듭니다. 정상 종료·일반 예외 시 정리합니다.
- 프로세스 강제 종료로 lock/`.opencode-kit-*` 임시 파일이 남으면 자동으로 삭제하거나 복구하지 않습니다. 실행 중인 편집이 없는지, 원본과 Git/SVN diff를 확인한 뒤 사람이 정리합니다.
- 외부 IDE는 이 lock을 따르지 않습니다. 저장 직전에도 해시를 확인하지만, Visual Studio와 AI가 같은 파일을 동시에 쓰는 것을 완전히 차단하는 샌드박스는 아닙니다. 같은 파일의 동시 편집을 피하세요.
- symlink·hardlink 파일은 지원하지 않습니다.
- custom tools를 제거하거나 다른 플러그인으로 덮어쓰면 보호가 사라집니다. 셸·별도 MCP의 쓰기도 이 보호 범위 밖입니다.

## 검증

```powershell
python -B -m unittest discover -s tests -p "test_*.py" -v
node --test tests/encoding-tools.test.mjs
```

위 명령은 개발/CI용입니다. 사용자 PC에서는 Python/Node 설치가 필요 없습니다. CI가 npm lock으로 개발 의존성을 준비합니다.

테스트는 CP949 확장 한글·EUC-KR·UTF-8 BOM·UTF-16LE/BE·CRLF, 표현 불가능한 문자, 모호한 치환, 승인 거절, 승인 중 변경, 교체 실패, 비 Git 프로젝트, 외부 경로 승인을 다룹니다. 실제 MFC 프로젝트는 복사본에서 변경 후 바이트·Git/SVN diff·빌드 결과를 추가 확인하세요.
