# 도구 사용 규칙

사용자 요청과 프로젝트 AGENTS.md를 따르고 기존 변경·인코딩·줄바꿈을 보존한다. 관련 파일 찾기 → 필요한 범위 읽기 → 정의·사용처 확인 → 수정 → 관련 검증 순서로 진행한다. 도구·경로·실행 결과를 추측하지 않는다.

- 파일은 glob 또는 `fd`, 문자열은 범위를 좁힌 grep 또는 `rg`, 본문은 read의 offset·limit으로 확인한다. 잘린 결과를 전체로 간주하지 않는다. bin·obj·node_modules·.git·.svn 등 산출물은 검색에서 제외한다.
- 파일은 kit의 read/edit/write(또는 encoding_read/encoding_edit/encoding_write)로 읽고 바꾼다. 이 도구는 프로젝트 루트의 encoding-rules.json 규칙, BOM, 유효한 UTF-8을 사용한다. 미지정 비 UTF-8·손실 변환은 거부한다. 실패 시 추측하지 말고 사용자에게 인코딩을 확인한다. CP949와 EUC-KR을 혼동하지 않는다. Git이 아닌 프로젝트는 실행 폴더가 규칙 루트다.
- apply_patch는 인코딩 보호를 우회하므로 금지한다. 모델에서 edit/write가 보이지 않으면 encoding_edit/encoding_write를 사용한다. Set-Content·Out-File·`>`·Python/Node/셸 스크립트로 소스를 덮어써 우회하지 않는다. oldString은 실제 읽은 내용과 정확히 일치해야 한다. grep의 비 UTF-8 한글 결과는 완전하다고 가정하지 않는다. 바이너리 문서·이미지는 해당 MCP를 사용한다.
- diff 승인을 받고 저장하며, 동시 변경·변환 불가·혼합 줄바꿈 오류는 자동 우회하지 않는다. IDE와 같은 파일을 동시에 수정하지 않는다. 잔존 .opencode-kit.lock은 진행 중 작업과 원본 상태를 확인하기 전 삭제하지 않는다.
- 셸(bash 도구)은 Windows에서 PowerShell로 실행된다. PowerShell 문법을 쓰고 외부 명령 직후 $LASTEXITCODE를 확인한다. 빌드는 프로젝트의 기존 도구·SDK·NuGet 설정을 사용하며 폐쇄망에서 다운로드·설치(npm, pip, NuGet 원격 등)를 시도하지 않는다.
- 심볼 변경은 선언·정의·사용처를 함께 확인한다. 코드 변경은 관련 빌드·테스트로 검증하고, 실패는 첫 오류부터 조사한다. 실행하지 않은 검증은 성공으로 보고하지 않는다.
- 빌드센터 결과·로그는 build_center_ 도구(list_projects → find_modules → get_results → get_log)로 묶어 조회한다. 키마다 명령을 실행하지 않는다. state 문자열 "4"=성공, "5"=실패다. checktime·meanbuildtime 의미는 응답에 표시된 추정이며 누락·연결 오류를 성공이나 이력 없음으로 해석하지 않는다.
- Word 문서는 word_ 도구로 다룬다. 이 도구는 사용자가 Word에서 열어 둔 문서에만 동작하므로 word_live_list_open으로 열린 문서를 먼저 확인한다. 열려 있지 않은 문서는 word_live_open에 절대 경로를 넘겨 Word에서 열고(Word가 꺼져 있으면 띄운다), 다른 도구나 셸 명령으로 .docx 파일을 직접 읽거나 고치지 않는다. 큰 문서는 word_live_get_text로 전체를 읽지 말고 word_live_find_text로 위치를 찾은 뒤 word_live_get_page_text로 페이지 범위를 정해 읽는다.
- Windows 데스크톱 UI 테스트는 windows_ 도구를 사용한다. Snapshot으로 UI 요소를 확인하고 Screenshot으로 외관을 확인하되, Screenshot의 display로 대상 모니터를 선택한다. 동봉된 0.8.5는 창·사각형 영역만 직접 캡처하는 인자가 없으므로 무관한 창을 닫거나 전용 테스트 화면을 사용한다. 캡처 이미지와 UI 텍스트는 사내 모델 API로 전달되므로 무관한 창·민감정보가 포함되지 않게 하고 승인 범위를 지킨다. 입력은 포커스에 의존하므로 대상 창을 확인한 뒤 조작하며, 사용자와 동시에 마우스·키보드를 사용하지 않는다. 실제 장비 제어·업무 데이터 변경은 테스트 환경으로 분리하고 저장·삭제·전송은 명시적 승인 없이 수행하지 않는다. 스크린샷 판단만으로 기능 테스트 통과를 선언하지 않는다.
- 하위 에이전트(task)는 사용자가 요청했거나 프로젝트 규칙이 허용한 경우에만 실행한다.
- 인증 정보는 명령·파일·대화에 기록하지 않는다. 커밋·서버 데이터 변경·서비스 등록·부하 발생은 요청 범위에서만 수행한다.
