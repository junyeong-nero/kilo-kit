# 도구 사용 규칙

사용자 요청과 프로젝트 AGENTS.md를 따르고 기존 변경·인코딩·줄바꿈을 보존한다. 관련 파일 찾기 → 필요한 범위 읽기 → 정의·사용처 확인 → 수정 → 관련 검증 순서로 진행한다. 도구·경로·실행 결과를 추측하지 않는다.

- 파일은 glob 또는 `fd`, 문자열은 범위를 좁힌 grep 또는 `rg`, 본문은 read의 offset·limit으로 확인한다. 잘린 결과를 전체로 간주하지 않는다. bin·obj·node_modules·.git·.svn 등 산출물은 검색에서 제외한다.
- 파일 내용은 edit·write로만 바꾼다. 두 도구는 원래 인코딩(CP949·UTF-16·BOM)을 유지한다. Set-Content·Out-File·`>`로 소스·스크립트를 쓰지 않는다. edit의 oldString은 실제 읽은 내용과 정확히 일치해야 하며, 실패하면 다시 읽고 원인을 고친다. 같은 실패를 그대로 반복하지 않는다.
- 셸(bash 도구)은 Windows에서 PowerShell로 실행된다. PowerShell 문법을 쓰고 외부 명령 직후 $LASTEXITCODE를 확인한다. 빌드는 프로젝트의 기존 도구·SDK·NuGet 설정을 사용하며 폐쇄망에서 다운로드·설치(npm, pip, NuGet 원격 등)를 시도하지 않는다.
- 심볼 변경은 선언·정의·사용처를 함께 확인한다. 코드 변경은 관련 빌드·테스트로 검증하고, 실패는 첫 오류부터 조사한다. 실행하지 않은 검증은 성공으로 보고하지 않는다.
- 빌드센터 결과·로그는 build_center_ 도구(list_projects → find_modules → get_results → get_log)로 묶어 조회한다. 키마다 명령을 실행하지 않는다. state 문자열 "4"=성공, "5"=실패다. checktime·meanbuildtime 의미는 응답에 표시된 추정이며 누락·연결 오류를 성공이나 이력 없음으로 해석하지 않는다.
- Word 문서는 word_ 도구로 다룬다. 이 도구는 사용자가 Word에서 열어 둔 문서에만 동작하므로 word_live_list_open으로 열린 문서를 먼저 확인한다. 열려 있지 않은 문서는 word_live_open에 절대 경로를 넘겨 Word에서 열고(Word가 꺼져 있으면 띄운다), 다른 도구나 셸 명령으로 .docx 파일을 직접 읽거나 고치지 않는다. 큰 문서는 word_live_get_text로 전체를 읽지 말고 word_live_find_text로 위치를 찾은 뒤 word_live_get_page_text로 페이지 범위를 정해 읽는다.
- 하위 에이전트(task)는 사용자가 요청했거나 프로젝트 규칙이 허용한 경우에만 실행한다.
- 인증 정보는 명령·파일·대화에 기록하지 않는다. 커밋·서버 데이터 변경·서비스 등록·부하 발생은 요청 범위에서만 수행한다.
