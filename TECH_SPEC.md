# TECH_SPEC.md — agentview (1차 MVP 기술 설계)

개정: 1회차 2026-11-07 작성. 2회차 2026-11-09 — plan-review 2회차 지시(K1~K10, L1~L8, N1~N23, O) 반영,
SPEC 6회차(699줄) 기준으로 맞춤. 2회차에서 바뀐 곳은 본문에 `(2회차 Kn/Ln/Nn)` 꼬리표를 달았다.
3회차 2026-11-09 — 2차 좁힌 검토(#1~#14)와 사용자 결정 #9(컷 단위 = 메시지) 반영. SPEC 7회차 새 문구(지시서 기준)에 맞춤.
바뀐 곳은 `(3회차 #n)` 꼬리표.

입력: `SPEC.md`(6회차 확정, F1~F20, 부록 "TECH_SPEC 위임 목록"), `PLANNING.md`(0절, A5·A8·A11·A12,
B2·B6·B7, C1, G1~G11, H절), PM 입력 메모(2026-11-07), 트랜스크립트 구조 요약(`jsonl_schema.json`),
실제 트랜스크립트의 필드명 Grep, PokePet 정적 덤프(`pokepet_dump.json`), 크레딧 초안(`credits_draft.md`),
`RUN_LOG.md` 2026-11-07 훅 조사 요약. 이 문서는 SPEC의 범위를 넓히거나 줄이지 않는다. 기능 범위가
궁금하면 SPEC을, 구현 방식이 궁금하면 이 문서를 본다. 이 문서가 정한 수치는 `[기본값]`으로 표시하며,
모두 데이터 파일(F20)에 들어가므로 코드 수정 없이 바꿀 수 있다.

표기: `SPEC F1` = SPEC.md 3절의 F1. `M3` = 6절의 실측 필요 항목 3번. `C2` = 6절의 확인된 항목 2번.
`R4` = 5a 공유 규칙 4번.

---

## 1. 개요 (Overview)

agentview는 이 PC의 Claude Code 세션·하위 에이전트 활동을 읽어, 보컬로이드 캐릭터들이 기숙사 한 방(바탕화면
가로 띠)에서 일하고 기다리고 쉬는 모습으로 보여 주고, 세션이 쓴 토큰을 재화로 바꿔 꾸미기·충원·애정에
쓰게 하는 Windows 데스크톱 앱이다. 새 프로젝트라 기존 코드는 없지만, 앱이 의존하는 외부 구조는 모두 이미
존재한다. Claude Code가 남기는 트랜스크립트 JSONL의 레코드 형식, 훅 이벤트의 stdin 페이로드와
`~/.claude/settings.json`의 `hooks` 구조, 같은 창 형태를 PyQt5로 구현한 참고 앱 PokePet의 설계가 그것이다.
앱의 정확도(상태 6종 판정, 토큰 중복 없는 집계)와 안전성(사용자 설정 파일 병합, 본문 미열람)은 이 외부 구조를
정확히 따르는지에 달려 있으므로, 2절에서 실제로 읽은 구조를 먼저 정리하고 그 위에 설계를 쌓는다.

**기술 스택 판정: Python 3.12 + PySide6(Qt 6) 채택.** 근거: PokePet이 PyQt5로 투명·프레임 없음·항상 위·작업
표시줄 숨김(`FramelessWindowHint`·`WindowStaysOnTopHint`·`Tool`·`WA_TranslucentBackground`), 트레이
(`QSystemTrayIcon`), 단일 인스턴스(`QLockFile` "app.lock")를 같은 앱 안에서 함께 쓰고 있음을 덤프에서
확인했고(2.4절), PySide6는 같은 Qt API를 LGPL로 제공하며 Qt 6은 모니터별 DPI 인식이 기본이다. 훅 쓰기는
GUI와 분리한 표준 라이브러리 전용 소형 실행 파일로 만들어, 배포본에서 Python 인터프리터 없이 동작한다(4.F16).

---

## 2. 기존 코드 구조 분석 → 참고 자료 구조 분석 (Reference Structure Analysis)

기존 코드가 없으므로 앱이 읽거나 쓰는 외부 구조 4종을 분석한다. 모든 항목은 아래 "근거" 열의 자료를 실제로
읽은 결과다. 트랜스크립트는 필드명·타입·열거값·숫자만 확인했고 메시지·도구 입출력 본문은 열람·인용하지 않았다.

### 2.1 읽은 근거 자료 목록

| # | 자료 | 읽은 방식 | 확인한 것 |
|---|---|---|---|
| S1 | `scratchpad/jsonl_schema.json` | Read 전체 | 트랜스크립트 2개의 레코드 type 분포, type별 키, usage 키, stop_reason, content 블록 종류, subagents 경로 |
| S2 | `C:\Users\SSAFY\.claude\projects\C--Users-SSAFY-Desktop-borry-agentview-agentview\45526821-….jsonl` | Grep `-o`(필드명·숫자·열거값만) | message.id 반복, usage 반복, stop_reason, system subtype, toolDenialKind 값, interruptedMessageId 존재 |
| S3 | 같은 세션의 `subagents\agent-a156d7fb8f2775287.jsonl` | Grep `-o` | `agentId`, `isSidechain:true`, `entrypoint:"cli"`, `userType:"external"` |
| S4 | `C:\Users\SSAFY\.claude\settings.json` | Grep(최상위 키 이름만) | 최상위 키 `model`·`statusLine`·`enabledPlugins`·`extraKnownMarketplaces`·`modelSettings`·`remote`·`tui`·`theme`. `hooks` 키 없음 |
| S5 | `scratchpad/pokepet_dump.json` | Grep + Read(모듈 `pokepet.local_sessions` 106627~106952, `pokepet.monitor` 106954~107074, `pokepet.tokens` 130383~130695, `pokepet.pet` 110798~110917, `pokepet.game` 92711, 창 플래그·락 파일 위치) | 상태 추정 규칙, 토큰 집계 방식, 창 플래그, 단일 인스턴스, local.json 용도, 턴 경험치 상한 |
| S6 | `RUN_LOG.md` 194행 | Read | 훅 공식 문서 조사 요약(이벤트, 필드, 발화 조건, 미확인 항목) |
| S7 | `scratchpad/techspec_input.md` | Read | 범위, 확정 기술 방향, 훅 필드 목록 |
| S8 | `scratchpad/credits_draft.md` | Read | 크레딧·비공식 고지 문구(권리자 5그룹) |
| S9 | `SPEC.md` 1~689행(5회차), 6회차 변경 행(86~94, 167~172, 190, 390, 399, 467, 474~494, 503~528, 555, 566~579, 628~646) 재열람, `PLANNING.md` 1~64·91~120행 | Read/Grep | 범위·수용 기준·위임 목록 |

### 2.2 트랜스크립트 JSONL 구조 (근거 S1·S2·S3)

**경로**(S1 `_subagent_files_example`, S7):
- 메인: `<CLAUDE_ROOT>\projects\<슬러그>\<sessionId>.jsonl`. 슬러그는 cwd의 `:`·`\`를 `-`로 바꾼 것으로 보인다
  (실제 폴더명 `C--Users-SSAFY-Desktop-borry-agentview-agentview`). 앱은 슬러그를 계산하지 않고
  `projects\*\<sessionId>.jsonl`로 찾는다(슬러그 규칙 변경에 둔감하게).
- 하위 에이전트: `<sessionId>\subagents\agent-<agentId>.jsonl`. 레코드마다 `agentId`(예 `"a156d7fb8f2775287"`)와
  `isSidechain: true`가 있다(S3). 부모 세션 ID는 디렉터리 이름에서 얻는다.

**레코드 type 분포**(S1, 큰 파일 3650줄 기준): `assistant` 547, `user` 328, `attachment` 594, `system` 170,
`queue-operation` 212, `api-request` 185, `api-request-blob` 286, `mode`·`permission-mode`·`atis-latch`·
`bridge-session` 각 150, `last-prompt` 151, `ai-title` 149, `custom-title`·`agent-name` 148,
`file-history-snapshot` 109, `tools-used` 12, `file-history-delta` 5, `api-request-shape` 4, `cost-state` 2.
앱이 쓰는 것은 `assistant`·`user`·`system` 3종뿐이고 나머지는 type만 보고 건너뛴다.

**앱이 읽는 필드(허용 메타, SPEC F15)**:

| 레코드 | 필드 | 타입·예시 | 용도 |
|---|---|---|---|
| 공통 | `type` | `"assistant"`/`"user"`/`"system"` | 분기 |
| 공통 | `sessionId` | UUID 문자열 | 세션 식별(파일명과 교차 확인) |
| 공통 | `timestamp` | ISO-8601 문자열(`Z` 접미, PokePet `_ts`가 `Z`→`+00:00` 치환 후 `fromisoformat`, S5) | 토큰의 턴 귀속, 활동 시각 |
| 공통 | `cwd` | 경로 문자열 | 폴더명 오버레이·단골 판정(훅 이벤트가 없을 때의 보조) |
| 공통 | `isSidechain`, `agentId` | bool, 문자열 | 하위 에이전트 판정 |
| assistant | `message.id` | `"msg_011CgJw3K2U1qenN6rvSMXoc"` 형식 | 토큰 중복 제거 키 |
| assistant | `message.stop_reason` | `"tool_use"`(355) / `"end_turn"`(189) | 턴 경계 보조 신호 |
| assistant | `message.usage.input_tokens` 등 4키 | 정수 | 토큰 총량 |
| assistant | `message.content[].type`, `.name`, `.id` | `"tool_use"`, `"AskUserQuestion"`, 문자열 | "?" 판정(입력 `input`은 읽지 않음) |
| user | `message.content[].type`, `.tool_use_id` | `"tool_result"`, 문자열 | "?" 해제(결과 유무만) |
| user | `toolDenialKind` | 키 존재 여부만(관찰된 값 `"user-reject"`는 해석·저장하지 않음) | 거부 보조 신호(SPEC F15 6회차 허용, 2회차 K7) |
| user | `interruptedMessageId` | 키 존재 여부만(값 미저장) | 인터럽트 보조 신호(SPEC F15 6회차 허용, 2회차 K7) |
| user/assistant | `entrypoint` | 열거값(관찰 `"cli"`) | 헤드리스 여부 판별만(SPEC F15 6회차 허용). 값은 런타임 세션 속성으로만 두고 세이브·로그에 쓰지 않는다 |
| system | `subtype` | `"turn_duration"`, `"away_summary"`, `"compact_boundary"`, `"informational"` 등 | `turn_duration` = 턴 종료 보조 신호(PokePet도 같은 기준, S5 local_sessions 독스트링) |

**확인된 구조 사실**:
1. **같은 message.id가 여러 줄에 걸친다.** S2 448~452행이 같은 `msg_011CgJw3…`이고 모두 `stop_reason:"tool_use"`.
   content 블록마다 한 줄씩 쓰이는 형태다. PokePet `tokens` 독스트링도 "같은 메시지가 여러 줄로 나뉘어 있으므로
   메시지 id당 한 번"이라고 적는다(S5 130419).
2. **한 줄에 usage 4키가 두 번 나온다.** S2 29행 등에서 4키가 키 순서만 다르게 두 번 나타난다. usage 키 목록에
   `iterations`가 있으므로(S1) 두 번째는 중첩 객체 안의 값으로 판단한다. **파서는 `message.usage` 최상위의 4개
   정수만 읽어야 하고**, 문자열 검색이나 재귀 탐색으로 합산하면 두 배가 된다(R3).
3. 이번 표본에서는 같은 id의 여러 줄 usage가 모두 같았다(S2 29~31, 51~52, 67~69행 등). 그래도 "최종 usage 기준"
   규칙(SPEC F3)을 지키도록 id별 최대값 갱신 방식으로 구현한다(R3, M9).
4. usage에는 4키 말고도 `cache_creation`(세부 객체), `server_tool_use`, `service_tier`, `speed`,
   `inference_geo`, `fallback_credit`, `output_tokens_details`, `iterations`가 있다(S1). 총량에는 넣지 않는다.
5. `cost-state` 레코드에 `modelUsage`·`totalCostUSD`가 있지만 세션당 1~2개뿐이고 갱신 시점이 불명확하다. 토큰
   원천으로 쓰지 않는다.
6. `system.subtype:"compact_boundary"`가 있다. 컴팩션이 파일을 다시 쓰지 않고 경계 레코드를 덧붙이는 형태로 보인다
   (추가 전용 가정, M10).
7. 메인 파일 `user` 레코드에 `entrypoint`·`sessionKind`·`promptSource`·`origin` 키가 있다(S1). 자동화 세션도
   같은 위치·형식으로 기록되므로 앱은 이 키로 세션을 거르지 않는다(SPEC F1 "자동화 세션 동일 취급").

### 2.3 훅 페이로드와 settings.json 구조 (근거 S4·S6·S7)

**이벤트별 stdin 필드**(S6·S7. 공식 문서 요약을 신뢰하며 직접 실행해 보지는 않았다):

| 이벤트 | 앱이 쓰는 필드 | 앱이 쓰지 않거나 저장하지 않는 필드 | 비고 |
|---|---|---|---|
| 공통 | `session_id`, `cwd`, `hook_event_name`, `permission_mode` | `transcript_path`(경로를 다시 계산함), 그 외 | |
| `PermissionRequest` | `tool_name`, `agent_id`(하위일 때) | `tool_input`(**본문, 저장 금지**) | 프롬프트 직전에 발화. `tool_use_id` 없음 |
| `PostToolUse` / `PostToolUseFailure` | `tool_name`, `agent_id` | `tool_input`, `tool_response` | |
| `Stop` | — | `background_tasks` | 인터럽트 때는 발화하지 않는다(S6) |
| `SessionEnd` | — | `reason`(clear/resume/logout/prompt_input_exit/other) | 상태 결과는 reason과 무관(SPEC F1) |
| `SubagentStart` / `SubagentStop` | `agent_id` | `agent_transcript_path` | 경로는 2.2 규칙으로 계산 |
| `Notification` | 종류(idle_prompt) | 메시지 본문 | stdin 필드명은 확인 안 됨(M4) → 종류는 명령행 인자로 받는다(4.F16) |

- 하위 에이전트 안의 도구 호출에도 같은 훅이 `agent_id`와 함께 발화한다(S6).
- 관찰 전용 훅은 exit 0, stdout 없음. exit 0/2가 아닌 실패는 세션을 막지 않는다. `"async": true`를 쓸 수 있다(S6).
- `Notification` permission_prompt는 약 6초 늦게 온다(S6). 앱은 permission_prompt를 쓰지 않는다(`PermissionRequest`가 1차).

**settings.json 구조**(S4): 이 PC의 `~/.claude/settings.json`에는 최상위 키 8개가 있고 `hooks` 키는 없다.
따라서 설치는 "키 생성" 경로와 "기존 hooks 병합" 경로를 모두 지원해야 한다. 훅 설정 형태(공식 문서 형식, S6):

```json
"hooks": {
  "<이벤트명>": [
    { "matcher": "<선택>", "hooks": [ { "type": "command", "command": "<명령>", "async": true, "timeout": 10 } ] }
  ]
}
```

### 2.4 PokePet 설계 (근거 S5 — 참고만 하며 코드는 가져오지 않는다)

| 관찰 | 근거 위치(덤프 행) | agentview에 반영 |
|---|---|---|
| 훅 없이 트랜스크립트로 상태를 추정: 턴 종료 = `turn_duration`/`end_turn`, 질문 툴 결과 없음 = 입력 대기, 빠른 툴의 결과 지연 = 승인 대기 추정 | 106678 (local_sessions 독스트링) | 앱은 훅을 1차 원천으로 쓰고, 트랜스크립트의 turn_duration/end_turn은 보조 신호로만 쓴다. "?"는 PokePet과 같은 기준 |
| 상수 `STALE_WORKING_SECONDS` 등과 값 1800·10800·900 | 106638~106699 | 일하는 중 상태가 무한히 남지 않게 정체 판정을 둔다(C1) |
| 토큰: assistant usage를 메시지 id당 한 번, 파일별 오프셋(`offset`)과 마지막 줄바꿈(`rfind`)까지만 소비 | 130419, 130583~130613 | R3 중복 기준과 R4 오프셋 규칙 |
| usage 4키 이름 `input_tokens`·`cache_read_input_tokens`·`cache_creation_input_tokens`·`output_tokens` | 130681~130684 | 2.2와 일치 |
| 백그라운드 스레드에서 수집 | 107037 | 수집은 작업 스레드, 게임 상태는 메인 스레드(4.F17, 5c) |
| 창 플래그 `FramelessWindowHint`·`Tool`·`WA_TranslucentBackground`·`WindowStaysOnTopHint` | 111213~111221(pet), 80607~80616, 106168~106178 | 띠 창 플래그(4.F13) |
| `QSystemTrayIcon` | 6428, 7038 | 트레이 |
| 단일 인스턴스 `QLockFile` + `tryLock` + `"app.lock"` | 6419, 7499, 7572, 7603 | 단일 인스턴스(4.F14) |
| 자동 시작: 시작프로그램 폴더에 스크립트 | 8364 | 1차는 HKCU Run 키를 쓴다(4.F18). 어느 쪽이든 가능 |
| `local.json`에 탭/세션 연결, 폴더 단골 저장 | 92711 (game 독스트링) | 세이브의 `session_links`·`folder_regulars`(4.F14) |
| 턴 경험치 상한 160(그쪽 식: 10 + 작업분×5) | 92711 | 우리 식은 log2라 수치는 따로 정한다(4.F12) |
| `CLAUDE_CONFIG_DIR` 환경 변수 참조 | 106681, 107046 | C10(PM 확정: 기본 `~/.claude`만, 분기 자리만) |
| `NICKNAME_MAX` 상수 | 110828 | 개명 길이 상한은 데이터(R7) |

---

## 3. 기능 목록 (Feature List)

SPEC과 같은 ID·이름을 쓴다. 새 ID는 없다.

| ID | 기능 | 주 모듈(5c) |
|---|---|---|
| F1 | 세션·에이전트 감지와 상태 판별 | `ingest/events.py`, `ingest/transcripts.py`, `core/sessions.py`, `hook/*` |
| F2 | 세션↔캐릭터·호기 매핑 | `core/assign.py` |
| F3 | 토큰 총량→재화 | `ingest/transcripts.py`, `core/economy.py` |
| F4 | 캐릭터 | `core/roster.py`, `data/` |
| F5 | 충원 | `core/economy.py`, `core/roster.py` |
| F6 | 숙소 | `core/economy.py` |
| F7 | 꾸미기 | `core/economy.py`, `ui/shop.py` |
| F8 | 기분 | `core/characters.py` |
| F9 | 애정 | `core/characters.py`, `ui/menus.py` |
| F10 | 상호작용 추상 대화 | `core/chatter.py` |
| F11 | 연대기 | `core/chronicle.py` |
| F12 | 숙련 경험치 계산·저장 | `core/characters.py` |
| F13 | 띠 UI | `ui/*` |
| F14 | 세이브 | `save/store.py` |
| F15 | 프라이버시 | 전 모듈(R12) |
| F16 | 온보딩 | `ui/onboarding.py`, `hook/installer.py` |
| F17 | 유휴 성능 | `ingest/*`, `ui/band.py` |
| F18 | 앱 꺼짐 처리 | `core/catchup.py`, `platform/win.py` |
| F19 | 시간 흐름 | `core/clock.py` |
| F20 | 콘텐츠 데이터화 | `data/loader.py`, `data/default/*`, `schemas/*` |

---

## 4. 기능별 요구사항 및 기술 수용 기준 (Functional Requirements & Acceptance Criteria)

SPEC의 수용 기준은 모두 유효하며 여기서 반복하지 않는다. 아래는 SPEC을 구현 가능하게 만드는 **기술 결정과
기술 수용 기준**(TA)이다. 각 기능 끝의 "위임 답"은 SPEC 부록 항목에 대한 답이다.

### F1. 세션·에이전트 감지와 상태 판별

**원천과 역할 분담**:
- 1차 원천: 훅 이벤트 파일(`%LOCALAPPDATA%\agentview\events\events-YYYY-MM-DD.jsonl`, 형식은 R10).
- 보조 원천: 트랜스크립트. 쓰는 것은 (a) 토큰(F3) (b) AskUserQuestion의 결과 없는 tool_use → "?" (c) 새 활동
  (마지막 턴 종료 뒤의 새 assistant/user 레코드) (d) 턴 종료 보조 신호(`system.subtype=="turn_duration"`,
  `stop_reason=="end_turn"`, `interruptedMessageId` **키 존재**) (e) 거부 보조 신호(`toolDenialKind` **키 존재**)
  (f) 헤드리스 판별(`entrypoint` 열거값). (d)(e)는 SPEC F15 6회차에 따라 키가 있는지만 보고 값은 해석·저장하지
  않는다(2회차 K7).
- 훅 이벤트와 트랜스크립트 신호가 충돌하면 훅이 이긴다. 트랜스크립트 신호로만 상태를 바꾸는 경우는 R1의 표에
  "보조"로 표시된 칸뿐이다.

**내부 상태 식별자**(표시 명칭은 데이터 `strings`의 `state.<id>`): `working`, `asking`, `permission`,
`humming`, `bored`, `off_duty`. n호기는 `working`/`permission`/`off_duty`만 갖는다("!"는 n호기에도
붙는다는 SPEC F1 매핑을 따라 `permission`을 허용. 소멸은 `off_duty`).

**상태 머신**: 공유 규칙 R1(전이 표)이 단일 원천이고 `core/sessions.py`의 `SessionTracker`가 유일한 구현이다.

**PermissionRequest↔PostToolUse 짝짓기**(위임 답): `tool_use_id`가 없으므로 호기 단위 키
`(session_id, agent_id 또는 "main")`마다 `tool_name → 대기 개수` 다중집합을 둔다. `PermissionRequest`는 해당
도구의 개수를 +1, 같은 키·같은 `tool_name`의 `PostToolUse`/`PostToolUseFailure`는 −1(0 미만 금지). 다중집합이
비어 있지 않으면 그 호기는 `permission`. 같은 도구의 병렬 호출은 어느 요청이 해제되는지 구분할 필요가 없다 —
개수가 0이 될 때까지 "!"가 유지되므로 화면 결과는 같다. 정리 규칙: 메인 `Stop` → 메인 다중집합 비움,
`SubagentStop` → 그 n호기 제거, `SessionEnd` → 세션 전체 제거, 트랜스크립트에서 `toolDenialKind` 키가 있는
레코드 → 해당 호기의 다중집합 비움(보조, SPEC F15 6회차 허용), 마지막 이벤트로부터 T 경과 → 퇴근(SPEC F1).

**이벤트 순서**: 훅은 `async`로 따로 실행되어 파일에 쓰는 순서가 발화 순서와 다를 수 있다(M6). 한 번의 폴링에서
읽은 이벤트 묶음을 `ts`(훅 작성기가 찍은 벽시계 ms)로 안정 정렬한 뒤 적용한다. 이미 적용한 이벤트보다 ts가 이른
이벤트가 다음 폴링에 오면 그대로 적용하되 세션의 "마지막 이벤트 시각"은 `max`로만 갱신한다.

**Stop 뒤 활동 판정 유예**(2회차 K9): `humming`/`bored` → `working` 전이의 "활동"은 읽은 순서가 아니라 **ts 비교**로
판정한다. 활동 이벤트·신호의 `ts > hum_base + G`일 때만 인정하고, `G = timing.post_stop_grace_sec = 3`[기본값]. Stop보다
늦게 기록된 같은 턴의 PostToolUse(async 역전)나 Stop 직후 쓰인 트랜스크립트 레코드가 콧노래 중을 깨지 않게 하기 위함이다.
`ts ≤ hum_base + G`인 활동은 마지막 이벤트 시각만 갱신한다. G 값은 M6의 ts 역전 폭 실측으로 조정한다.

**같은 틱의 처리 순서**(2회차 K1): 작업자가 넘긴 한 묶음을 `Engine.ingest`가 다음 순서로 처리한다 —
① 훅 이벤트(ts 정렬) → `SessionTracker`(열림·상태) ② 열림에 따른 `Assigner` 배정·`fill_vacancies` ③ 트랜스크립트 신호.
**트랜스크립트 `activity`로 새로 열린 세션도 ④ 델타 처리 전에 ②와 같은 규칙으로 배정한다**(3회차 #6). 하위 에이전트 파일만
먼저 보이고 부모 메인 파일·훅 이벤트가 아직 없으면, 그 하위 파일의 `activity`를 부모 sid의 활동으로 보아 부모 세션을 열고
배정한다 ④ 토큰 델타 → R5 판정 → `Economy`·턴 버킷. **아직 "열림"이 되지 않은 세션의 델타는 버리지 않고 세션별 보류 큐에
넣었다가** 그 세션이 열려 배정되는 순간 R5로 판정해 적용한다. 하위 에이전트 파일이 메인 파일보다 먼저 읽혀 부모 세션이 아직
없는 경우도 같은 보류 큐(부모 sid 기준)를 쓰며, 위 규칙으로 부모가 같은 묶음 안에서 열리므로 보통 보류 큐에 오래 남지 않는다.
보류 큐는 세션당 T 동안만 유지하고 그 뒤에도 열리지 않으면 버린다.

**세션 발견**: (1) 이벤트 파일에 처음 보는 `session_id`가 오면 즉시 `projects\*\<sid>.jsonl`을 찾아 감시 목록에
넣는다. (2) **3초마다 `projects\*` 하위 디렉터리(슬러그 폴더)와, 활성(열린) 세션의 `<sid>\subagents` 폴더만**(3회차 #13 —
퇴근한 세션·오래된 세션의 subagents 폴더는 stat하지 않고 30초 전체 탐색에 맡김) **mtime을 stat**하고, mtime이
바뀐 디렉터리만 `os.scandir`로 나열해 새 `.jsonl`을 찾는다[기본값](2회차 K2). NTFS에서 디렉터리 mtime은 항목이 생기거나
지워질 때 바뀌므로 새 세션 파일 생성을 3초 안에 잡는다(M13). (3) 30초마다 `projects` 트리 전체를 훑는 탐색은 보조
안전망으로 유지한다[기본값]. (4) `SubagentStart`가 오면 `<sid>\subagents\agent-<aid>.jsonl`을 감시 목록에 넣는다.
훅 이벤트 없이 트랜스크립트만 갱신된 세션(훅 설치 전에 시작된 세션, C7)도 감지해 `working`으로 표시한다(SPEC F1 첫
수용 기준).

**cwd 고정**(2회차 N22): 세션의 cwd는 **처음 관측한 값**(훅 이벤트의 `cwd` 또는 트랜스크립트 첫 레코드의 `cwd` 중
먼저 온 것)으로 고정하고, 이후 다른 값이 와도 바꾸지 않는다(세션 중 `cd`로 오버레이·단골 키가 흔들리지 않게).

**훅 상태 게이트**: `HookStatus`(R11)가 `OK`가 아니면 `App`이 띠·시뮬레이션 틱·토큰 집계를 멈추고
설치 안내 창만 보인다. 검사는 시작 시 1회 + 30초마다[기본값]. 판정 세부는 F16.
**안내 화면 구간 = 꺼짐 구간**(2회차 L1, SPEC F1·F3·F18 6회차): 게이트가 닫힌 시각 `gate_closed_at`을 세이브에 기록하고,
게이트가 닫힌 동안에는 이벤트·트랜스크립트 커서를 전진시키지 않는다. 다시 `OK`가 되면 `catchup.run`을 앱 시작 때와
**같은 규칙**(F18 1~5단계)으로 한 번 실행한다 — 그 구간의 토큰은 널 캐릭터가 맡은 세션을 제외하고(저장된 널 목록에 없는
세션, SPEC 7회차 190·646행 괄호 "널 캐릭터가 맡은 세션 제외"와 일치 — 3회차 #5) 재화로,
경험치·단골 갱신 없음, 세션 상태는 마지막 이벤트 시각과 현재 벽시계로 재판정, 그 구간에 시작·종료된 세션이 있으면
`absence_summary` 1건. 시뮬레이션 시계도 그 구간 동안 멈춘다. 게이트가 닫히기 전에 배정돼 있던 세션은 재개 때 `origin="resumed"`
(F2 (마))로 같은 캐릭터를 유지하고 `cut_at = 재개 시각`이 된다(3회차 #1).

**헤드리스 `-p`**(위임 답): `Stop`·`Notification`이 오지 않을 수 있다(M3). 대비책은 이미 설계에 들어 있다 —
`Stop`이 없으면 트랜스크립트 턴 종료 신호 + idle_prompt 조합(R1 보조 칸)이나 정체 판정(C1)이 콧노래 중/퇴근을
대신한다. 실측 결과 `-p`에서 `Stop`이 발화하지 않는 것으로 확인되면, `-p` 세션(`entrypoint` 열거값으로 구분 — SPEC
F15 6회차가 "헤드리스 여부 판별용 열거값"으로 허용, 값은 세이브·로그에 쓰지 않음, M3)에
한해 트랜스크립트 턴 종료 단독으로 콧노래 중에 들어가도록 데이터 플래그 `hook_mapping.headless_turn_end_fallback`을
켠다[기본값 false].

**퇴근 임계 T 기본값**(위임 답): **3시간**[기본값] (`timing.off_duty_threshold_min = 180`). 콧노래 1시간보다 길어야
한다는 제약은 데이터 로더의 교차 검증으로 강제한다(R13). 이벤트 파일 보존 기간(7일[기본값])은 T보다 길어야 한다
(재시작 시 재구성).

TA
- TA1-1: `SessionTracker`는 Qt를 import하지 않는 순수 Python이며, `(이벤트 목록, 트랜스크립트 신호 목록, now_ms)`
  입력만으로 R1의 모든 전이를 단위 테스트할 수 있어야 한다.
- TA1-2: 같은 도구 `Bash`에 대한 `PermissionRequest` 2건 뒤 `PostToolUse(Bash)` 1건이면 "!" 유지, 2건이면 해제.
- TA1-3: `agent_id="a1"`인 `PermissionRequest`는 메인이 아닌 a1 호기에만 `permission`을 만든다.
- TA1-4: `SessionEnd`(reason 값 무관, 저장도 하지 않음) 직후 틱에서 세션은 `off_duty`이고 n호기 0개.
- TA1-5: `Stop` ts=t0 이후 이벤트가 없으면 `t0+1h−1ms`까지 `humming`, `t0+1h`부터 `bored`, `t0+T`부터 `off_duty`.
  n호기 이벤트 ts=t1>t0가 있으면 기준 시각은 `max(t0, t1)`.
- TA1-6: 메인 `Stop` 뒤 n호기가 `working`이면 1호기 표시는 `working`, 세션은 퇴근하지 않는다.
- TA1-7: `Notification(idle_prompt)` 단독으로는 어떤 상태도 바뀌지 않는다(R1 보조 칸의 조건이 모두 맞을 때만).
- TA1-8(3회차 #3 정정): 앱 재시작 시 보존 기간의 이벤트 파일 전체를 재생해 각 세션의 상태·마지막 이벤트 시각·퇴근 오버레이
  경과를 재구성한다. **`event_cursor` 이전 구간은 "상태만" 모드**로 부수효과(경험치, 연대기, 보너스, 재화, 단골)가 0건이고,
  **이후 구간은 "따라잡기" 모드**로 F18 규칙에 따라 `session_end`·`absence_summary`·단골 갱신·재화(경험치·보너스 없음)가
  생긴다(F18의 2단계 재생).
- TA1-9: 훅 이벤트→상태 매핑과 상태 표시 명칭은 `hook_mapping.json`·`strings.ko.json`에서 읽는다. 코드에는 이벤트명
  문자열 비교가 `hook_mapping`을 해석하는 한 곳(`sessions.py`)에만 있다.
- TA1-10: 설정 화면과 세이브 스키마에 세션 선택·제외 항목이 없다.
- TA1-11(2회차 K2): 새 슬러그 폴더 또는 기존 폴더에 새 `<sid>.jsonl`이 생기면, 훅 이벤트가 없어도 다음 3초 디렉터리
  stat 주기 안에 감시 목록에 오르고 `working`으로 표시된다(가짜 파일시스템으로 단위 테스트, 실제 지연은 M13).
- TA1-12(2회차 K9): Stop ts=s 뒤 `ts ≤ s+3초`인 PostToolUse가 늦게 기록돼도 `humming` 유지, `ts > s+3초`면 `working`.
- TA1-13(2회차 K1): 하위 에이전트 파일의 델타가 부모 세션 열림보다 먼저 들어와도 보류 큐를 거쳐 열림 직후 한 번만
  적용된다(누락·중복 0).
- TA1-14(2회차 L1): 게이트가 닫힌 구간에 쌓인 이벤트·토큰은 게이트가 다시 열릴 때 `catchup.run`으로 처리되고, 그 구간
  세션의 턴에는 경험치가 붙지 않는다.
- TA1-15(2회차 K7): `toolDenialKind`·`interruptedMessageId`의 **값**이 파서 출력 dataclass·세이브·로그 어디에도 없다
  (파서 단위 테스트에서 값 문자열을 임의로 바꿔도 출력이 같다).
- TA1-16(2회차 N22): 같은 세션에서 cwd가 다른 이벤트가 와도 오버레이 폴더명과 `cwd_key`는 첫 관측값을 유지한다.
- TA1-17(3회차 #6): 훅 이벤트 없이 하위 에이전트 파일만 먼저 나타난 묶음에서, 부모 sid가 그 묶음 안에서 열려 배정되고 하위
  파일의 델타가 같은 묶음의 ④에서 R5로 판정된다(보류 큐 잔류 0).

### F2. 세션↔캐릭터·호기 매핑

**구현**: `core/assign.py`의 `Assigner`가 유일한 배정 결정자다. 입력은 세션 열림·닫힘 신호(`SessionTracker`가 발행),
**배정 가능 캐릭터 목록**(`list[AssignableChar(char_id, join_seq)]` — `Engine`이 I4의 `Roster`에서 고아를 뺀 명단으로 만들어
넘기는 데이터, 2회차 N15: `Assigner`는 I4 모듈을 import하지 않는다), 즐겨찾기 순서, 단골 표. 출력은 `Assignment(sid, char_id |
NULL_CHAR, assigned_at_ms, assign_seq, cut_at_ms | None)`. `cut_at_ms`는 R5의 지급 하한(아래).

- 배정 우선순위(SPEC F2) 구현 순서: `favorites_free`(즐겨찾기 시각 내림차순) → `regular_of(cwd_key)`가 비어 있으면
  → `idle_by_join_order` → 널.
- 폴더 키(`cwd_key`)는 R8: `os.path.normcase(os.path.normpath(cwd))`(Windows에서 소문자·역슬래시 정규화). 표시용
  폴더명은 정규화 전 cwd의 마지막 요소.
- 같은 폴더 동시 세션: 단골은 이미 다른 세션이 쥐고 있으면 "담당 세션 있음"이 되어 자연히 건너뛴다.
- 빈자리 채우기 `fill_vacancies(now)`: 진짜 캐릭터가 빌 때(퇴근·충원·고아 복귀·명단 증가) 호출. 널 세션을 시작 시각
  오름차순으로 순회하며 위 우선순위로 빈 캐릭터를 고른다. 같은 틱에 새 세션 열림과 빈자리가 겹치면 `fill_vacancies`를
  먼저 실행한 뒤 새 세션을 배정한다(SPEC F2 "널 교체가 먼저").
- 호기 번호: 세션마다 `used_numbers` 집합. 메인 = 1. `SubagentStart` 때 2부터 가장 작은 빈 번호. 해제는
  `SubagentStop`·정체·세션 퇴근.
- 호기 인스턴스 ID(R9): 메인 = `"{sid}#m{assign_seq}"`, n호기 = `"{sid}#a{agent_id}"`. 응원 쿨다운은 이 ID에
  붙으므로 번호를 재사용해도 쿨다운이 이어지지 않는다(SPEC F9⑦).
- 세션 열림 정의: 퇴근 상태가 아닌 세션에 처음 활동이 보일 때, 또는 `off_duty`인 세션에 새 활동이 올 때(재배정, 새
  `assign_seq`). 재배정 시 `session_links[sid]`의 `start_recorded`·`first_wait_recorded`는 **새 assign_seq마다 false로
  초기화**한다(2회차 L4, SPEC F11·F14 6회차 "배정 회차 단위").
- **지급 하한 `cut_at_ms`**(2회차 K1): (가) 앱 실행 중(라이브 모드)에 **처음 본 새 세션 ID**가 진짜 캐릭터를 받으면 `cut_at_ms
  = None` — 세션의 첫 레코드부터 재화·경험치를 준다. (나) 널 → 진짜 캐릭터 교체: `cut_at_ms = 교체 시각`. (다) 앱 시작·게이트
  재개 시점에 이미 진행 중이던 세션이 배정받을 때: `cut_at_ms = 배정 시각`(그 이전 토큰은 F18 따라잡기 규칙으로 재화만).
  (라) 퇴근 뒤 같은 sid 재배정: `cut_at_ms = None`(직전 회차 종료 이후의 레코드는 모두 새 회차 몫).
  (마) **`origin="resumed"`**(3회차 #1): 앱 재시작·게이트 재개 때 세이브 `session_links`에 같은 sid가 있고 그 세션이 아직 퇴근
  전이면(SPEC F2 149행 "같은 세션 ID가 퇴근 전에 다시 보일 때 이전 캐릭터를 그대로") 새로 배정하지 않고 **저장된 `char_id`·
  `assign_seq`를 유지**한다. `start_recorded`가 true면 `session_start`를 다시 기록하지 않고 `first_wait_recorded`도 유지한다.
  `cut_at_ms = 재개 시각`(앱 시작 또는 게이트가 다시 열린 시각) — 꺼짐·안내 화면 구간의 메시지는 F18 따라잡기 규칙(재화만)으로
  처리되고, 재개 이후 타임스탬프의 메시지만 라이브로 재화·경험치를 받는다. 저장된 캐릭터가 그 사이 고아가 되었어도 진행 중
  세션이므로 유지한다(F4).
  **컷 단위 = 메시지**(3회차 #9, 사용자 2026-11-09 확정, SPEC 7회차 새 문구 "컷 시각(교체·배정·재개) 이후 타임스탬프의 메시지부터
  재화·경험치 반영, 컷 순간 진행 중이던 턴의 나머지 메시지도 새 캐릭터가 받는다"): `cut_at_ms`는 턴 경계가 아니라 메시지
  `timestamp` 비교(`ts ≥ cut_at_ms`)로 적용한다. 컷 순간 진행 중이던 턴은 컷 이후 메시지만 그 캐릭터의 몫이고, 그 부분 턴도 턴
  종료 때 정상 정산된다(F12).
- 단골 갱신: 세션이 `off_duty`로 바뀌는 순간, **그 시점의 담당이 진짜 캐릭터**이고 그 세션의 시작(배정)이 첫 실행 이후이고
  앱이 그 세션을 "실행 중에 보았거나 꺼지기 전에 배정했던" 경우에만 `folder_regulars[cwd_key] = char_id`. 널로 시작했다가
  진짜로 교체된 세션도 종료 시점 담당이 진짜면 갱신하고, 널인 채 끝나면 갱신하지 않는다(2회차 L3, SPEC F2 6회차 172행).
  꺼진 동안·안내 화면 구간에 시작·종료된 세션과 기준선 이전 세션은 갱신하지 않는다(F18 규칙과 동일).
- **session_links 보존·정리**(O): `off_duty`가 된 세션의 링크는 퇴근 오버레이 유지 시간 + T가 지나면 세이브에서 지운다(같은
  sid가 다시 오면 새 배정이므로 필요 없음). `null_sessions`는 퇴근·교체 즉시 지운다.
- 고아 캐릭터(R14): 풀에 없는 명단 캐릭터는 배정 후보에서 빠진다. 진행 중 세션을 맡은 고아는 그 세션이 끝날 때까지
  유지한다.

TA
- TA2-1: `Assigner`는 순수 Python이며 SPEC F2의 예시(미쿠·린, 세션 A·B·C, A 퇴근 → C 교체)가 단위 테스트로 재현된다.
- TA2-2: 어떤 시점에도 `char_id → sid` 역색인의 값은 1개 이하(불변식 검사를 디버그 빌드에서 매 틱 수행).
- TA2-3: 널 세션의 토큰 델타는 `Economy.credit_tokens`에 도달하기 전에 버려진다(R5). 널→진짜 교체 세션과 시작 시점에
  이미 진행 중이던 세션·재개(resumed) 세션은 `cut_at_ms` 이후 타임스탬프의 메시지만 재화·경험치로 가고(컷 단위 = 메시지, SPEC
  7회차 문구 — 3회차 #9), 실행 중 처음 본 새 세션은 첫 레코드부터 간다(2회차 K1).
- TA2-4: `session_links`(sid→char_id·assign_seq·assigned_at·cut_at)와 `null_sessions`(sid·cwd·started_at)는 세이브에
  저장되고 토큰은 저장하지 않는다.
- TA2-5(2회차 L3): 널로 시작해 미쿠로 교체된 뒤 퇴근한 세션은 `folder_regulars[cwd_key] = miku`, 널인 채 퇴근한 세션은
  단골 표 무변경.
- TA2-6(2회차 L4): 퇴근 후 같은 sid가 재배정되면 `first_wait_recorded=false`가 되어 새 회차의 첫 "?"/"!"에서
  `first_wait`가 다시 기록된다.
- TA2-7(2회차 N15): `assign.py`의 import 목록에 `core.roster`·`core.economy`·`core.characters`가 없다(정적 검사).
- TA2-8(3회차 #1): 미쿠가 맡은 세션 S가 진행 중일 때 앱을 재시작하면, 재시작 후에도 S는 미쿠(같은 assign_seq)이고 연대기의
  S `session_start`는 전후 합쳐 1건이며, 재개 시각 이전 타임스탬프의 메시지는 경험치에 들어가지 않는다(재화는 따라잡기 규칙만).

### F3. 토큰 총량→재화

**토큰 총량 정의**(R2): `message.usage`의 `input_tokens + output_tokens + cache_creation_input_tokens +
cache_read_input_tokens`(없는 키는 0). 가중치 표를 데이터에 두되 1차 값은 모두 1.

**환산표 형식**(위임 답, `economy.json`):

```json
"conversion": {
  "tokens_per_unit": 10000,
  "weights": { "input_tokens": 1, "output_tokens": 1,
               "cache_creation_input_tokens": 1, "cache_read_input_tokens": 1 }
}
```

- 재화 증가 = `floor((remainder + weighted_total) / tokens_per_unit)`, 나머지는 세이브 `economy.token_remainder`에
  보관해 손실이 없다. `tokens_per_unit` = 10000[기본값](근거: 이 PC의 한 응답이 캐시 읽기 포함 수만~수십만 토큰,
  S2. 실제 분포는 M11로 재조정). 값을 바꿔도 이미 지급된 재화는 다시 계산하지 않는다(누적 잔액만 저장하므로 자연히 성립).
- 재화는 Python `int`(상한 없음, SPEC F3). 세이브 JSON에도 정수로 쓴다.

**중복 집계 방지 구현**(위임 답, R3·R4. 2회차 N2·K5로 변경):
- 파일별 상태 `FileCursor{key, offset, size, mtime_ns}`. **키는 경로가 아니라 sid 기반**이다 — 메인 `"<sid>"`, 하위
  `"<sid>/a/<agentId>"`(2회차 K5). 경로는 매번 2.2 규칙(`projects\*\<sid>.jsonl`, `<sid>\subagents\agent-<aid>.jsonl`)으로
  다시 계산하며 세이브·로그에 경로를 쓰지 않는다(계산한 경로는 메모리 캐시에만 둔다 — 3회차 #8). 폴링 시 `(size, mtime_ns)`가
  같으면 열지 않는다. 다르면 `offset`부터 읽어 마지막 `\n`까지만 소비하고 `offset`을 그 위치로 옮긴다.
- **같은 sid가 여러 슬러그 폴더에 있을 때**(3회차 #8, M10): `projects\*\<sid>.jsonl`이 2개 이상 발견되면 그 sid의 커서 키를
  `"<sid>@<슬러그 폴더명 SHA-256 앞 8자>"`(하위는 `"<sid>@<해시>/a/<aid>"`)로 전환해 파일마다 따로 둔다. 기존 `"<sid>"` 커서는
  먼저 발견된(mtime이 이른) 쪽 키로 이름만 옮긴다. 토큰 중복은 전역 id 집합(R3)이 막으므로 키 전환은 오프셋 관리만을 위한 것이다.
  해시는 폴더명만 가리고 경로 자체는 세이브·로그에 쓰지 않는다.
- **전역 메시지 id 집합(시간 창)**(2회차 N2): `SeenIds{msg_id → (지급한 총량, 마지막 관측 ts)}`를 파일과 무관하게 **하나만**
  둔다. assistant 레코드마다 `t = total(message.usage)`; `prev = seen.get(id, 0)`; `delta = max(0, t − prev)`;
  `seen[id] = (max(prev, t), ts)`; `delta > 0`이면 `TokenDelta(sid, agent_id, msg_id, ts_ms, delta)` 발행. 같은 id가 여러
  줄·여러 번·**여러 파일**(resume·continue로 이전 대화가 새 파일에 복사되는 경우, M10)에 나와도 최종 usage만큼만 한 번
  반영된다.
- 시간 창(3회차 #2로 하한 정정): 마지막 관측 ts가 `last_ingest_ms − 창`(`ingest.dedupe_window_days = 7`[기본값])보다 오래된
  id는 집합에서 뺀다. 창보다 오래된 메시지가 새 파일에 복사되어 다시 나타나는 경우를 막기 위해, **레코드 `timestamp`가
  `last_ingest_ms − 창`보다 이른 assistant 레코드는 지급하지 않는다.** 하한을 `now`가 아니라 `last_ingest_ms`(세이브 R18, 마지막으로
  수집을 마친 시각)에서 세는 이유: 앱이 창보다 오래(예 10일) 꺼져 있었다면 그 구간의 진짜 새 메시지도 `now − 창`보다 이르므로
  `now` 기준이면 따라잡기에서 버려진다. `last_ingest_ms − 창`보다 이른 메시지는 직전 수집 시점에 이미 창 안에서 보고 지급했거나
  (집합에서 빠진 것은 창 밖으로 밀려난 것뿐) 기준선 이전이다. `last_ingest_ms`는 매 수집 틱(라이브 폴링·따라잡기 완료)마다
  그 틱의 시작 시각으로 갱신하고, 기준선 때 기준 시각(`first_run_ms`)으로 초기화한다. 게이트가 닫힌 동안은 수집하지 않으므로
  갱신되지 않는다.
- 파일이 줄어들면(`size < offset`) 재작성으로 보고 처음부터 다시 읽는다. 전역 집합이 이미 지급한 id를 걸러 주므로 중복 지급은
  없고, 경고는 sid만 로그에 남긴다.
- 커서와 전역 집합은 세이브 `ingest.transcript_cursors`(키→offset·size·mtime_ns)와 `ingest.seen_ids`(id→총량·ts, 창 안의
  것만)에 저장한다. SPEC F14의 "로그 마지막 집계 시점과 반영된 메시지 ID"가 이것이다. 커서는 **활성 파일**(최근 T+1시간 안에
  바뀐 파일과 열린 세션의 파일)만 저장하고, 비활성 파일은 `(offset=size, size, mtime_ns)` 3정수만 남긴다(2회차 N5). 사라진
  파일의 커서는 지운다(로그 정리 영향 없음).
- **크래시 일관성**(2회차 N5): 토큰 반영(잔액·나머지)과 커서·`seen_ids` 갱신은 같은 메모리 상태에서 함께 바뀌고 **한 번의
  세이브 쓰기**로 함께 저장된다. 쓰기 전에 크래시하면 둘 다 이전 값으로 돌아가 다음 실행에서 같은 구간을 다시 읽어 한 번만
  반영한다.

**기준선**(R5): 온보딩 완료 순간 `projects` 트리의 모든 `.jsonl`에 대해 `offset = 마지막 \n 위치`인 커서를 만든다.
그 이후 생긴 파일은 offset 0에서 시작. 기준선 이전 토큰은 어디에도 반영되지 않는다. 같은 순간 **`ingest.event_cursor`를 현재
이벤트 파일의 끝으로 초기화**한다(2회차 K3). 기준선 이전 이벤트는 "상태만" 모드로 재생해 열린 세션 식별에만 쓰고
`session_end`·`absence_summary`·단골 갱신을 만들지 않는다. 기준선 순간에 `first_run_ms`가 정해지므로 시간 창 규칙과 함께
기준선 이전 메시지가 복사본 파일로 다시 나타나도 지급되지 않는다(`timestamp < first_run_ms`인 레코드는 지급 안 함).

**안내 화면 구간**(2회차 L1, SPEC F3 6회차 190행): 게이트가 닫힌 동안 쌓인 토큰은 게이트 재개 시 F18 따라잡기 규칙으로
지급한다 — 진짜 캐릭터가 배정된(저장된 널 목록에 없는) 세션만, 경험치 없음.

**직렬 처리**: 모든 재화 변경은 메인 스레드의 `Economy` 메서드 하나씩을 통해서만 일어난다(5c). UI는 요청을 큐에
넣고 결과를 받는다. 각 메서드는 "잔액 확인 → 차감 → 세이브 dirty 표시"를 한 번에 수행하므로 음수·이중 차감이
없다. 기본 간식(상점 물건이 아닌 "간식 주기")은 예약 물건 id `"_basic"`으로 다루며(2회차 N10), `items.json`에 이 id의 행을
둘 수 없다(로더 검증).

TA
- TA3-1: 같은 `message.id`가 3줄(usage 동일)이면 델타 합 = 1회분. 2줄째가 더 큰 usage면 델타 합 = 최종값.
- TA3-2: usage가 줄 안에 두 번 있는 레코드(2.2 사실 2)에서 총량이 두 배가 되지 않는다(테스트 픽스처에 중첩
  `iterations` 포함).
- TA3-3: 토큰 종류만 다르고 합이 같은 두 메시지의 재화 증가가 같다.
- TA3-4: `Economy.buy(...)`를 같은 틱에 10번 호출해도 잔액은 0 미만이 되지 않는다.
- TA3-5: 재화 표시는 `strings`의 `currency.name`·`currency.format`으로 만든다.
- TA3-6(2회차 N2): 같은 `message.id`가 메인 파일과 다른 sid의 새 파일(resume 복사본)에 모두 있어도 지급은 1회분.
- TA3-7(2회차 K5): 세이브 JSON 전체에 트랜스크립트 경로 문자열이 없다(세이브 스냅샷 테스트에서 `projects` 경로 부분
  문자열 검색 0건). cwd 계열 값은 SPEC이 요구한 `null_sessions.cwd`와 단골 판정용 `cwd_key`(`folder_regulars` 키,
  `session_links.cwd_key`)에만 있다.
- TA3-8(2회차 K3): 온보딩 완료 직후 `event_cursor`는 이벤트 파일 끝이고, 그 전 이벤트로 인한 연대기·단골 변화가 0건.
- TA3-9(2회차 N5): 토큰 반영 후 세이브 쓰기 전에 프로세스를 죽이고 재시작해도 잔액은 정확히 1회분만 늘어 있다.
- TA3-10(3회차 #2): `last_ingest_ms = t0`로 저장하고 앱을 10일 끈 사이 진짜 캐릭터 세션이 쓴 메시지(ts가 t0+1일~t0+9일)는 다음
  시작 따라잡기에서 전부 재화로 지급된다(`now − 7일` 하한이었다면 버려졌을 메시지 포함). ts < t0 − 7일인 복사본 메시지는 지급 0.

### F4. 캐릭터

- 캐릭터 풀 = `characters.json`의 `characters[]`(10행: `miku, rin, len, luka, kaito, meiko, teto, neru, una,
  adachi_rei`[기본 id]). 행 필드: `id`, `name_key`, `default_skin`, `skins[]`(1차 1개), `sprite_dir`,
  `credit_group`, `dialogue_set`. 널 캐릭터는 이 배열에 없고 `null_character` 객체(실루엣 스프라이트, 이름 키
  `null.name` = "(미배정)")로 따로 둔다.
- 명단(세이브 `roster[]`): `{char_id, joined_at, join_seq, skin_id, display_name|null}`. 첫 실행 = `miku` 1명.
- 고아 처리(R14): 로드 시 풀에 없는 `roster` 항목은 `orphan=true` 런타임 표시만 붙이고 세이브에서는 지우지 않는다.
  화면 숨김·충원 후보 제외. 풀에 돌아오면 자동 복원. 복원으로 명단 인원이 현재 숙소 등급의 캐릭터 상한을 넘어도 허용한다
  (기존 캐릭터를 다시 숨기지 않음, 새 충원만 상한으로 막힘)(O).

TA
- TA4-1: 데이터 로더가 `characters`의 id 중복, `default_skin`이 `skins`에 없음, `credit_group`이 `credits.json`에
  없음을 검증 실패로 처리한다.
- TA4-2: 고아 캐릭터가 있는 세이브를 로드·저장해도 그 항목이 바이트 단위로 보존된다(알 수 없는 필드 포함).

### F5. 충원

`economy.json`:

```json
"recruit": {
  "pick_until_roster_size": 5,
  "cost_bands": [ { "min_n": 2, "max_n": 2, "cost": 0 },
                  { "min_n": 3, "max_n": 5, "cost": 1500 },
                  { "min_n": 6, "max_n": 10, "cost": 4000 } ]
}
```
[기본값] n = 충원 후 명단 인원(고아 제외, 널 제외). 구간은 연속·겹침 없음을 로더가 검증. 마지막 구간보다 큰 n은
마지막 구간 비용. 가챠는 `random.SystemRandom().choice(후보)`; 후보 = 풀 − 명단(고아 제외 기준 풀). 충원 성공 시
`Assigner.fill_vacancies` 호출, 연대기 `recruit`.

TA
- TA5-1: 버튼 활성 조건 = 후보 ≥ 1 AND 명단 < 숙소 상한 AND 재화 ≥ 비용. 비활성일 때 사유 문자열 키를 표시.
- TA5-2: 명단 5명 이하 구간의 충원은 `pick`이 필수(None이면 `TxResult(ok=False)`), 6명째부터는 `pick`을 무시하고 가챠
  결과가 명단에 없던 캐릭터다(난수 시드 고정 1000회 테스트에서 중복 0).
- TA5-3: 충원 성공 직후 같은 틱에서 가장 오래된 널 세션이 새 캐릭터로 교체되고 `cut_at_ms = 교체 시각`이다.

### F6. 숙소

`dorm.json`의 `grades[]`[기본값]:

| 등급 | 캐릭터 상한 | 바닥 슬롯 | 벽 슬롯 | 업그레이드 비용(이 등급으로) | 소요 시간 |
|---|---|---|---|---|---|
| 1 | 2 | 4 | 2 | — | — |
| 2 | 4 | 5 | 3 | 3000 | 2시간 |
| 3 | 6 | 6 | 4 | 8000 | 6시간 |
| 4 | 8 | 7 | 4 | 20000 | 12시간 |
| 5 | 10 | 8 | 5 | 50000 | 24시간 |

- 진행 중 업그레이드는 세이브 `dorm.upgrade = {to_grade, started_at_ms, duration_ms}`. 완료 = 벽시계
  `now ≥ started_at + duration`. 매 틱과 따라잡기에서 검사. 시계 역행 처리는 R6.
- 로더 검증: 1등급 상한 ≥ 2, 상한 비감소, 최고 등급 = 마지막 행.

TA(2회차 N1)
- TA6-1: 가짜 시계로 업그레이드 시작 후 `duration − 1ms`에는 등급 유지, `duration`에 등급 상승·`dorm_upgrade` 연대기 1건.
- TA6-2: 진행 중 두 번째 `start_upgrade`는 `TxResult(ok=False, reason_key="dorm.busy")`이고 잔액 무변경.
- TA6-3: 꺼진 동안 완료 시각이 지난 세이브로 시작하면 `catchup.run`이 완료 시각의 게임 날짜로 연대기를 남긴다.

### F7. 꾸미기

- `furniture.json` 행: `id, name_key, kind(bed|desk|sofa|deco|…), slot(floor|wall), price, comfort, pose(포즈 키 |
  null), use(work|rest|sit|none), sprite`. `items.json`(간식류): `id, name_key, price, sprite`. 캐릭터×물건 예외:
  `items.json`의 `snack_exceptions: []`(1차 비어 있음).
- 세이브: `furniture[] = {iid, def_id, placed: {slot_type, index} | null, owner_char|null, is_default}`;
  `items = {item_id: count}`.
- **쾌적도 합산**(위임 답): `comfort = min(Σ 배치된 가구의 comfort, comfort_cap)`, `comfort_cap = 100`[기본값].
  바닥·벽 모두 포함, 보관함 제외.
- 배치 규칙: 슬롯 종류 불일치 거부, 점유 슬롯에 배치하면 기존 가구는 `placed=null`(보관함).

TA(2회차 N1)
- TA7-1: 바닥 가구를 벽 슬롯에 `place`하면 `TxResult(ok=False)`, 상태 무변경.
- TA7-2: 점유된 슬롯에 배치하면 기존 가구 `placed=null`, 쾌적도 = 배치된 가구 합(보관함 제외, 상한 100).
- TA7-3: 데이터에서 사라진 가구(`def_id` 고아)는 세이브에 남고 쾌적도·화면에서 빠진다.

### F8. 기분(심심함 척도)

`mood.json`[기본값]:

| 키 | 값 | 의미 |
|---|---|---|
| `initial` | 50 | 초기값 |
| `range` | [0, 100] | |
| `bands` | `{"low_max_exclusive": 33, "high_min_inclusive": 67}` | v<33 나쁨, 33≤v<67 중간, v≥67 좋음 |
| `rise_per_sim_hour` | 12 | 일하는 중 기본 상승 |
| `fall_per_sim_hour` | 6 | 심심해요·배정 없음 기본 하락 |
| `comfort_effect` | 0.5 | f = 1 + 0.5 × comfort/comfort_cap (1.0~1.5) |
| `off_duty_bonus` | 3 | 퇴근 보너스 |
| `snack_gain` | 5 | 간식 주기·간식 선물 정상 반응 |
| `affection_multiplier` | `{"low":0.9,"mid":1.0,"high":1.1}` | |

- **구간 경계값 소속**(위임 답): 경계값은 위 구간에 속한다(33 = 중간, 67 = 좋음). 판정 함수는 R15 하나.
- 상승 = `rise × f × Δsim_h`, 하락 = `fall ÷ f × Δsim_h`, 결과를 [0,100]으로 clamp.
- 캐릭터 단위 심심함 척도 원천(3회차 #12, 여러 호기를 가진 캐릭터): 호기 중 하나라도 `working` → 상승. 아니면 메인 호기가
  `asking`/`permission`/`humming` → 유지. 아니면(`bored`, 배정 없음, 퇴근 후 휴식) → 하락.
- 퇴근 보너스는 앱 실행 중 실시간으로 처리된 퇴근에만 준다. 따라잡기(꺼짐·안내 화면 구간) 중의 퇴근에는 주지 않는다(C2,
  PM 확정).

TA(2회차 N1)
- TA8-1: `mood_band(32)="low"`, `mood_band(33)="mid"`, `mood_band(66)="mid"`, `mood_band(67)="high"`.
- TA8-2: comfort 0과 100에서 같은 1 sim-hour 동안 상승폭 비 = 1.5, 하락폭 비 = 1/1.5.
- TA8-3: `TickDelta.sim_ms = 0`인 틱(공백·꺼짐)에서는 척도가 바뀌지 않는다.

### F9. 애정

`affection.json`[기본값]:
- 초기값 `initial = 0`[기본값](2회차 K10, SPEC F9 "초기값은 데이터(애정 0)").
- 단계 6개: 경계 `[0, 100, 300, 600, 1000, 1500]`, 최대 `2000`(6단계 상한, 도달 시 "MAX" 표시·증가 정지).
- 시간 증가: `rate_per_sim_hour = 10`. 증가량 = `rate × g × mood_mult × Δsim_h`(곱한 뒤 재clamp 없음).
- 성장률 `g(t) = clamp(1 − k·ln(1 + t/τ), 0.2, 1)`, `k = 0.35`, `τ = 1 sim-hour`, t = 마지막 리셋 이후 시뮬레이션
  시간. (t=1h → 0.76, 3h → 0.51, 약 9.8h 이후 0.2.) 세이브에는 `g_reset_sim_ms`(그 캐릭터 리셋 시점의 시뮬레이션
  시계 값)를 저장한다.
- 행동 상승량(× mood_mult, g 미적용, 상승 후 g 리셋): 말 걸기 2, 간식 주기 3, 쓰다듬기 2, 쓰다듬기 특수(높은 단계)
  추가 5, 큰 폭 선물 30, 소량 선물 1, 응원 2.
- 쓰다듬기 "높은 단계" 경계 = **상위 절반**: 단계 수 N이면 `⌈N/2⌉ + 1` 이상, 6단계면 **4단계 이상**(데이터
  `pet_high_stage_min = 4`[기본값])(2회차 L6, SPEC F9⑤ 6회차 399행). 로더는 이 값이 1~N 범위인지 검증한다.
- 반응 종류 `Reaction.kind`: `normal | like | refuse | full | special_like | special_refuse | invalid`. `like`는 캐릭터×물건
  예외 조합의 간식(선물)에서 "계속 먹으며 좋아하는 반응"이다(2회차 N10). 기본 간식은 예약 id `"_basic"`으로 같은 예외 표를
  조회한다(1차 예외 표는 비어 있음).
- 연속 규칙 `interactions.json`: `window_min = 10`, `talk.refuse_at = 5`, `snack.full_at = 3`, `pet.special_at = 5`,
  `cheer.cooldown_sec = 60`, `gift.big_cooldown_h = 6`, 행동별 대사 키 목록.
- 연속 카운트 상태: 세이브 `streaks[char_id][action] = {window_start_ms, count}`. 행동 시 `now − window_start ≥
  window` 또는 `now < window_start`(역행)이면 `window_start = now, count = 0`으로 다시 시작 후 `count += 1`.
- 간식류 선물은 `streaks[char]["snack"]`에 합산. 예외 목록에 있는 (캐릭터, 물건)은 카운트·거부를 건너뛴다.
- 선물 한도: 세이브 `last_big_gift_ms[char_id]`. 큰 폭 = 없음 또는 `now − last ≥ 6h`. 역행 처리는 R6.
- 응원 쿨다운: 세이브 `cheer_cooldowns[unit_instance_id] = last_ms`(R9). 1분 초과한 항목은 저장 시 정리.
- 개명: R7 검증 함수만 사용. 연대기 `rename`.
- 즐겨찾기(2회차 L2, SPEC F9④ 6회차 390행): 띠 최우선 1칸은 가장 최근 즐겨찾기 캐릭터의 **1호기가 working/humming일 때만**
  차지한다. 배정 없는 몸·bored·퇴근한 몸은 상태별 위치가 우선한다(R17).

TA(2회차 N1)
- TA9-1: g는 리셋 직후 1, sim 1시간 뒤 약 0.757, 충분히 지나면 정확히 0.2(하한). g=0.2·척도 low에서 시간 증가 계수 0.18.
- TA9-2: 쓰다듬기 특수 반응은 단계 4 이상에서 `special_like`(추가 +5), 단계 3에서 `special_refuse`(애정·g 무변경).
- TA9-3: 말 걸기 5회째부터 `refuse`, 창 시작 시각 + 10분 뒤 첫 행동은 count=1로 새 창.
- TA9-4: 큰 폭 선물 직후 6시간 안의 다른 선물은 소량(+1)이고 `last_big_gift_ms`는 바뀌지 않는다. 거부된 간식 선물은 재고·한도·
  애정 무변경.
- TA9-5: 응원 쿨다운은 호기 인스턴스 ID 단위라 같은 번호를 새로 받은 n호기는 즉시 응원 가능.

### F10. 상호작용 추상 대화

- `chatter.json`: `interval_sec = [120, 360]`[기본값, 균등 분포 난수], `lines[] = {kind: chat|praise|prank|solo, icon,
  text_key, min_stage?}`. 다음 대화 시각은 벽시계가 아니라 앱 내부 단조 시계로 잡는다(꺼진 동안 몰아서 나오지 않게).
- 참여자: 화면에 보이는 진짜 캐릭터의 몸(캐릭터 단위로 중복 제거) 중 무작위 2명. 1명이면 `solo`. 널은 제외.
- 애정·척도에 어떤 호출도 하지 않는다(`chatter.py`는 `characters.py`를 import하지 않는다 — 정적 검사로 확인).

TA(2회차 N1)
- TA10-1: 가짜 단조 시계로 `interval_sec=[120,360]`에서 1000회 표본의 간격이 모두 범위 안.
- TA10-2: 보이는 진짜 캐릭터가 1명(호기 여럿 포함)이면 `solo` 줄만 선택된다. 널 몸만 있으면 대화 없음.
- TA10-3: 대화 전후 모든 캐릭터의 `mood`·`affection`·`g_reset_sim_ms`가 같다.

### F11. 연대기

- 파일: `%APPDATA%\agentview\chronicle.jsonl`(세이브와 별도). 한 줄 = `{"v":1, "ts": ms, "day": 게임날짜, "type":
  "...", "char": id|null, "params": {...}, "text": "렌더링된 문장"}`. `params`에는 숫자·캐릭터 id·가구 id만 넣고
  **cwd·폴더명·세션 본문은 넣지 않는다**(R12).
- 사건 type: `join, recruit, dorm_upgrade, furniture_buy, affection_stage_up, session_start, session_end,
  first_wait, absence_summary, rename`. 템플릿은 `chronicle.json`의 `templates[type]`.
- **로그 회전**(위임 답): 삭제하지 않는다. 파일이 5MB[기본값]를 넘으면 `chronicle-YYYYMMDD-HHMMSS.jsonl`로 이름을
  바꾸고 새 파일을 연다. 회전된 파일도 지우지 않는다.
- 자막 대기열: 표시 4초[기본값], 대기 상한 5[기본값]. 상한 초과분은 대기열 마지막 항목을 "외 N건"(템플릿
  `subtitle.more`)으로 대체 표시. 로그에는 모두 개별 기록.
- 기록 조건(널 제외, 메인만, 시작 기록된 세션만 종료 기록, 최초 입력 대기는 **배정 회차마다** 1회)은 `chronicle.py`의
  `record()`가 아닌 호출자(`assign.py`·`sessions.py` 연결부인 `core/game.py`)가 판단한다. 판단 함수는 R16 하나.
- **크래시 뒤 중복**(2회차 N5): 연대기는 사건마다 즉시 파일에 추가되고 세이브는 디바운스 저장이라, 크래시 후 재생에서 같은
  사건이 다시 생길 수 있다. 이를 허용하되 각 줄에 `"key": "<sid 또는 char>|<type>|<ts>"`를 넣고, 시작 시 현재 파일의 마지막
  1000줄[기본값]의 key 집합을 읽어 같은 key의 기록·자막을 건너뛴다.

TA(2회차 N1)
- TA11-1: 자막 7건을 한 번에 넣으면 대기열 표시는 4건 + "외 3건" 1건이고 로그에는 7줄.
- TA11-2: 널 세션의 열림·퇴근·"!"에서 `session_start`·`session_end`·`first_wait`가 0건.
- TA11-3: 파일 크기가 회전 임계를 넘으면 기존 파일이 `chronicle-<ts>.jsonl`로 남고(삭제 0) 새 파일에 이어 쓴다.
- TA11-4: 같은 key의 사건을 두 번 `record`하면 두 번째는 무시된다. 연대기 줄의 `params`·`text`에 cwd·폴더명이 없다.

### F12. 숙련 경험치

- 식: `xp = min(log2(1 + x), turn_cap)`, `turn_cap = 20`[기본값](x ≈ 100만 토큰에서 상한. M11로 재조정).
  세이브 `xp[char_id]`는 float.
- 턴 귀속: 세션마다 `turn_bucket`(토큰 합). 앱 실행 중(라이브 모드)에 받은 `TokenDelta` 중 R5를 통과하고(실행 중 처음 본 새
  세션은 첫 레코드부터, 교체·진행 중·재개 세션은 `cut_at_ms` 이후 타임스탬프의 메시지 — 2회차 K1, 3회차 #9) `ts_ms > 직전 턴
  종료 시각`인 것을 더한다. 메인 `Stop`(ts = s)이 오면 "턴 마감 대기"로 표시하고, **`s + G` 이후**에 완료된 트랜스크립트 폴링이 한
  번 끝나면 `ts_ms ≤ s`인 델타까지 포함해 경험치를 계산하고 버킷을 비운다(Stop 훅이 트랜스크립트의 마지막 usage보다 먼저 도착할
  수 있으므로). 마감 대기 상수는 Stop 뒤 활동 유예 G와 **같은 값·같은 키**(`timing.post_stop_grace_sec = 3`)를 쓴다(3회차 #11 —
  두 값이 다르면 "콧노래는 유지됐는데 그 델타는 다음 턴으로" 같은 어긋남이 생긴다). 마감 대기 중 늦게 읽힌 `ts_ms ≤ s` 델타는
  **직전 턴(마감 중인 턴) 버킷**에 넣고, `ts_ms > s`인 델타는 다음 턴으로 넘어간다. G는 M6 실측으로 조정한다.
- **컷 순간의 부분 턴**(3회차 #9, 사용자 결정 컷 단위 = 메시지): 교체·배정·재개로 `cut_at_ms`가 생긴 순간 진행 중이던 턴은 **컷
  이후 타임스탬프의 메시지만** 버킷에 넣고(컷 이전 메시지는 버킷에 들어가지 않음 — 널이었으면 버려지고, 꺼짐·안내 화면 구간이면
  재화만), 그 부분 턴도 다음 턴 종료(Stop 또는 퇴근 정산) 때 **정상 턴으로 정산**한다(턴당 상한 1회).
- 하위 에이전트에는 자기 턴이 없다. 하위 에이전트 토큰은 메인 세션의 현재 턴 버킷에 더하고, 메인 턴 종료(Stop) 때 한 번
  계산하며 턴당 상한도 그때 한 번 적용한다. 메인 Stop 이후에도 일하는 n호기의 토큰은 다음 메인 턴 버킷으로 간다(2회차 L5,
  SPEC F12 6회차 — C11 "SPEC 반영됨").
- **퇴근 정산**(2회차 L5): 세션이 Stop 없이 퇴근(SessionEnd 또는 임계 T)하면 남은 버킷을 턴 하나로 정산해 `min(log2(1+x),
  turn_cap)`을 지급한다. 정산 조건은 퇴근 직전 메인 상태가 **`working`·`humming`·`bored`면 정산**(3회차 #10 — R1과 통일, humming·
  bored는 보통 버킷이 비어 있지만 Stop 뒤 n호기 토큰이 남을 수 있음), 퇴근 직전 메인이 `asking`/`permission`이었던(방치 퇴근)
  경우는 버킷을 버린다(재화는 이미 지급됨).
  따라잡기 중의 퇴근은 경험치가 없으므로 정산도 없다.
- 트랜스크립트 보조 신호로 턴 종료를 판정한 경우(R1 보조 칸)에도 같은 방식으로 경험치를 준다(C5, SPEC F15 6회차로 키 존재
  사용 허용).
- `turn_bucket`은 세이브에 저장하지 않는다(O). 앱이 턴 도중 꺼지면 그 턴의 토큰은 재화로만 남고 경험치는 없다 — SPEC F12
  "꺼진 동안의 턴은 재화에만"과 같은 결과로 수용한다.

TA(2회차 N1)
- TA12-1: 버킷 x=0 → xp 0, x=1,048,575 → 20(상한), x=2^30 → 20.
- TA12-2: Stop 뒤 2초 안에 늦게 읽힌 같은 턴의 델타(`ts ≤ s`)가 그 턴 경험치에 포함되고, `ts > s`인 델타는 다음 턴으로 간다.
- TA12-3: n호기 토큰 x1과 메인 토큰 x2가 한 턴에 있으면 xp = `min(log2(1+x1+x2), cap)` 1회(따로 계산하지 않음).
- TA12-4: Stop 없이 SessionEnd로 퇴근하면 남은 버킷이 1회 정산되고, `permission` 상태에서 T로 퇴근하면 xp 무변경.
- TA12-5(3회차 #9): 널 세션의 한 턴에서 메시지 m1·m2(ts < 교체 시각) 뒤 미쿠로 교체되고 m3·m4·m5(ts ≥ 교체 시각) 뒤 Stop이 오면,
  재화는 m3~m5의 토큰만 늘고 미쿠의 xp는 `min(log2(1 + (m3+m4+m5)), cap)` 1회만 늘어난다(m1·m2는 재화·경험치 0).

### F13. 띠 UI

**창**(위임 답):
- 최상위 `QWidget` 1개(`BandWindow`), 플래그 `Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool`(작업
  표시줄 숨김), 속성 `Qt.WA_TranslucentBackground`, `Qt.WA_ShowWithoutActivating`. PokePet과 같은 조합(2.4).
- 크기: 아트 좌표계 기준 방 높이 48px + 말풍선 여유 24px = 72px, 폭 = `16(왼벽) + 40 × 바닥 슬롯 수 + 32(문) +
  16(오른벽)`. 화면 크기 = 아트 px × 정수 배율 S(설정 2/3/4, 기본 3[기본값]). 등급이 오르면 폭이 늘어난다.
- 위치: 기본 = 주 모니터 `availableGeometry()`(작업 표시줄 제외 영역)의 왼쪽 아래에 붙임. 방 배경을 왼쪽 버튼으로
  끌면 이동(캐릭터 위가 아닐 때), 놓으면 위치를 세이브 `settings.band_pos = {screen_name, x, y}`에 저장. 띠 안의
  캐릭터 순서를 바꾸는 드래그는 없다(SPEC F13).
- **클릭 통과**: 방 영역 밖(말풍선 여유 띠의 빈 곳, 투명 픽셀)은 클릭이 아래 창으로 지나가야 한다. 1안 = 알파 0
  픽셀 통과(Windows 레이어드 창의 기본 동작으로 기대, M7). 1안이 실측에서 실패하면 2안 = `setMask(QRegion)`을
  "방 사각형 ∪ 현재 말풍선 사각형들"로 말풍선이 바뀔 때마다 갱신.
- **DPI·모니터**(위임 답): Qt 6 기본(모니터별 DPI 인식 v2)을 쓰고 `QGuiApplication.setHighDpiScaleFactorRoundingPolicy
  (PassThrough)`. 그림은 아트 해상도 `QImage`에 그린 뒤 `round(S × devicePixelRatio)` 배율로 최근접 이웃 확대
  (`Qt.FastTransformation`) — 픽셀 아트가 번지지 않는다. `QWindow.screenChanged`, `QScreen.availableGeometryChanged`,
  `QGuiApplication.screenRemoved`에서 위치를 다시 계산해 화면 안으로 clamp하고, 저장된 `screen_name`의 모니터가
  없으면 주 모니터 기본 위치로 옮긴다. 같은 모니터에서 배율만 바뀌는 경우(디스플레이 설정 변경)는
  `QScreen.logicalDotsPerInchChanged`와 `devicePixelRatio` 값 변화(그리기 직전 이전 값과 비교)로 감지해 다시 계산한다.
  **창 논리 크기는 물리 픽셀에서 역산**한다: 물리 크기 = 아트 px × `round(S × dpr)`, 논리 크기 = 물리 크기 / dpr. 이렇게
  해야 소수 배율(125%·150%)에서도 아트 1px이 물리 정수 픽셀에 맞는다(2회차 N17).
- **트레이**(위임 답): `QSystemTrayIcon` + 메뉴 `상점 / 숙소 / 충원 / 설정 / 정보(크레딧) / 띠 숨기기·보이기 / 종료`.
  왼쪽 클릭 = 띠 보이기·숨기기 전환. "띠 숨기기"는 SPEC F13 6회차가 허용한 **사용자 숨김 예외**다(2회차 L7·N16). 숨긴 동안에도
  엔진·시뮬레이션은 그대로 돌고, 어느 호기가 새로 `asking`/`permission`이 되면 `QSystemTrayIcon.showMessage`로 트레이 알림
  ("미쿠 1호기 · 허락해 주세요" 형식. SPEC F15가 cwd 사용처를 오버레이·단골로 한정하므로 폴더명은 넣지 않는다)을 띄운다. 알림은 호기·상태당 1회, 트레이
  아이콘 자체도 "?"/"!" 배지 아이콘으로 바꾼다. 트레이 아이콘이나 알림을 클릭하면 띠가 복귀한다. 숨김 상태는 세이브
  `settings.band_hidden`에 저장한다.
- **진입점**(위임 답): 띠 오른쪽 위 HUD에 재화 아이콘+잔액, 그 옆 아이콘 4개(상점·숙소·충원·설정). 트레이 메뉴에도
  같은 진입점. 정보(크레딧)는 설정 창의 "정보" 탭과 트레이 메뉴.
- 레이아웃: 왼쪽부터 바닥 슬롯 구역 1..N, 오른쪽 끝에 문. 벽 슬롯은 뒷벽(바닥 슬롯 위). 즐겨찾기 1칸 = 바닥 구역 1.
  위치 배정 알고리즘은 R17 하나(`ui/layout.py`, Qt 없는 순수 함수로 테스트 가능).
- 표시 가능 몸 수 = 현재 등급의 바닥 슬롯 수(C4). 넘치면 "+N" 배지. 표시 순서(O): ① 진짜 캐릭터의 메인 호기(즐겨찾기 →
  선택한 정렬 순) ② 진짜 캐릭터의 n호기(소속 캐릭터 순서 → 호기 번호 오름차순) ③ 배정 없는 몸(정렬 순) ④ 널의 1호기(널 세션
  시작 시각 순) ⑤ 널의 n호기. 잘리는 것은 뒤에서부터. "이름 순" 정렬은 표시 이름을 NFC 정규화한 문자열의 **유니코드 코드 포인트
  순** 비교(로캘 무관, 같으면 합류 순)다.
- 말풍선(2회차 N12): `ui.json`의 `bubble` 표가 상태→말풍선을 정한다. 기본 `{"working": null, "asking": "?", "permission": "!",
  "humming": "~♪", "bored": "…", "off_duty": null}`. 말풍선 그림은 `assets/ui/bubble_<키>.png`.
- 오버레이: 몸 아래 한 줄 `폴더명 · 상태명`(작은 비트맵 글꼴, 설정으로 끔). 널은 끄더라도 "(미배정)" 유지.
- 우클릭 메뉴: 프레임 없는 팝업 `QWidget`(항상 위)에 아이콘 6개(간식·개명·즐겨찾기·쓰다듬기·선물·응원)와 애정
  게이지(단계, 다음 경계까지 막대, MAX). 응원은 `working`이 아니면 비활성. 널 몸은 클릭 이벤트를 무시.
- 애니메이션: 포즈별 프레임 수·fps는 스프라이트 메타데이터. 전역 애니메이션 타이머는 4fps[기본값], 화면에 변화가
  없으면(모든 보이는 몸이 1프레임 포즈이고 자막·말풍선 변화 없음) 타이머를 멈춘다.
- 사운드 API(`QSoundEffect`, `QMediaPlayer`, `winsound`)를 import하지 않는다.

**스프라이트 규격**(PM 요청 제안):
- 몸 프레임 32×32 아트 px, 투명 PNG 시트. 경로 `assets/characters/<char_id>/<skin_id>/sheet.png` +
  `sheet.json`(`{"frame_w":32,"frame_h":32,"poses":{"work":{"row":0,"frames":4,"fps":4,"loop":true}, ...}}`).
- 필수 포즈 키 4종: `work`, `wait`, `rest`, `react`. 선택 키: `sit`, `walk`, `floor_sit`, `talk`, `eat`, `pet`,
  `cheer`, `sleep`, `hum`. 선택 키가 없으면 `poses.json`의 대체 사슬(예 `hum → sit → wait`, `cheer → react`)로 필수
  키에 떨어진다.
- 널: `assets/characters/_null/default/` 같은 규격, 같은 키.
- 가구: 바닥 40×32, 벽 32×24 아트 px, `assets/furniture/<id>.png`. 말풍선·배지·아이콘: `assets/ui/`.
- 플레이스홀더: PNG가 없으면 로더가 캐릭터별 단색 사각형 + 이니셜 프레임을 생성한다(작화 전 개발 가능). 플레이스홀더
  사용 여부는 시작 로그에 남긴다.

TA(2회차 N1)
- TA13-1: `place_bodies`는 Qt 없는 순수 함수이며, 즐겨찾기 미쿠의 1호기가 `working`이면 구역 1, `bored`이면 rest 가구 자리,
  배정 없는 몸이면 rest 가구 자리(구역 1 아님)에 놓인다. 구역 1에 책상이 없으면 `floor_sit` 포즈로 구역 1 바닥.
- TA13-2: 몸 수 > 표시 가능 수일 때 결과 끝에 `+N` 1개, 널 몸은 진짜 캐릭터 몸보다 뒤.
- TA13-3: 띠를 숨긴 상태에서 어느 호기가 `permission`이 되면 트레이 알림이 1회 발생하고, 트레이 클릭 후 띠가 보인다.
- TA13-4: 배율 125%·150% 화면에서 아트 1px의 물리 폭이 모든 열에서 같은 정수다(스크린샷 열 폭 검사).
- TA13-5: 널 몸에 대한 좌·우클릭은 `Engine.command`를 호출하지 않는다.

### F14. 세이브

- 위치: `%APPDATA%\agentview\save.json`, 백업 `save.bak.json`, 임시 `save.json.tmp`, 손상본
  `save.corrupt-YYYYMMDD-HHMMSS.json`. 형식 = UTF-8 JSON(들여쓰기 2), 최상위 `save_version: 1`. 필드 목록은 R18.
- **원자적 쓰기**: tmp에 쓰기 → `flush` → `os.fsync` → `os.replace(tmp, save.json)`. `os.replace`가 `PermissionError`
  (백신·인덱서가 파일을 잡은 경우)로 실패하면 100ms 간격 5회[기본값] 재시도하고, 그래도 실패하면 dirty를 유지한 채 트레이
  알림을 띄우고 다음 디바운스 주기에 다시 시도한다(2회차 N21).
- 쓰기 시점(2회차 N5): 상태가 바뀌면 dirty 표시 후 **디바운스 10초**[기본값](`save.debounce_sec`) — 마지막 변경 뒤 10초
  동안 추가 변경이 없거나 첫 변경 뒤 60초가 지나면 1회 쓴다. 종료(트레이 "종료", Windows 로그오프 `QGuiApplication.commitDataRequest`/
  `aboutToQuit`) 시 즉시 쓴다. 재화 변경마다 즉시 쓰지 않는다 — 토큰 반영과 커서를 한 번의 쓰기로 묶기 위함(F3 크래시 일관성).
- **시작 순서**(SPEC F14 그대로): ① save 읽기·JSON 파싱·스키마 검증 ② 성공 → save를 bak로 복사(덮어쓰기) → 사용
  ③ 실패 → bak 검증 ④ bak 성공 → save를 손상본 이름으로 보존, bak를 save로 복사(bak는 건드리지 않음) → 사용
  ⑤ 둘 다 실패 → 알림 창, save와 bak를 모두 손상본 이름으로 보존, 새 시작(온보딩).
- **버전·마이그레이션**(위임 답): `MIGRATIONS = {1: migrate_1_to_2, ...}` 사슬. 낮은 버전 → 메모리에서 순서대로 변환 후
  검증, 원본을 `save.v<N>.bak.json`으로 보존한 뒤 저장. **앱이 아는 것보다 높은 버전** → 세이브·백업을 수정하지 않고
  "새 버전 앱에서 만든 세이브" 안내 후 종료(덮어쓰면 데이터 손실). 알 수 없는 추가 필드는 그대로 보존(라운드트립).
- **단일 인스턴스**: `QLockFile(%LOCALAPPDATA%\agentview\app.lock).tryLock(0)` 실패 시 `QLocalSocket`으로
  `agentview-<사용자SID 해시>` 서버에 "show" 전송 후 즉시 종료. 세이브 파일을 열기 전에 수행한다. 첫 인스턴스는
  `QLocalServer`로 받아 띠를 앞으로 가져온다.

TA(2회차 N1)
- TA14-1: `store.load` 단위 테스트 5경우 — (정상 save) → bak 갱신 / (깨진 save, 정상 bak) → save 복구·손상본 1개·bak 바이트
  무변경 / (둘 다 깨짐) → `fresh`·손상본 2개 / (save_version 99) → `too_new`·두 파일 바이트 무변경 / (save_version 0 가정의
  구버전 픽스처) → 마이그레이션 후 `save.v0.bak.json` 존재.
- TA14-2: 두 번째 인스턴스 실행 시 `save.json`의 mtime이 바뀌지 않고 프로세스가 3초 안에 종료한다.
- TA14-3: `os.replace`를 모의로 5회 실패시키면 dirty가 유지되고 알림 1회, 6번째 주기에서 성공하면 dirty 해제.
- TA14-4: 디바운스 동안 변경 100회가 있어도 쓰기는 1회.

### F15. 프라이버시

규칙 R12가 단일 원천이다. 구현 요점:
- 트랜스크립트 파서는 줄을 `json.loads`한 뒤 R12의 허용 키만 뽑아 작은 dataclass로 만들고 원본 dict를 즉시 버린다.
  `message.content[]`에서는 `type`·`name`·`id`·`tool_use_id`만 읽는다(`input`·`text`·`content`·`thinking` 미접근).
- 훅 작성기는 stdin JSON에서 허용 필드만 뽑아 쓴다. `tool_input`·`reason`·`background_tasks`·경로 필드는 파일에 쓰지
  않는다.
- `toolDenialKind`·`interruptedMessageId`는 키 존재 여부(bool)만 파서 출력에 남기고 값은 버린다. `entrypoint`는 헤드리스
  판별용 열거값으로 런타임 세션 속성에만 두고 세이브·로그에 쓰지 않는다(2회차 K7, SPEC F15 6회차).
- 로깅(2회차 K5): 앱 진단 로그(`%LOCALAPPDATA%\agentview\logs\app.log`)에는 **세션 ID(또는 경로의 SHA-256 앞 12자 해시)와
  개수만** 남긴다. 트랜스크립트 경로·cwd·폴더명은 로그에 쓰지 않는다. 파싱 실패 줄의 내용을 로그에 찍지 않는다(줄 번호·
  길이만). 로그는 1MB × 3개 회전[기본값].
- 네트워크: 1차 앱은 소켓·HTTP 모듈을 쓰지 않는다(`QLocalSocket`은 로컬 명명 파이프라 예외). 정적 검사로
  `urllib`·`http`·`requests`·`socket`·`QNetwork*` import 금지.
- `~/.claude/.credentials.json`과 `.env*`는 경로 상수로도 두지 않는다. `projects` 이외의 `~/.claude` 하위는
  `settings.json`만 연다(R12).

TA(2회차 N1)
- TA15-1: 정적 검사 스크립트가 네트워크 모듈 import와 `.credentials`·`.env` 문자열 리터럴을 0건으로 보고한다.
- TA15-2: 합성 트랜스크립트 픽스처의 본문 필드(`text`·`input`·`thinking`·`content` 문자열)에 표식 문자열을 넣고 앱을 돌린 뒤,
  세이브·연대기·로그·이벤트 파일 어디에도 표식이 없다.
- TA15-3: 합성 훅 stdin에 `tool_input`·`reason`을 넣어도 이벤트 파일 줄의 키 집합은 R10과 정확히 같다.

### F16. 온보딩·훅 설치

**훅 명령과 인터프리터 의존**(PM 질문 답): 배포본은 PyInstaller로 실행 파일 2개를 만든다 — `agentview.exe`(GUI)와
`agentview-hook.exe`(표준 라이브러리 전용 훅 작성기, PySide6를 import하지 않음). 훅 명령은 `agentview-hook.exe`의
절대 경로를 부르므로 **Python 인터프리터에 의존하지 않는다**. 개발 실행에서는 같은 스크립트를
`"<venv python.exe>" -I "<repo>\agentview\hook\hook_writer.py"`로 부른다(설치기가 실행 모드를 보고 선택).
**배포 형태**(2회차 N19): 두 실행 파일 모두 PyInstaller **onedir**(onefile은 매 실행마다 임시 폴더에 풀어 시작이 느리고 백신
오탐이 잦다). 훅 exe는 같은 설치 폴더의 하위 폴더 `hook\agentview-hook.exe`에 둔다.

**명령 형식**(2회차 N18: `--out` 제거):
```
"C:/…/hook/agentview-hook.exe" --av-hook agentview-v1 --event <이벤트명> [--kind idle_prompt]
```
경로는 슬래시로 쓰고 큰따옴표로 감싼다(cmd·bash 어느 쪽으로 실행돼도 같은 의미가 되도록, M2). `--av-hook
agentview-v1`이 **앱 소유 표지**다. 이벤트 디렉터리는 명령행에 넣지 않고 훅 exe가 `%LOCALAPPDATA%` 환경 변수를 직접 읽어
`%LOCALAPPDATA%\agentview\events`로 정한다 — 비ASCII 사용자 이름의 프로필 경로를 settings.json 명령 문자열과 셸 인용에 실을
필요가 없게 하기 위함이다(M2에 비ASCII 경로 실측 포함). 명령에 남는 경로는 설치 폴더 하나뿐이고, 설치 폴더에 비ASCII가 있으면
설치기가 경고한다.

**설치 항목**(F1 매핑표의 이벤트, 8그룹):

| 이벤트 | matcher | 인자 |
|---|---|---|
| PermissionRequest | 없음(전체) | `--event PermissionRequest` |
| PostToolUse | 없음 | `--event PostToolUse` |
| PostToolUseFailure | 없음 | `--event PostToolUseFailure` |
| Stop | 없음 | `--event Stop` |
| SessionEnd | 없음 | `--event SessionEnd` |
| SubagentStart | 없음 | `--event SubagentStart` |
| SubagentStop | 없음 | `--event SubagentStop` |
| Notification | `idle_prompt` | `--event Notification --kind idle_prompt` |

각 훅 객체: `{"type":"command","command":…,"async":true,"timeout":10}`.

**병합 절차**(위임 답, `hook/installer.py`):
1. 동의 버튼을 누르기 전에는 settings.json을 쓰지 않는다(읽기만).
2. 읽기: UTF-8(BOM 허용). JSON이 아니면(주석 포함 등) 설치 중단·안내, 파일 무변경.
3. 백업(2회차 N20): settings.json **옆에 1개** `settings.json.agentview.bak`(설치·재설치·제거 때마다 덮어씀). 설치 성공을
   확인한 뒤에도 지우지 않고 유지하며, 완료 화면에 "백업 파일 위치와, 이 파일에는 settings.json의 내용(환경 변수·토큰 같은
   시크릿이 들어 있을 수 있음)이 그대로 들어 있으니 공유하지 말라"는 고지를 띄운다. 앱 데이터 폴더로 복사하지 않는다(시크릿이
   담길 수 있는 사본을 늘리지 않기 위함).
4. `hooks`가 없으면 `{}`로 만든다. 이벤트별 배열에서 **표지가 있는 훅 객체를 먼저 모두 제거**(재설치·경로 변경 대응),
   빈 그룹 제거, 그 뒤 위 8그룹을 배열 끝에 추가. 다른 키·다른 훅 객체는 순서까지 보존.
5. 쓰기 직전에 파일 `mtime_ns`를 다시 확인해 읽은 뒤 바뀌었으면 1부터 재시도(최대 3회). 쓰기는 tmp + `os.replace`,
   원본의 개행(CRLF/LF)과 들여쓰기 폭을 감지해 유지.
6. `install_state.json`(`%APPDATA%\agentview\`)에 `{marker, hook_cmd_path, events, installed_at_ms}` 기록.
7. 자가 시험: `agentview-hook.exe`를 합성 stdin(`{"hook_event_name":"AgentviewSelfTest","session_id":"selftest"}`)으로
   직접 실행해 3초 안에 이벤트 파일에 해당 줄이 생기는지 확인. 앱은 `selftest` 세션을 무시한다.

**제거**: 4단계의 "표지 객체 제거"만 수행. 그 결과 `hooks`가 비면 `hooks` 키도 제거. `install_state.json` 삭제.

**설치 상태의 원천**(O): "훅 설치 상태"는 `install_state.json`이 소유한다. 세이브의 `hook` 필드는 화면 표시용 사본이며, 둘이
다르면 `install_state.json`과 settings.json 검사 결과를 따른다.

**경로 변경 감지와 재설치**(2회차 N19): 시작 시 `install_state.hook_cmd_path`와 현재 `build_command()`가 만드는 경로를 비교한다.
다르면(앱 폴더 이동·업데이트) `HookStatus = EXE_MISSING` 또는 `PARTIAL`로 안내 화면을 띄우고, 사용자가 동의 버튼을 누르면 표지
항목을 지우고 새 경로로 다시 추가한다(동의 없이 자동 수정하지 않음).

**앱 삭제와 훅 잔존**(2회차 N19): 앱 폴더만 지우면 settings.json의 훅 항목이 남아 Claude Code가 매 이벤트마다 없는 실행 파일을
부르게 된다(세션은 막히지 않지만 훅 오류가 표시될 수 있음, M2). 대응: ① 설정 화면 "훅 제거" 버튼 ② `agentview.exe
--uninstall-hooks` 명령행(창 없이 제거만 수행) ③ 1차는 설치 프로그램 없이 zip 배포이므로 README·정보 창에 "앱을 지우기 전에
설정 → 훅 제거를 누르세요, 이미 지웠다면 settings.json에서 `--av-hook agentview-v1`이 들어 있는 항목을 지우세요" 안내를 둔다.

**훅 미작동 판정**(위임 답): `HookStatus`(R11) 판정 함수 하나가 다음을 순서대로 검사한다 —
① settings.json 읽기 가능 ② `disableAllHooks`가 true가 아님(M12) ③ 8그룹이 모두 표지와 함께 존재
④ 명령의 실행 파일 경로가 존재 ⑤ 이벤트 디렉터리 쓰기 가능 ⑥ 마지막 자가 시험 성공(시작 시 1회 재실행).
settings.json은 `mtime_ns`가 바뀔 때만 다시 파싱한다. 실행 중 "트랜스크립트 활동은 있는데 훅 이벤트가 없는" 경우는
기본적으로 경고 로그만 남긴다 — 훅 설치 전에 시작된 세션은 훅을 발화하지 않을 수 있기 때문이다(C7, M5).
**훅은 설치됐으나 미발화로 보일 때의 사용자 안내**(O): 설치 시각 이후에 시작된 세션(트랜스크립트 첫 레코드 ts > 설치 시각)에서
트랜스크립트 활동이 5분 이상 이어지는데 그 sid의 훅 이벤트가 0건이면, 게이트는 닫지 않고 트레이 알림 1회와 설정 화면 경고
("훅이 동작하지 않는 것 같습니다 — Claude Code를 다시 시작하거나 `/hooks`에서 확인, 재설치 버튼")를 띄운다. 이 판정은 M5·M12
실측 후 게이트 조건으로 올릴지 다시 정한다.

**온보딩 화면**(3쪽): ① 미쿠 + 방 미리보기 + 설명 3줄(`strings` 키 `onboarding.line1~3`) ② 훅 설치(동의 버튼,
진행 표시, 실패 시 사유와 재시도, 성공 전 "다음" 비활성, "이미 열린 Claude Code 세션은 다시 시작해야 정확히
보입니다" 안내) ③ 비공식·비영리 고지와 크레딧(`credits.json`). 완료 시: 기준선 기록(F3 — 트랜스크립트 커서 +
`event_cursor`를 이벤트 파일 끝으로, 2회차 K3) → 그 전 이벤트를 "상태만" 모드로 재생해 열린 세션 식별 → 세이브 생성 →
연대기 `join`(미쿠) → 열린 세션 배정(`cut_at_ms = 지금`) → 띠 표시.

**크레딧 데이터**: `credits.json` = `{"schema_version":1, "notice":{"ko":…, "en":…}, "groups":[{"id":"crypton",
"characters":["miku","rin","len","luka","kaito","meiko"], "text":…}, {"id":"neru",…}, {"id":"teto",…}, {"id":"una",…},
{"id":"adachi_rei",…}], "footer":…}`. 문구는 `credits_draft.md`를 그대로 옮긴다(일본어 원문 포함, 번역·축약 금지).
로더는 풀의 모든 캐릭터가 어떤 그룹에 속하는지 검증한다.

TA(2회차 N1)
- TA16-1(병합 라운드트립): 임의의 기존 훅·키(합성 픽스처 10종: hooks 없음, 같은 이벤트에 타 훅 있음, CRLF, 들여쓰기 4칸, BOM
  등)에 대해 `install` → `uninstall` 결과가 원본과 의미상 같고(`json.loads` 비교) 개행·들여쓰기 폭도 같다.
- TA16-2: `install`을 두 번 실행해도 앱 항목은 8그룹 하나씩만 있다(중복 0).
- TA16-3: 주석이 든(JSON이 아닌) settings.json에서 `install`은 `ok=False`이고 파일 바이트 무변경, 백업도 만들지 않는다.
- TA16-4: 동의 버튼 전에는 settings.json의 mtime이 바뀌지 않는다. 설치 성공 후 `settings.json.agentview.bak`이 1개 있다.
- TA16-5: `install_state.hook_cmd_path`가 현재 경로와 다르면 `check_status`가 `OK`를 돌려주지 않는다.

### F17. 유휴 성능

- **폴링 주기**(위임 답): 이벤트 파일 2초, 활성 트랜스크립트 stat 3초, **`projects\*`·`subagents` 디렉터리 mtime stat
  3초**(2회차 K2), 전체 트리 탐색 30초(보조), 훅 상태 30초, 게임 틱 1초[모두 기본값]. SPEC F17 "2~5초 범위"는 감지 폴링 3종
  (이벤트·트랜스크립트·디렉터리)에 적용하며, 데이터 로더가 이 3개 값이 2~5초 안인지 검증하고 벗어나면 그 파일을 검증 실패로
  처리한다(O, R13). "활성" = 최근 `T + 1시간` 안에 바뀐 파일 또는 열린 세션의 파일. `subagents` 디렉터리 stat은 활성(열린)
  세션의 것만 한다(3회차 #13).
- 이벤트 파일 정리 직전의 커서 저장은 디바운스가 아니라 `SaveScheduler.flush_now()`로 즉시 쓴다(3회차 #14, F18 6단계).
- **변경 기반**: `os.stat`의 `(st_size, st_mtime_ns)`가 같으면 파일을 열지 않는다. 파일시스템 이벤트
  (`QFileSystemWatcher`/`ReadDirectoryChangesW`)는 쓰지 않는다 — 재귀 감시가 안 되고 하위 폴더 수만큼 핸들이
  늘어나며, SPEC이 폴링으로 정했다.
- 수집(`ingest`)은 `QThread` 작업자 1개에서 실행하고 결과 묶음을 큐로 메인 스레드에 넘긴다. 게임 상태 변경은 메인
  스레드에서만. (이 규칙의 범위는 트랜스크립트·이벤트 파일 읽기다. 세이브·연대기·settings.json 쓰기와 자가 시험은 메인
  스레드에서 동기로 한다 — O.)
- **유휴 CPU 측정 조건**(위임 답): 릴리스 빌드, Windows 11, 세션 0개, 명단 3명(배정 없는 몸 3개가 휴식 애니메이션),
  오버레이 켬, 시작 후 2분 안정화 뒤 10분 측정. 명령 `typeperf "\Process(agentview)\% Processor Time" -si 1 -sc 600`의
  평균 ÷ 논리 코어 수 ≤ 1%. 같은 조건에서 "세션 2개 활성"도 기록(목표 아님, 참고치). 측정 절차는 M8.

TA(2회차 N1)
- TA17-1: `(size, mtime_ns)`가 같은 파일에 대해 폴링 100회 동안 `open` 호출 0회(모의 파일시스템 계수).
- TA17-2: `timing.json`의 감지 폴링 값이 1초 또는 6초면 로더가 그 파일을 검증 실패로 보고 내장 기본값을 쓴다.
- TA17-3: 화면 변화가 없을 때 애니메이션 타이머가 정지 상태다(타이머 `isActive()==False`).

### F18. 앱 꺼짐 처리(따라잡기)

**따라잡기 구현**(위임 답, `core/catchup.py`): 시작 시 훅 상태 OK 확인 후, 띠를 보이기 전에 다음을 수행한다. **훅 안내
화면 구간이 끝나 게이트가 다시 열릴 때도 같은 절차를 그대로 실행한다**(2회차 L1, SPEC F18 6회차 646행 — "꺼진 동안"을
"꺼졌거나 안내 화면이던 동안"으로 읽는다).
1. 이벤트 파일 2단계 재생: 세이브의 `ingest.event_cursor`(파일명, offset) 이전 이벤트는 "상태만" 모드, 이후 이벤트는
   "따라잡기" 모드로 `SessionTracker`에 넣는다. 온보딩 완료(기준선) 때 `event_cursor`가 이벤트 파일 끝으로 초기화되므로,
   기준선 이전 이벤트는 언제나 "상태만"이다 — 열린 세션 식별에만 쓰고 `session_end`·`absence_summary`·단골 갱신을 만들지
   않는다(2회차 K3).
2. 트랜스크립트 커서 이후의 델타를 **전체 트리 탐색(`full_walk=True`)으로** 읽는다(2회차 N23 — 꺼진 동안 생긴 슬러그 폴더·
   하위 에이전트 파일을 빠짐없이 찾기 위함). 각 `TokenDelta`의 재화 처리: 세이브 `null_sessions`에 있던 세션 → 버림. 그 외 →
   재화 지급(기준선 이후이므로, C3 PM 확정, SPEC 7회차 "널 캐릭터가 맡은 세션 제외"와 일치 — 3회차 #5). 경험치는 주지 않는다.
3. 따라잡기 모드에서 생긴 사건을 모아 **발생 시각 순으로** 처리: 숙소 업그레이드 완료(완료 시각), 꺼지기 전 시작된
   세션의 퇴근(`session_end` + 단골 갱신, 퇴근 보너스 없음 C2), 꺼진 동안 시작·종료된 세션은 개수와 재화 합만 모아
   `absence_summary` 1건(시각 = 마지막 그런 세션의 종료 시각, 1건 이상일 때만).
   **SessionEnd 없이 임계로 끝난 세션의 발생 시각**(2회차 K8): `SessionTracker`가 임계 퇴근을 판정할 때의 발생 시각은 "판정한
   now"가 아니라 **마지막 기준 시각 + T**다. 기준 시각은 R1의 해당 행이 쓰는 값(hum_base와 최근 n호기 ts의 최댓값, 또는 마지막
   이벤트·트랜스크립트 활동 ts). 이 가상 퇴근 사건도 위 시각순 병합에 들어간다. 이를 위해 따라잡기 중에는
   `SessionTracker.tick`을 now에 한 번만 부르지 않고, 재생하는 **각 이벤트의 ts 직전마다**(그리고 마지막에 now로) 부른다 —
   그래야 "꺼진 동안 T가 지나 퇴근 → 같은 sid에 새 활동 → 재배정" 순서가 실제 시각대로 재현된다.
   **트랜스크립트 신호도 같은 스트림으로**(3회차 #4): 2단계에서 읽은 트랜스크립트 `activity`·`turn_end`·`ask_open/close` 등의
   신호를 훅 이벤트와 **하나의 시각순 스트림으로 병합**해 재생하고, 그 각 항목의 ts 직전마다 `tick`을 돌린다. 훅 이벤트가 없는
   세션(C7 — 훅 설치 전에 시작된 세션 등)도 이렇게 해야 마지막 활동 ts가 맞게 잡혀 정체 퇴근 시각(기준 + T)이 정확해진다. 토큰
   델타 자체는 이 스트림에서 상태를 바꾸지 않고, 그 메시지 ts 시점의 세션 담당(널 여부)을 R5로 판정하는 데만 쓴다.
4. 아직 열린 세션: 세이브 `session_links`에 퇴근 전 링크가 있으면 `origin="resumed"`(F2 (마) — 저장된 캐릭터·assign_seq 유지,
   `start_recorded`가 true면 `session_start` 재기록 없음, `cut_at_ms = 지금`, 3회차 #1). 링크가 없으면 `origin="startup_inflight"`로
   현재 규칙에 따라 배정(`cut_at_ms = 지금`)하고, 진짜 캐릭터면 `session_start`를 지금 시각으로 기록.
5. 각 사건의 연대기 날짜 = 발생 시각의 게임 날짜(R6).
6. **이벤트 파일 정리**(2회차 K4): 1~5단계가 끝나고 `event_cursor`를 저장한 **뒤에만**, `event_cursor`가 가리키는 파일보다
   **완전히 앞선**(이름순으로 이전이며 커서가 이미 끝을 지난) 파일 중 보존 기간(7일)보다 오래된 것을 지운다. 삭제가
   `PermissionError`(WinError 32, 훅 프로세스가 열고 있음)로 실패하면 무시하고 다음 정리 기회(하루 1회 또는 다음 시작)로 미룬다.
   `event_cursor`가 가리키는 파일과 그 뒤의 파일은 지우지 않는다. 정리 직전의 커서 저장은 디바운스가 아닌 `flush_now()`로 즉시
   디스크에 쓴다(3회차 #14 — 커서가 저장되기 전에 파일이 지워진 채 크래시하면 재생 구간이 사라지므로). 시작 시 커서가 가리키는
   파일이 없으면(수동 삭제 등) 그 날짜 이후의 첫 파일을 offset 0부터 읽는다(3회차 #14).
- **실행 중 시간 공백**(위임 답): 게임 틱마다 `Δmono = time.monotonic() 차`, `Δwall = time.time() 차`. 둘 중 하나라도
  `gap_threshold_sec = 180`[기본값]을 넘으면 그 틱의 시뮬레이션 증가 = 0(벽시계 규칙은 그대로 진행). 공백이 끝나면
  1~3단계를 "따라잡기" 모드로 한 번 더 실행하지 않고 평소 폴링이 이어받는다(파일은 계속 쌓여 있으므로).
- **자동 시작**: HKCU `Software\Microsoft\Windows\CurrentVersion\Run` 값 `agentview` = `"<agentview.exe 경로>"`
  (표준 라이브러리 `winreg`). 설정 체크박스와 레지스트리 실제 값을 시작 시 대조해 표시.

TA(2회차 N1)
- TA18-1(2회차 K8): Stop ts=t0 뒤 앱이 꺼지고 t0+5h에 켜지면 `session_end`의 ts는 `t0+T`(=t0+3h)이고, 같은 구간의 숙소 완료
  사건(t0+2h)보다 뒤, 완료 사건과 시각순으로 기록된다.
- TA18-2(2회차 K8): 꺼진 동안 "T 경과 퇴근 → 같은 sid 새 활동"이 있으면 그 sid는 따라잡기 뒤 새 assign_seq로 열려 있다.
- TA18-3(2회차 K4): `event_cursor`가 가리키는 파일과 그 뒤 파일은 날짜가 오래돼도 지워지지 않는다. 삭제 실패는 예외 없이 넘어간다.
- TA18-4(2회차 L1): 게이트 닫힘 → 이벤트·토큰 발생 → 게이트 열림 시나리오에서 재화 반영·경험치 0·`absence_summary` 규칙이
  앱 재시작 시나리오와 같은 결과를 낸다.
- TA18-5: 공백 임계(180초)를 넘는 틱에서 `sim_ms = 0`, 게임 날짜·업그레이드는 벽시계대로 진행.
- TA18-6(3회차 #4): 훅 이벤트가 전혀 없고 트랜스크립트 활동만 있던 세션(마지막 활동 ts = a)이 꺼진 동안 끝나면, 따라잡기의
  정체 퇴근 사건 시각은 `a + T`이다(now가 아님).

### F19. 시간 흐름

두 시계는 R6이 정의하고 `core/clock.py`가 유일한 구현이다.
- 벽시계: `time.time()`(UTC epoch ms). 게임 날짜 = `floor((now − first_run_ms) / 12h) + 1`, 단 표시값은
  `max(계산값, 세이브의 last_game_day)`로 뒤로 가지 않는다.
- 시뮬레이션 시계: 세이브 `sim_clock_ms`(누적). 틱마다 R6의 규칙으로 증가.
- **시계 역행·전진**(위임 답): 모든 경과 계산은 `elapsed = max(0, now − t)`. 저장된 시각이 미래면(`t > now`) 그 값을
  `now`로 clamp해 세이브에 다시 쓴다. 대상: `last_big_gift_ms`, `streaks.window_start_ms`, `cheer_cooldowns`,
  `dorm.upgrade.started_at_ms`(완료 예정 = started + duration, 남은 시간이 duration을 넘지 않음), `first_run_ms`(역행
  감지 시 clamp하지 않고 `last_game_day`로 날짜만 유지). 전진(시계를 미래로)은 정상 경과로 취급한다(업그레이드 완료,
  날짜 증가). 시뮬레이션은 공백 규칙(180초)에 걸려 증가하지 않는다. 시뮬레이션 증가량은 `max(0, min(Δmono, Δwall))`이라
  역행 틱에서도 음수가 되지 않는다(2회차 K6).

TA(2회차 N1)
- TA19-1: `first_run_ms`부터 12h−1ms는 1일차, 12h는 2일차. 시계를 1일 되돌려도 표시 날짜는 줄지 않는다.
- TA19-2: `Δwall = −10s`, `Δmono = 1s`인 틱의 `sim_ms = 0`. `Δwall = 1s`, `Δmono = 1s`이면 1000.
- TA19-3: 미래로 저장된 `last_big_gift_ms`는 로드 직후 now로 clamp되어 세이브에 다시 쓰인다.

### F20. 콘텐츠 데이터화

**형식**(위임 답): **JSON**(UTF-8) + **JSON Schema(draft 2020-12)** 검증(`jsonschema` 패키지). 근거: 세이브가 JSON으로
정해져 있어 형식을 하나로 통일하고, 표준 라이브러리로 읽을 수 있으며, 스키마를 파일로 함께 배포해 사용자도 같은
기준을 볼 수 있다. TOML(주석 가능)은 쓰기 라이브러리가 표준에 없고, YAML은 의존성과 암묵 타입 변환 위험이 있다.

**파일 목록**(`agentview/data/default/`, 각 파일 최상위 `schema_version`):

| 파일 | 내용 |
|---|---|
| `characters.json` | 캐릭터 풀, 스킨, 널 캐릭터 |
| `strings.ko.json` | 모든 표시 문자열(상태 명칭, 재화 이름, 온보딩 3줄, UI 라벨, "(미배정)", "외 N건") |
| `dialogue.json` | 지목 행동·상태별 대사 키(단계·척도 구간 조건) |
| `chatter.json` | 추상 대화 줄과 간격 |
| `chronicle.json` | 연대기 템플릿, 자막 표시 시간·대기열 상한, 회전 크기 |
| `economy.json` | 환산표, 충원 계단, 간식 비용(50[기본값]) |
| `dorm.json` | 숙소 등급표 |
| `furniture.json` | 가구 행, 기본 가구(침대·책상) |
| `items.json` | 간식류 물건(바게트·가라아게·파 등), 캐릭터×물건 예외(빈 배열) |
| `mood.json` | 척도 수치(F8 표) |
| `affection.json` | 단계·성장 수치 |
| `interactions.json` | 연속 규칙·쿨다운·선물 한도·개명 길이 |
| `timing.json` | 게임 하루 12h, 콧노래 60분, 퇴근 임계 180분, 퇴근 오버레이 10분, 공백 180초, Stop 뒤 유예 3초(`post_stop_grace_sec`, 턴 마감 대기와 같은 키 — 3회차 #11), 폴링 주기(감지 3종 2~5초 검증), 이벤트 보존 7일, 메시지 id 중복 창 7일, 세이브 디바운스 10초 |
| `hook_mapping.json` | 훅 이벤트→상태 매핑(R1의 데이터 부분) |
| `poses.json` | 상태·행동→포즈 키, 대체 사슬 |
| `ui.json` | 정렬 기준 목록(`favorite_affection`, `join_order`, `name`), 기본 배율, 오버레이 기본값, 상태→말풍선 `bubble` 표(2회차 N12) |
| `credits.json` | 크레딧·비공식 고지 |

- **사용자 덮어쓰기**: `%APPDATA%\agentview\data\<같은 파일명>`이 있으면 그 파일 전체가 기본 파일을 대체한다(키 단위
  병합 아님 — 규칙이 단순하고 예측 가능).
- **검증 실패 처리**(위임 답, 2회차 N13): 사용자 파일이 스키마 검증에 실패하면 그 파일만 무시하고 기본 파일을 쓴다.
  **교차 검증(R13)이 실패하면, 실패에 관련된 파일 중 사용자 덮어쓰기 파일을 버리고 내장 기본으로 바꾼 뒤 교차 검증을 다시
  돌린다**(관련 사용자 파일이 모두 내장으로 돌아갈 때까지 반복. 내장끼리는 통과가 보장되어야 함). 어느 경우든 트레이 알림 +
  정보 창에 "적용 안 된 사용자 데이터: 파일명·첫 오류 경로(교차 검증이면 충돌한 상대 파일명)"를 표시한다(조용히 동작하지
  않음). 기본 파일이 실패하면(배포 결함) 오류 창 후 종료.
- 교차 검증(R13): 포즈 키 존재, 크레딧 그룹 포함, 콧노래 < T < 이벤트 보존, 구간 연속성, 등급 상한 비감소 등.
- 문자열 키: 다른 데이터 파일은 표시 문자열 대신 `*_key`를 가진다. 키가 `strings`에 없으면 검증 실패.

TA(2회차 N1)
- TA20-1: 사용자 `mood.json`이 스키마에 맞지 않으면 내장 `mood.json`이 쓰이고 `DataIssue` 1건(파일명 포함)이 생긴다.
- TA20-2: 사용자 `timing.json`이 콧노래 240분(> T 180분)으로 교차 검증에 실패하면 사용자 `timing.json`이 버려지고 내장으로
  재검증 통과, 알림에 `timing.json` 표시.
- TA20-3: 내장 데이터 전체가 스키마·교차 검증을 통과한다(CI 테스트).
- TA20-4: 사용자 `characters.json`에서 캐릭터 1명을 지우고 재시작하면 풀 크기가 9가 되고, 세이브의 그 캐릭터는 고아로 보존된다.

### 위임 목록 답 요약 (SPEC 부록 대조표)

| 위임 항목 | 답 위치 | 답 |
|---|---|---|
| 폴링 주기 | F17 | 이벤트 2초, 트랜스크립트 3초, 디렉터리 mtime 3초, 트리 30초(보조), 훅 상태 30초 [기본값] |
| 훅 이벤트 매칭(짝짓기) | F1 | 호기별 `tool_name` 다중집합, 개수 0이면 해제. 실측 M6 |
| 퇴근 임계 T 기본값 | F1 | 180분 [기본값] |
| 중복 집계 방지 | F3, R3·R4 | sid 키 파일 커서 + 전역 message.id 집합(7일 창) 최대값 델타 |
| 환산표 형식 | F3 | `tokens_per_unit` + `weights`(1차 전부 1) |
| 쾌적도 합산·척도 수치·속도 | F7, F8 | 합계(상한 100), 상승 12/h·하락 6/h, f = 1+0.5·C/100 |
| 척도 경계값 소속 | F8, R15 | 경계값은 위 구간 |
| 애정 단계 경계·성장 수치 | F9 | 6단계, 0/100/300/600/1000/1500, MAX 2000, k=0.35 τ=1h |
| 턴당 경험치 상한 | F12 | 20 [기본값] |
| 개명 글자 수 단위·공백 | R7 | NFC 후 코드 포인트 1~12, 앞뒤 공백 제거, 제어 문자 거부 |
| 대화 간격 기본 범위 | F10 | 120~360초 균등 |
| 크기·위치·클릭 통과·트레이·진입점 | F13 | 아트 72px 높이 × 배율 3, 왼쪽 아래, 알파 통과(대안 마스크), 트레이 메뉴, HUD 아이콘 |
| 해상도·DPI·모니터 변경 | F13 | Qt6 PassThrough + 정수 최근접 확대, 화면 신호로 재배치 |
| 연대기 로그 회전 | F11 | 5MB마다 이름 변경, 삭제 없음 |
| 시계 역행·전진 | F19, R6 | 음수 경과 0, 미래 시각 clamp, 날짜 비감소 |
| 알 수 없는 세이브 버전·스키마 실패 | F14, F20 | 높은 버전 = 무수정 종료, 낮은 버전 = 마이그레이션, 사용자 데이터 실패 = 그 파일만 기본값 + 알림 |
| 로그 경로 변종 | C10 | 범위 밖. 기본 `~/.claude`만 지원, `Paths.resolve`에 분기 자리만(PM 확정) |
| 유휴 CPU 측정 조건 | F17 | typeperf 10분 평균 ÷ 코어 ≤ 1% |
| 데이터 파일 형식 | F20 | JSON + JSON Schema |
| 따라잡기 구현 | F18 | 2단계 재생 + 이벤트 ts마다 tick + 시각순 사건 처리, 안내 화면 구간에도 동일 적용 |
| 헤드리스 `-p`의 Notification/Stop | F1, M3 | 실측 계획 + 데이터 플래그 대비 |
| 설치 병합 방식 | F16 | 표지 기반 제거 후 추가, settings.json 옆 백업 1개, mtime 재확인 |
| 이벤트 파일 형식·회전 | R10, F18 | 일별 JSONL, 보존 7일, 커서보다 완전히 앞선 파일만 따라잡기 뒤 삭제 |
| 훅 미작동 판정 세부 | F16, R11 | 6단계 검사 |
| (본문 기본값) 간식 척도·애정, 쓰다듬기, 선물 큰 폭·소량, 공백 임계 | F8, F9, F18 | 척도 +5, 애정 3/2/특수+5/30/1, 공백 180초, 애정 초기 0, 쓰다듬기 높은 단계 4 |

---

## 5. 신규 구현 필요 함수 명세 (New Function/Interface Specs)

모든 시각은 epoch ms 정수(`int`). 코어 모듈은 Qt를 import하지 않는다.

### 5.1 훅·수집

| 함수/클래스 | 시그니처 | 설명 |
|---|---|---|
| `hook_writer.main` | `main(argv: list[str], stdin: BinaryIO) -> int` | 항상 0 반환, stdout 무출력. 이벤트 디렉터리는 `%LOCALAPPDATA%` 환경 변수에서 직접 계산(2회차 N18). stdin 전체 읽기 → JSON 파싱(실패 시 이벤트명만 기록) → R10 레코드 1줄 생성 → 추가 쓰기. **1안**(2회차 N4): `ctypes`로 `CreateFileW(path, FILE_APPEND_DATA, FILE_SHARE_READ\|FILE_SHARE_WRITE\|FILE_SHARE_DELETE, OPEN_ALWAYS)` 후 `WriteFile` 1회(줄 전체, 4KB 미만으로 자름) — 추가 전용 핸들의 단일 쓰기는 파일 끝에 붙는다. **2안**(M1 실측 실패 시): 프로세스별 파일 `events/<YYYY-MM-DD>/<ms>-<pid>.jsonl`(**시각 우선** 이름, 3회차 #7 — 이름순이 곧 생성 시각순)에 쓰고, 리더는 날짜 폴더 안 파일들을 이름순으로 읽는다. 모든 예외 삼킴 |
| `installer.check_status` | `check_status(paths: Paths, mode: RunMode) -> HookStatus` | R11 |
| `installer.install` | `install(paths, mode) -> InstallResult` | F16 병합 절차. `InstallResult(ok: bool, reason_key: str | None, backup_path: Path | None)` |
| `installer.uninstall` | `uninstall(paths) -> InstallResult` | 표지 객체만 제거 |
| `installer.self_test` | `self_test(paths, mode, timeout_s=3.0) -> bool` | 합성 이벤트 왕복 |
| `installer.build_command` | `build_command(paths, mode, event: str, kind: str | None) -> str` | 명령 문자열 단일 생성자 |
| `events.EventReader` | `__init__(dir: Path, cursor: EventCursor)`, `poll() -> list[HookEvent]`, `replay_all(until: EventCursor) -> Iterator[HookEvent]`, `cursor -> EventCursor`, `seek_end() -> EventCursor`(기준선, K3), `prune(now_ms, retention_days, saved_cursor: EventCursor) -> int` | 일별 파일을 이름순으로 읽고 마지막 `\n`까지만 소비. 깨진 줄은 건너뛰고 개수만 센다. `prune`은 따라잡기 완료·커서 저장(`flush_now`) 뒤에만 호출되며 `saved_cursor`의 파일보다 완전히 앞선 파일만 지우고 `PermissionError`는 삼켜 다음으로 미룬다(2회차 K4, 3회차 #14). `EventCursor` 정의(3회차 #7): 1안 = `{file: "events-YYYY-MM-DD.jsonl", offset}`. 2안 = `{date: "YYYY-MM-DD", offsets: {파일명: offset}}`(그 날짜 디렉터리에서 읽은 파일별 offset 맵). 2안에서 "커서보다 완전히 앞선 파일" = **날짜 디렉터리가 커서 날짜보다 이전**인 것(디렉터리째 삭제). 커서가 가리키는 파일·디렉터리가 없으면 그 날짜 이후 첫 파일의 offset 0부터 읽는다(3회차 #14) |
| `transcripts.TranscriptScanner` | `__init__(root: Path, cursors: dict[str, FileCursor], seen: SeenIds)`, `watch_session(sid)`, `watch_subagent(sid, aid)`, `poll(now_ms, full_walk: bool) -> ScanBatch`, `baseline_all() -> dict[str, FileCursor]`, `export_state() -> (cursors, seen)` | R3·R4·R12. 커서 키는 `"<sid>"`/`"<sid>/a/<aid>"`(K5), 같은 sid가 여러 슬러그 폴더에 있으면 `"<sid>@<슬러그 sha256 앞 8자>"`로 전환(3회차 #8). 경로는 메모리 캐시만, 세이브·로그 미기록. 3초 디렉터리 mtime 감시(K2, subagents는 활성 세션만 — 3회차 #13). 시작 따라잡기에서는 `full_walk=True`(N23). `poll`은 끝날 때 `last_ingest_ms`를 그 폴링 시작 시각으로 갱신(3회차 #2) |
| `paths.Paths` | `Paths.resolve() -> Paths` | `claude_root`, `projects_dir`, `claude_settings`, `appdata_dir`, `localappdata_dir`, `events_dir`, `save_path`, `data_override_dir`, `chronicle_path`, `log_dir`. 경로 규칙의 단일 원천 |

데이터 모양:

```python
@dataclass(frozen=True)
class HookEvent:          # R10 한 줄
    ts: int; ev: str; sid: str; aid: str | None; tool: str | None
    cwd: str | None; pm: str | None; kind: str | None

@dataclass(frozen=True)
class TokenDelta:
    sid: str; aid: str | None; msg_id: str; ts: int; total: int   # total = 가중 합 증가분

@dataclass(frozen=True)
class TranscriptSignal:
    sid: str; aid: str | None; ts: int
    kind: Literal["activity", "ask_open", "ask_close", "turn_end", "interrupted", "denied"]
    ref: str | None        # ask_open/close의 tool_use id
    # interrupted/denied는 interruptedMessageId/toolDenialKind "키 존재"에서만 생기며 값은 담지 않는다(K7)

@dataclass
class ScanBatch:
    deltas: list[TokenDelta]; signals: list[TranscriptSignal]; cwd_seen: dict[str, str]
    headless: dict[str, bool]   # sid → entrypoint 기반 헤드리스 여부(런타임 전용, 값 문자열은 담지 않음)
```

### 5.2 코어

| 함수/클래스 | 시그니처 | 설명 |
|---|---|---|
| `clock.Clocks` | `tick(wall_ms: int, mono_s: float) -> TickDelta`, `game_day(wall_ms) -> int`, `elapsed(now, t) -> int`, `clamp_future(t, now) -> int` | R6. `TickDelta(wall_ms, sim_ms, gap: bool)` |
| `sessions.SessionTracker` | `apply_event(ev: HookEvent, mode: Literal["state","catchup","live"]) -> list[SessionChange]`, `apply_signals(sigs, mode)`, `tick(now_ms) -> list[SessionChange]`, `view() -> list[SessionView]` | R1. `SessionChange(kind: opened|state|unit_added|unit_removed|closed|turn_end|first_wait, sid, aid, ts, …)`. 임계 퇴근의 `closed.ts` = 기준 시각 + T(K8). 따라잡기에서는 이벤트 ts마다 `tick(ev.ts)`를 먼저 호출(K8) |
| `assign.Assigner` | `__init__(assignable: list[AssignableChar], favorites, regulars)`, `set_assignable(list[AssignableChar])`, `on_opened(sid, cwd, ts, origin: Literal["live_new","resumed","startup_inflight","reopen"]) -> Assignment`, `on_closed(sid, ts) -> Release`, `fill_vacancies(ts) -> list[Assignment]`, `unit_number(sid, aid) -> int`, `is_real(sid, ts) -> bool`, `restore_links(session_links)` | F2. `origin`이 R5의 `cut_at_ms`를 정한다(K1). `"resumed"`(3회차 #1) = 세이브 `session_links`에 퇴근 전 링크가 있는 sid를 앱 시작·게이트 재개 때 다시 볼 때 — 새 배정 없이 저장된 `char_id`·`assign_seq`·`start_recorded`·`first_wait_recorded`를 복원하고 `cut_at_ms = 재개 시각`, `start_recorded`가 true면 `session_start` 미발행. `"startup_inflight"` = 링크 없이 시작·재개 시점에 이미 진행 중. I4 모듈 비의존(N15) |
| `economy.Economy` | `credit_tokens(deltas: list[TokenDelta], is_real: Callable[[str,int], bool]) -> int`, `buy_furniture(def_id) -> TxResult`, `buy_item(item_id, qty=1)`, `recruit(pick: str | None) -> TxResult`, `start_upgrade(now) -> TxResult`, `check_upgrade(now) -> int | None`, `pay_snack() -> TxResult`, `place(iid, slot)`, `unplace(iid)`, `gift_furniture(iid, char_id) -> TxResult` | 모든 재화 변경의 유일한 통로. `TxResult(ok, reason_key, cost)` |
| `characters.CharacterSim` | `sim_tick(sim_ms, unit_states, comfort)`, `talk(char, now) -> Reaction`, `snack(char, now) -> Reaction`, `pet(char, now)`, `gift(char, thing, now)`, `cheer(unit_instance_id, char, now)`, `rename(char, name) -> TxResult`, `toggle_favorite(char, now)`, `add_turn_xp(char, tokens) -> float`, `off_duty_bonus(char)` | F8·F9·F12. `Reaction(kind: normal|like|refuse|full|special_like|special_refuse|invalid, line_key, pose_key)`(N10 `like` 추가). 기본 간식은 `snack(char, now, item_id="_basic")` |
| `roster.Roster` | `members(include_orphans=False)`, `add(char_id, now)`, `is_orphan(char_id)`, `candidates()` | F4 |
| `chronicle.Chronicle` | `record(type, ts, char, params)`, `subtitles() -> SubtitleQueue` | F11 |
| `chatter.Chatter` | `tick(mono_ms, visible_chars) -> ChatLine | None` | F10 |
| `catchup.run` | `run(state: GameState, reader, scanner, now_ms) -> CatchupReport` | F18 |
| `game.Engine` | `__init__(data: GameData, save: SaveModel, paths)`, `startup(now) -> CatchupReport`, `ingest(batch: ScanBatch, events: list[HookEvent])`, `tick(wall_ms, mono_s)`, `command(cmd: Command) -> TxResult`, `snapshot() -> BandModel`, `gate_closed(now)`, `gate_reopened(now) -> CatchupReport`(L1) | 조립자. UI는 `snapshot()`만 그린다. `ingest`는 F1 "같은 틱의 처리 순서"와 보류 큐를 구현(K1) |
| `ui.layout.place_bodies` | `place_bodies(model: BandModel, grade: DormGrade, sort_key: str) -> list[BodyPlacement]` | R17 |

### 5.3 데이터·세이브

| 함수 | 시그니처 | 설명 |
|---|---|---|
| `loader.load_game_data` | `load_game_data(default_dir: Path, override_dir: Path, schema_dir: Path) -> tuple[GameData, list[DataIssue]]` | 파일별 사용자 우선, 실패 시 기본값 + 이슈 |
| `loader.cross_validate` | `cross_validate(data: GameData) -> list[DataIssue]` | R13 |
| `store.load` | `load(paths) -> LoadResult` | F14 시작 순서. `LoadResult(save: SaveModel | None, status: ok|restored|fresh|too_new, notice_key)` |
| `store.write_atomic` | `write_atomic(path: Path, obj: dict, retries=5, retry_ms=100) -> bool` | tmp + fsync + replace, `PermissionError` 시 짧은 재시도 후 False(N21). 세이브·install_state·settings.json 공용(settings는 개행 보존 옵션) |
| `store.SaveScheduler` | `mark_dirty(now)`, `due(now) -> bool`, `flush_now()` | 디바운스 10초·최대 60초(N5) |
| `store.migrate` | `migrate(raw: dict) -> dict` | 버전 사슬 |
| `names.validate_display_name` | `validate_display_name(raw: str, max_len: int) -> tuple[str | None, str | None]` | R7. (정규화된 이름, 오류 키) |

### 5.4 연결 관계

```
hook_writer.exe ──append──▶ events/*.jsonl ──▶ EventReader ─┐
~/.claude/projects/**.jsonl ──▶ TranscriptScanner ──────────┤ (QThread 작업자, 큐)
                                                            ▼
                     Engine.ingest ─▶ SessionTracker ─▶ SessionChange ─▶ Assigner / Chronicle / CharacterSim
                                   └▶ Economy.credit_tokens (is_real = Assigner 판정)
                     Engine.tick(Clocks) ─▶ CharacterSim.sim_tick, Economy.check_upgrade, SessionTracker.tick
                     Engine.snapshot ─▶ BandModel ─▶ ui.layout.place_bodies ─▶ BandWindow.paint
```

---

## 5a. 공유 규칙 표 (Shared Rules)

| # | 규칙 | 단위·의미(정확히) | 단일 소유 함수 | 사용하는 쪽 |
|---|---|---|---|---|
| R1 | 상태 전이 표(아래) | 메인 호기·n호기 상태, 시각은 훅 `ts`(ms) | `sessions.SessionTracker` | catchup, game, ui(표시만) |
| R2 | 토큰 총량 | `message.usage` 최상위 4개 정수 × `weights` 합. 중첩 객체 무시 | `transcripts._usage_total(usage: dict, weights) -> int` | scanner만 |
| R3 | 토큰 중복 기준 | 키 = `message.id`, **전역 집합 1개**(파일 무관), 시간 창 7일(마지막 관측 ts가 `last_ingest_ms − 창`보다 이르면 만료). 지급량 = `max(0, 최신 총량 − 지급한 총량)`. 레코드 `timestamp < max(first_run_ms, last_ingest_ms − 창)`이면 지급 안 함(2회차 N2, 3회차 #2 — 하한은 `now`가 아니라 세이브의 `last_ingest_ms` 기준이라 창보다 긴 꺼짐 뒤에도 그 구간 메시지가 지급됨) | `transcripts.SeenIds.credit(id, total, ts) -> int` | scanner만 |
| R4 | 파일 소비 경계 | 바이트 오프셋, 마지막 `\n`까지. `(size, mtime_ns)` 불변이면 미개봉. 커서 키는 sid 기반(`"<sid>"`, `"<sid>/a/<aid>"`), 같은 sid가 여러 슬러그 폴더에 있으면 `"<sid>@<슬러그 sha256 앞 8자>"`로 전환(3회차 #8), 경로는 재계산·메모리 캐시만(2회차 K5) | `ingest.common.read_new_lines(path, cursor)` | EventReader, TranscriptScanner |
| R5 | 지급 대상 판정 | 기준선 이후 AND 진짜 캐릭터 담당 AND (`cut_at_ms`가 None이거나 메시지 `ts ≥ cut_at_ms`). **컷 단위 = 메시지**(3회차 #9, 사용자 확정 — SPEC 7회차 "컷 시각(교체·배정·재개) 이후 타임스탬프의 메시지부터 재화·경험치 반영, 컷 순간 진행 중이던 턴의 나머지 메시지도 새 캐릭터가 받는다"). `cut_at_ms`: 실행 중 처음 본 새 세션·퇴근 후 재배정 = None(첫 레코드부터), 널→진짜 교체 = 교체 시각, 시작·게이트 재개 시 링크 없이 이미 진행 중(`startup_inflight`) = 배정 시각, 퇴근 전 링크가 있는 재개(`resumed`) = 재개 시각(같은 캐릭터 유지, 3회차 #1). 따라잡기(꺼짐·안내 화면 구간): 재화만, 널 캐릭터가 맡은 세션(저장된 널 목록) 제외(SPEC 7회차 190·646, 3회차 #5). 열림 전 델타는 보류 후 열림 시 판정(2회차 K1) | `assign.Assigner.is_real(sid, ts) -> bool` | Economy, CharacterSim(xp), Engine 보류 큐 |
| R6 | 두 시계 | 벽시계 = `time.time()` ms, 음수 경과 0, 미래 시각 clamp, 게임 날짜 = floor(경과/12h)+1 비감소. 시뮬레이션 = 틱별 **`max(0, min(Δmono, Δwall))`**, 단 둘 중 하나가 180초 초과면 0(2회차 K6). 게이트가 닫힌 동안도 0 | `clock.Clocks` | 전 모듈. 다른 곳에서 `time.time()` 직접 호출 금지(테스트 주입) |
| R7 | 개명 길이 | NFC 정규화 → 앞뒤 공백(`str.strip()`) 제거 → **코드 포인트** 수 1~`max_len`(12). 공백만·제어 문자(Cc)·줄바꿈 포함 시 거부. 중간 공백 허용, 중복 이름 허용 | `names.validate_display_name` | 개명 대화상자, CharacterSim.rename, 세이브 검증 |
| R8 | 폴더 키 | `normcase(normpath(cwd))`. 표시명 = 원본 cwd의 마지막 요소. cwd는 세션의 **첫 관측값으로 고정**(2회차 N22) | `assign.cwd_key(cwd) -> str`, `assign.folder_label(cwd) -> str` | Assigner, ui 오버레이 |
| R9 | 호기 인스턴스 ID | 메인 `"{sid}#m{assign_seq}"`, n호기 `"{sid}#a{agent_id}"` | `assign.unit_instance_id(...)` | 응원 쿨다운, ui 클릭 대상 |
| R10 | 이벤트 레코드 | 한 줄 JSON `{"v":1,"ts":ms,"ev":str,"sid":str,"aid":str|null,"tool":str|null,"cwd":str|null,"pm":str|null,"kind":str|null}`, UTF-8, `\n` 종료, 파일 `events-YYYY-MM-DD.jsonl`(UTC, 2안이면 `events/<날짜>/<ms>-<pid>.jsonl` — 시각 우선, 3회차 #7). 커서: 1안 `{file, offset}`, 2안 `{date, offsets{파일명: offset}}`. 정리: 보존 7일 경과 AND `event_cursor`보다 완전히 앞선 파일(2안은 커서 날짜보다 이전 날짜 디렉터리)만, 따라잡기 완료·`flush_now` 커서 저장 뒤 앱이 삭제, 열린 파일 삭제 실패는 다음으로 미룸(2회차 K4, 3회차 #14). 커서 파일이 없으면 그 날짜 이후 첫 파일 offset 0부터 | 쓰기 `hook_writer.make_record`, 읽기 `events.parse_record`, 정리 `events.EventReader.prune` | — |
| R11 | 훅 상태 | `OK / SETTINGS_UNREADABLE / DISABLED / NOT_INSTALLED / PARTIAL / EXE_MISSING / EVENTS_DIR_UNWRITABLE / SELFTEST_FAILED` | `installer.check_status` | App 게이트, 설정 화면, 온보딩 |
| R12 | 허용 필드(프라이버시) | 트랜스크립트: 2.2 표의 필드만(`toolDenialKind`·`interruptedMessageId`는 키 존재 bool만, `entrypoint`는 헤드리스 판별 런타임 전용 — SPEC F15 6회차). 훅: R10 필드만. cwd는 오버레이·단골에만, 연대기·로그·트레이 알림 금지. 진단 로그에는 sid 또는 경로 해시만(2회차 K5·K7) | `transcripts._extract`, `hook_writer.make_record` | 리뷰·정적 검사 |
| R13 | 데이터 교차 검증 | 콧노래 < T < 보존 기간(T < 7일), 중복 창 ≥ 1일, 감지 폴링 3종 2~5초, `pet_high_stage_min` ∈ [1, 단계 수], `items`에 `"_basic"` 행 금지, 구간 연속, 등급 비감소, 키 존재. 실패 시 관련 사용자 파일을 버리고 내장으로 재검증(2회차 N13) | `loader.cross_validate` | 로더 |
| R14 | 고아 판정 | 세이브 항목의 id가 현재 데이터에 없으면 고아. 숨김·신규 차단, 세이브 보존 | `roster.is_orphan`, `economy.is_orphan_furniture` | ui, Assigner |
| R15 | 척도 구간 | v<33 low, 33≤v<67 mid, v≥67 high(경계는 데이터) | `characters.mood_band(v, bands) -> str` | 대사 선택, 애정 배수, 표정 |
| R16 | 연대기 기록 자격 | 메인만, 진짜 캐릭터만, `session_end`는 그 배정 회차에 `session_start`가 기록된 세션만, `first_wait`는 **배정 회차(assign_seq)마다** 첫 asking/permission 1회(2회차 L4). 크래시 재생 중복은 key(`sid|type|ts`)로 제거(N5) | `game.chronicle_eligible(change, assignment) -> bool` | Engine |
| R17 | 몸 위치 배정 | 표시 우선순위: 진짜 메인 호기(즐겨찾기 → 정렬 기준) → 진짜 n호기(캐릭터 순 → 번호) → 배정 없는 몸 → 널 1호기 → 널 n호기. 즐겨찾기 1칸 = 가장 최근 즐겨찾기 캐릭터의 **1호기가 working/humming일 때만**(배정 없는 몸·bored·퇴근 몸은 해당 없음, 2회차 L2). 1칸에 책상(use=work 가구)이 없으면 그 구역 **바닥에 앉아 일함**(`floor_sit` 포즈). 상태 위치가 즐겨찾기보다 우선(asking/permission=문 앞, bored·쉬는 몸=rest 가구 → 없으면 바닥 걷기·앉기). 이름 정렬 = NFC 후 유니코드 코드 포인트 순 | `ui.layout.place_bodies` | BandWindow |
| R18 | 세이브 필드 | 아래 목록 | `save.schema.json` + `store` | 전 모듈 |
| R19 | Stop 뒤 활동 유예 | `humming`/`bored` → `working`은 활동 `ts > hum_base + G`(G = 3초)일 때만. 읽은 순서가 아니라 ts 비교(2회차 K9) | `sessions.SessionTracker` | — |
| R20 | 말풍선 | 상태→말풍선 표 `ui.json.bubble`(working 없음 / asking ? / permission ! / humming ~♪ / bored … / off_duty 없음)(2회차 N12) | `ui.sprites.bubble_for(state)` | BandWindow, 트레이 배지 |

**R1 상태 전이 표**(메인 호기, `hook_mapping.json`이 이벤트→동작을 정의하고 아래 의미를 코드가 구현):

| 현재 | 입력 | 다음 | 부수 |
|---|---|---|---|
| (없음)/off_duty | 활동(훅 이벤트 아무거나, 트랜스크립트 `activity`) | working | `opened`(재배정). off_duty에서 오면 같은 처리 묶음 안에서 **`closed`(직전 회차) 부수효과를 모두 끝낸 뒤** `opened`를 발행한다 — 풀 복귀 → `fill_vacancies` → 이 세션 재배정 순(O) |
| any(off_duty 제외) | PermissionRequest(aid 없음) | permission | 다중집합 +1, `first_wait` 후보 |
| permission | PostToolUse/Failure(같은 tool, aid 없음) | 다중집합 비면 asking 여부 → asking 또는 working | |
| any | 트랜스크립트 `ask_open` | permission이면 유지, 아니면 asking | `first_wait` 후보 |
| asking | `ask_close` | 다중집합 비면 working | |
| permission | 트랜스크립트 `denied`(`toolDenialKind` 키 존재, 보조, SPEC F15 6회차 허용) | 다중집합 비움 → working | |
| any(off_duty 제외) | Stop(aid 없음) | humming(n호기 working 있으면 표시는 working) | 다중집합·asking 비움, `turn_end`, hum_base = ts |
| working | (보조) 트랜스크립트 `turn_end` 또는 `interrupted`(`interruptedMessageId` 키 존재) **그리고** 이후 Notification(idle_prompt) | humming(hum_base = 트랜스크립트 신호 ts) | `turn_end`(C5, SPEC F15 6회차 허용) |
| humming | now − max(hum_base, 최근 n호기 ts) ≥ 60분 | bored | |
| humming/bored | 위 기준 ≥ T | off_duty | `closed`, 발생 시각 = 기준 + T(K8). 남은 버킷 퇴근 정산(3회차 #10) |
| asking/permission | now − 마지막 이벤트 ts ≥ T | off_duty | `closed`, 발생 시각 = 마지막 이벤트 ts + T(K8). 방치 퇴근 → 턴 버킷 폐기 |
| working | now − 마지막 활동 ts ≥ T 이고 working n호기 없음 | off_duty | `closed`(정체, C1 PM 확정), 발생 시각 = 마지막 활동 ts + T. 턴 버킷은 퇴근 정산(L5) |
| humming/bored | 활동 **`ts > hum_base + G`**(R19, G=3초) | working | `ts ≤ hum_base + G`면 상태 유지·마지막 이벤트 시각만 갱신(K9) |
| any | SessionEnd | off_duty | n호기 전부 제거, `closed`. 직전이 **working·humming·bored면** 버킷 퇴근 정산, asking/permission이면 폐기(L5, 3회차 #10 — T 경과 퇴근과 같은 조건으로 통일) |

n호기: SubagentStart → working(`unit_added`). aid가 있는 PermissionRequest → permission, 같은 aid·tool의 PostToolUse →
다중집합 비면 working. aid가 있는 도구 이벤트 → last_ts 갱신. SubagentStop → 제거(`unit_removed`). 마지막 이벤트로부터 T
경과 → 제거. 메인 off_duty → 전부 제거.

**R18 세이브 필드**(`save_version: 1`): `first_run_ms`, `last_game_day`, `sim_clock_ms`, `onboarded`,
`economy{balance:int, token_remainder:int}`, `roster[]{char_id, join_seq, joined_at, skin_id, display_name}`,
`favorites[]{char_id, at_ms}`(최근순), `characters{char_id:{mood, affection, g_reset_sim_ms, xp}}`,
`dorm{grade, upgrade|null}`, `furniture[]{iid, def_id, placed|null, owner_char|null, is_default}`, `items{id:count}`,
`session_links{sid:{char_id, assign_seq, assigned_at, cut_at|null, start_recorded, first_wait_recorded, cwd_key}}`
(`start_recorded`·`first_wait_recorded`는 assign_seq가 바뀔 때마다 false로 초기화, 2회차 L4. 퇴근 후 오버레이 시간 + T가 지나면 항목
삭제, O), `null_sessions[]{sid, cwd, started_at}`, `folder_regulars{cwd_key: char_id}`, `cheer_cooldowns{unit_instance_id: ms}`,
`last_big_gift_ms{char_id: ms}`, `streaks{char_id:{action:{window_start_ms, count}}}`,
`ingest{event_cursor{file, offset} | {date, offsets{파일명: offset}}, transcript_cursors{"<sid>"|"<sid>/a/<aid>"|"<sid>@<해시8>…": {offset,size,mtime_ns}}, seen_ids{msg_id:[total, ts]}, last_ingest_ms}`
(`last_ingest_ms`: 마지막 수집 틱 시작 시각, 매 수집 틱 갱신, 기준선 때 `first_run_ms`로 초기화 — R3 시간 창 하한, 3회차 #2. `event_cursor` 2안 형태 3회차 #7.
커서 키 `@해시` 형태 3회차 #8)
(커서 키는 sid 기반·경로 미저장, 2회차 K5. `seen_ids`는 7일 창 안의 것만, 2회차 N2·N5), `gate_closed_at|null`(2회차 L1),
`settings{sort_key, overlay, scale, band_pos, band_hidden, autostart}`, `hook{installed, installed_at_ms, last_selftest_ok}`(표시용 사본,
원천은 `install_state.json`). `turn_bucket`은 저장하지 않는다(O).
캐릭터별 스킨 칸 = `roster[].skin_id`.

---

## 5b. 외부 서비스 설정 점검표 (External Service Checklist)

외부 클라우드 서비스는 없다. 대신 앱이 의존하는 로컬 외부 시스템(Claude Code 설정)을 점검한다.

| 설정 | 없으면 깨지는 것 | 보이는 증상 | 확인 상태 |
|---|---|---|---|
| `~/.claude/settings.json`의 `hooks`에 앱 8그룹 | 상태 판정 전부 | 앱이 설치 안내 화면만 표시(`NOT_INSTALLED`/`PARTIAL`) | 구조는 S6 기준, 실행 미확인 |
| `agentview-hook.exe` 경로 유효(앱 이동·재설치 후) | 훅이 실패해도 세션은 계속(비차단) → 이벤트 없음 | `EXE_MISSING`; `install_state` 경로 ≠ 현재 경로면 동의 후 재설치 안내(2회차 N19) | 설계 |
| 앱 삭제 후 settings.json에 훅 잔존 | Claude Code가 없는 exe를 매번 호출 | 훅 오류 표시 가능(세션 비차단) | 안내 문구·`--uninstall-hooks`(N19), 증상은 M2 |
| settings.json 백업 `settings.json.agentview.bak` | 병합 실수 복구 불가 | — | 시크릿 포함 가능 고지(N20) |
| `disableAllHooks: true`가 아님 | 모든 훅 미발화 | `DISABLED` | M12 |
| 관리자 정책(관리형 설정의 훅 제한) | 사용자 훅 미발화 | 자가 시험은 성공하는데 이벤트가 안 옴 | M12 |
| 훅 적용 시점(세션 시작 시 스냅샷 여부) | 설치 전 열린 세션은 이벤트 없음 | 해당 세션은 트랜스크립트 기반 working/"?"만 | M5 |
| 훅 실행 셸(Windows에서 cmd/bash) | 명령 인용이 깨지면 미실행 | 이벤트 없음, Claude Code 훅 오류 표시 | M2 |
| 이벤트 디렉터리 쓰기 권한 | 기록 실패 | `EVENTS_DIR_UNWRITABLE` | 설계 |

설치 순서: (사용자만 가능) 온보딩에서 동의 버튼 → 앱이 병합·자가 시험 → (사용자만 가능) 이미 열린 Claude Code 세션
재시작 권장. 제거: 설정 → "훅 제거" → 앱이 표지 항목만 삭제.

---

## 5c. 소유권 맵·인터페이스 계약 초안 (Ownership Map & Contract Draft)

이 절이 5절과 다르면 이 절이 이긴다. 파일마다 소유자 1명. 저장소 루트 아래 패키지 `agentview/`.

| 구현자 | 접두사(테스트·Qt objectName·로거 이름) | 소유 파일 |
|---|---|---|
| I1 기반 | `av_base` | `agentview/paths.py`, `agentview/core/clock.py`, `agentview/names.py`, `agentview/errors.py`, `agentview/data/loader.py`, `agentview/data/default/*.json`, `agentview/schemas/*.schema.json`, `agentview/save/store.py`, `agentview/save/migrations.py`, `agentview/platform/win.py`(자동 시작), **공유 타입 파일 전부**(`agentview/ingest/types.py`, `agentview/core/types_sess.py`, `agentview/core/types_game.py`, `agentview/data/types.py`, `agentview/save/types.py`), `pyproject.toml`, `requirements.txt`(PySide6, jsonschema, pyinstaller[개발]), `scripts/check_imports.py`(금지 import·금지 문자열 정적 검사), `tests/base/*` |
| I2 훅·수집 | `av_ingest` | `agentview/hook/hook_writer.py`, `agentview/hook/installer.py`, `agentview/ingest/common.py`, `agentview/ingest/events.py`, `agentview/ingest/transcripts.py`, `agentview/ingest/worker.py`(QThread 래퍼), `packaging/agentview-hook.spec`, `tests/ingest/*`(트랜스크립트 픽스처는 합성 데이터만) |
| I3 세션·배정 | `av_sess` | `agentview/core/sessions.py`, `agentview/core/assign.py`, `agentview/core/catchup.py`, `tests/sessions/*` |
| I4 게임 규칙 | `av_game` | `agentview/core/economy.py`, `agentview/core/roster.py`, `agentview/core/characters.py`, `agentview/core/chronicle.py`, `agentview/core/chatter.py`, `agentview/core/game.py`(Engine), `tests/game/*` |
| I5 UI | `av_ui` | `agentview/app.py`, `agentview/ui/*.py`(band, layout, sprites, menus, shop, dialogs, onboarding, install_guide, tray, settings), `agentview/assets/**`(플레이스홀더 포함), `packaging/agentview.spec`, `README.md`(훅 제거 안내 포함), `tests/ui/*` |
| team-lead | — | `tests/integration/*`(엔드투엔드 시나리오·실측 스크립트 M1~M13), 통합 시 공유 타입 변경 승인 |

**공유 계약**:
- 데이터 모양(2회차 N14로 소유자 변경): 공유 타입 파일 5개는 **모두 I1 소유**다. 내용 — `ingest/types.py`: `HookEvent`·
  `TokenDelta`·`TranscriptSignal`·`ScanBatch`·`FileCursor`·`SeenIds` 모양 / `core/types_sess.py`: `SessionChange`·`SessionView`·
  `Assignment`·`AssignableChar` / `core/types_game.py`: `BandModel`·`Command`·`TxResult`·`Reaction` / `data/types.py`: `GameData`·
  `DataIssue` / `save/types.py`: `SaveModel`. 다른 구현자가 필드를 바꿔야 하면 I1(통합 단계에서는 team-lead)에게 요청한다.
  모두 `@dataclass`, 시각은 `int` ms. I1이 이 5개 파일을 가장 먼저 내놓는다.
- 오류 규칙: 코어 함수는 사용자 행동 실패를 예외가 아니라 `TxResult(ok=False, reason_key=...)`로 돌려준다. `reason_key`는
  `strings.ko.json`의 키. 파일 I/O 오류는 `agentview.errors.AvIOError`(I1 소유)로 감싸 올린다. 훅 작성기는 예외를 절대
  밖으로 내보내지 않는다.
- 스레드 규칙: **트랜스크립트·이벤트 파일 읽기**는 I2의 작업자만 하고, 결과는 `queue.SimpleQueue`로 메인 스레드에 전달.
  데이터·세이브 로드(시작 시 1회), 세이브·연대기·settings.json 쓰기, 자가 시험은 메인 스레드에서 동기로 한다(O — 규칙 범위
  명시). I3·I4 객체는 메인 스레드 전용.
- 배정 입력(2회차 N15): `Engine`(I4)이 `Roster`에서 고아를 뺀 `list[AssignableChar]`를 만들어 `Assigner.set_assignable`로 넘긴다.
  I3는 I4 모듈을 import하지 않는다.
- 시간 규칙: R6 — 코어는 `Clocks`가 넘긴 값만 쓴다. 테스트는 가짜 시계 주입.
- 프라이버시 규칙: R12 — I2만 원본 JSON을 만진다. 다른 구현자는 원본 dict를 받지 않는다.
- 진입·시작 순서(`app.py`, I5): 단일 인스턴스 → `Paths.resolve` → `load_game_data` → `store.load` → (온보딩 미완료면
  온보딩) → `check_status` 게이트 → `Engine.startup`(catchup) → 작업자 시작 → 띠 표시 → `QTimer` 1초로 `Engine.tick`.
- 금지 import: `agentview/core/**`는 `PySide6` 금지. `hook_writer.py`는 표준 라이브러리 외 금지. 전체에서 네트워크 모듈
  금지(F15).

**권장 디스패치 순서**: ① I1(공유 타입 5개·errors·clock·paths·loader 골격·데이터 기본 파일·pyproject·정적 검사 스크립트)
② I2와 I3를 병렬(둘 다 I1의 타입 파일만 필요) ③ I4(I3의 `Assigner` 인터페이스 필요, 구현 완료는 불필요) ④ I5(전 계약 고정 후,
단 band 그리기와 플레이스홀더 스프라이트는 ①과 병렬 가능) ⑤ team-lead 통합 테스트·실측(M1~M13).

---

## 6. 미확정 사항 (Open Questions)

### 6.1 참고 자료에서 확인됨 (Confirmed from references) — 13건(3회차: 8건 닫힘, 5건 남음)

상태 표기: **[닫힘·PM 확정]** / **[닫힘·SPEC 반영됨]** / **[열림]** / **[기록용]**.

- **C1. [닫힘·PM 확정]** SPEC은 `working` 상태가 이벤트 없이 무한히 남는 경우(Claude Code 프로세스 강제 종료로 Stop·
  SessionEnd 모두 미발화)를 다루지 않는다. PokePet에도 정체 상수(`STALE_WORKING_SECONDS`)가 있다(S5). "마지막 활동부터 T 경과 →
  퇴근"(R1)을 PM이 확정했다. 부작용 — 단일 도구가 T(3시간)보다 오래 실행되면 그 세션이 퇴근 처리된 뒤 다음 활동에서 재배정되고
  퇴근 보너스가 다시 지급될 수 있다 — 도 PM이 수용했다(2회차 L8).
- **C2. [닫힘·PM 확정]** 꺼진 동안 퇴근한 세션의 퇴근 보너스 +3: SPEC F8 "꺼져 있는 동안 척도는 변하지 않는다"를 우선해 따라잡기
  (꺼짐·안내 화면 구간) 중에는 주지 않는다(2회차 L8).
- **C3. [닫힘·PM 확정]** 앱 실행 시점에 진행 중이면서 꺼진 동안 시작된 세션이 시작 시 널을 받는 경우를 포함해, "저장된 널 목록에
  없던 세션의 꺼진 동안 토큰은 지급"(R5)으로 확정(2회차 L8).
- **C4. [열림]** SPEC F13 "몸의 수가 방의 슬롯 수를 넘을 때"의 "슬롯 수"가 바닥 슬롯인지 바닥+벽인지 불명확하다. 몸은 바닥에 서므로
  바닥 슬롯 수로 정했다(데이터 `dorm.grades[].body_capacity`로 따로 지정 가능). 비차단.
- **C5. [닫힘·SPEC 반영됨]** 인터럽트 때 `Stop`이 발화하지 않는다(S6). SPEC F15 6회차가 `interruptedMessageId`를 "키 존재만"
  허용 메타로 추가했다. R1의 "트랜스크립트 턴 종료/인터럽트 + idle_prompt" 보조 전이와 그 턴의 경험치는 유지하고, 값은 저장·
  해석하지 않는다(2회차 K7).
- **C6. [닫힘·SPEC 반영됨]** 수동 거부 전용 훅이 없다(S6). SPEC F15 6회차가 `toolDenialKind`를 "키 존재 여부만, 값은 저장·해석
  안 함"으로 허용했다. 거부 보조 신호(R1)는 키 존재만으로 판정한다(2회차 K7).
- **C7. [열림]** 훅 설치 전부터 열려 있던 세션은 훅을 발화하지 않을 수 있다(M5). 그런 세션은 트랜스크립트만으로 working/"?"를
  표시하고, "!"·콧노래 중은 보조 신호에 의존한다. 온보딩에 재시작 안내를 넣었다. 비차단.
- **C8. [기록용]** SPEC F15의 훅 저장 허용 목록에 `SessionEnd.reason`·`Stop.background_tasks`·`transcript_path`가 없다. 상태 판정에
  필요 없으므로 저장하지 않는다(경로는 다시 계산). 문제 없음 — 기록용.
- **C9. [기록용]** 한 줄 안에 usage가 두 번(최상위·중첩) 나타난다(S2). 문자열 검색식 집계는 두 배가 된다. R2로 최상위만 읽도록 고정했다.
  구현자 주의 사항 — 기록용.
- **C10. [닫힘·PM 확정]** PokePet은 `CLAUDE_CONFIG_DIR` 환경 변수로 `~/.claude` 위치를 바꾼다(S5). SPEC "로그 경로 변종은 범위
  밖"에 따라 기본 `~/.claude`만 지원하고 `Paths.resolve`에 분기 자리만 둔다(2회차 L8).
- **C11. [닫힘·SPEC 반영됨]** SPEC F12 6회차가 "하위 에이전트에는 자기 턴이 없고 토큰은 메인 턴 버킷, Stop 없이 퇴근하면 남은
  버킷을 턴 하나로 정산(방치 퇴근은 재화만)"을 명시했다. F12·R1에 반영(2회차 L5).
- **C12. [기록용]** SPEC F16의 크레딧 고지 취지("공식 일러스트·로고·음성 미사용")는 `credits_draft.md` 4행 문구와 일치하고, 권리자 5그룹이
  풀 10명을 모두 덮는다(S8). 문제 없음 — 기록용.
- **C13. [닫힘·SPEC 반영됨, 3회차 #5]** SPEC F3 190행·F18 646행(6회차)은 안내 화면 구간의 토큰을 "진짜 캐릭터가 배정된 세션만"
  재화로 반영하라고 했고, 그 구간에 새로 시작된 세션은 아직 배정이 없다는 점이 문제였다. PM이 TECH 해석(저장된 널 목록에 없으면
  지급)을 확정했고, SPEC 7회차가 이 괄호를 "널 캐릭터가 맡은 세션 제외"로 바꾼다. R5·F1 게이트·F18 2단계에 반영.

닫힘 8건: C1·C2·C3·C10(PM 확정), C5·C6·C11(SPEC 6회차 반영), C13(PM 확정 + SPEC 7회차 반영, 3회차 #5). 남은 5건: 열림 2건(C4·C7),
기록용 3건(C8·C9·C12).

### 6.2 실측 필요 — 미확정 (Needs measurement) — 13건(2회차: M13 신규, M1·M2·M6·M10 보강)

| # | 항목 | 왜 필요한가 | 실측 방법 |
|---|---|---|---|
| M1 | 여러 훅 프로세스가 동시에 같은 이벤트 파일에 추가할 때 줄이 섞이지 않는지(1안 `CreateFileW(FILE_APPEND_DATA)` + 단일 `WriteFile`, 2회차 N4) | 병렬 도구 호출 시 PostToolUse가 동시에 발화 | `agentview-hook.exe`를 PowerShell `1..50 \| ForEach-Object -Parallel { … }`로 동시 실행(합성 stdin, 줄 길이 3.5KB 포함) → 결과 파일의 모든 줄이 `json.loads` 성공·50줄인지 확인, 10회 반복. 한 번이라도 실패하면 2안(프로세스별 파일 `events/<날짜>/<pid>-<ms>.jsonl`)으로 전환 |
| M2 | Windows에서 훅 명령을 어떤 셸로 실행하는지, 인용·슬래시 경로가 통하는지, 콘솔 창이 깜빡이는지, **비ASCII 경로**(2회차 N18) | 명령이 안 돌면 앱 전체가 무용 | 설치 후 Claude Code 세션에서 Read 한 번 → 이벤트 파일에 `PostToolUse` 줄이 생기는지, `/hooks` 메뉴의 표시, 화면 깜빡임 관찰. 깜빡이면 `--noconsole` 빌드에서 stdin이 들어오는지 같은 방식으로 재시험. 추가: 한글 이름의 Windows 테스트 계정(프로필 `C:\Users\테스트`)에서 같은 시험 — 훅 exe가 `%LOCALAPPDATA%`를 읽어 비ASCII 이벤트 경로에 쓰는지, 설치 폴더가 비ASCII일 때 settings.json 명령이 실행되는지. 앱 폴더를 지운 뒤 세션에서 도구를 써 Claude Code가 어떤 오류를 보이는지(N19 잔존 증상)도 기록 |
| M3 | 헤드리스 `claude -p`에서 `Stop`·`Notification`·`SessionEnd` 발화 여부와 `entrypoint` 값 | -p 세션의 콧노래 중·퇴근 판정 | 빈 임시 폴더에서 `claude -p "1+1만 답해"` 실행 → 이벤트 파일에서 그 sid의 이벤트 종류 확인, 트랜스크립트 `entrypoint` 값을 Grep `-o`로 확인 |
| M4 | `Notification` stdin의 종류 필드명 | 저장 필드(`kind`) 교차 확인 | 시험용으로 `--event Notification`일 때만 stdin의 **키 이름 목록**만 로그에 남기는 디버그 플래그로 실행, 60초 방치해 idle_prompt 유도 |
| M5 | 훅이 세션 시작 시점 스냅샷인지(설치 전 세션에 적용되는지) | C7 안내·미작동 판정 | 세션 A를 연 채 설치 → A에서 도구 실행 → 이벤트 유무. 새 세션 B에서 반복 |
| M6 | 같은 도구 병렬 호출 시 PermissionRequest·PostToolUse의 도착 순서, async 훅의 기록 순서 역전 빈도, **Stop과 같은 턴 PostToolUse의 ts 역전 폭**(2회차 K9) | 짝짓기·정렬 가정 검증, 유예 G(기본 3초) 조정 | 승인이 필요한 Bash 2개를 한 턴에 병렬 요청하게 하고 하나 승인·하나 거부 → 이벤트 파일 순서·ts 확인, "!" 해제 시점 관찰. 추가: 도구를 많이 쓰는 턴 20회를 돌려 "파일상 Stop 뒤에 기록된 PostToolUse"의 (PostToolUse.ts − Stop.ts) 분포와 최댓값, 같은 턴 트랜스크립트 마지막 레코드 `timestamp − Stop.ts`의 최댓값을 구한다. 최댓값이 G보다 크면 G를 그 값 + 1초로 올린다 |
| M7 | 투명 픽셀(알파 0) 클릭 통과가 PySide6 창에서 기본 동작하는지 | 띠 바깥 클릭 통과 | 띠 위 말풍선 여유 영역의 빈 곳을 클릭해 아래 바탕화면 아이콘이 선택되는지 확인. 실패 시 `setMask` 2안 적용 후 재확인 |
| M8 | 유휴 CPU ≤ 1% | SPEC F17 | F17 측정 조건 그대로 `typeperf` 10분. 초과 시 애니메이션 fps·트리 탐색 주기 조정 |
| M9 | 같은 message.id의 여러 줄 중 usage가 다른 경우(스트리밍 중간값)가 있는지 | 최종 usage 기준 확인 | 하네스로 긴 출력을 만든 트랜스크립트에서 Grep `-o`로 id별 `output_tokens` 값 목록 비교(숫자만) |
| M10 | 트랜스크립트가 추가 전용인지(컴팩션·resume 때 재작성·잘림 없음), **resume·continue 시 이전 대화가 새 sid 파일로 복사되는지**(2회차 N2) | 오프셋 커서 가정, 전역 id 집합·시간 창의 필요성 | `/compact`와 `--resume` 전후 파일 크기·첫 1KB 해시 비교(`Get-FileHash`), 크기가 줄었는지 확인. 추가: `claude --resume <sid>`와 `claude --continue`로 이어 간 뒤 새로 생긴 `.jsonl`이 있는지, 있으면 원래 파일의 `message.id` 목록(Grep `-o`로 id만)과 새 파일의 id 목록의 교집합 크기를 센다. 교집합이 있으면 전역 집합이 필요하다는 근거, 복사된 레코드의 `timestamp`가 원본과 같은지도 확인(시간 창 규칙 검증). **추가(3회차 #8): 같은 sid의 `.jsonl`이 2개 이상의 슬러그 폴더에 생기는지**(다른 폴더에서 `--resume <sid>`, 세션 중 `cd` 뒤 재개 등) — PowerShell `Get-ChildItem <projects> -Recurse -Filter <sid>.jsonl`로 개수 확인. 2개 이상이면 F3의 `"<sid>@<슬러그 해시>"` 키 전환이 필요하다는 근거이며, 이때 두 파일의 id 교집합도 센다 |
| M11 | 토큰 분포(응답당·턴당) | `tokens_per_unit`, 경험치 상한, 가격표 재조정(PLANNING B2) | 실제 구현까지 간 프로젝트 트랜스크립트에서 Grep `-o`로 usage 4키 숫자만 추출 → id별 최대 → 턴(`turn_duration` 경계)별 합의 분위수 계산 |
| M12 | `disableAllHooks`·관리형 정책 키의 정확한 이름과 동작 | 훅 미작동 판정 ② | 공식 문서 settings 절 확인 후, 사용자 settings에 `disableAllHooks: true`를 임시로 넣고 자가 시험·실세션 이벤트 유무 비교(시험 후 원복) |
| M13 | **(2회차 신규, K2)** 새 `.jsonl` 생성 시 `projects\<슬러그>`·`<sid>\subagents` 디렉터리 mtime이 바로 바뀌는지(NTFS 디렉터리 mtime 갱신 지연·캐시 여부), 새 슬러그 폴더 생성 시 `projects` mtime이 바뀌는지 | SPEC F1 "감지 주기 이내"·F17 "2~5초" 충족 경로의 가정 | 새 폴더에서 `claude` 세션을 시작하고, 시작 전후로 PowerShell `(Get-Item <dir>).LastWriteTimeUtc`를 0.5초 간격으로 기록 → 파일 생성 시각과 디렉터리 mtime 변화 시각의 차이를 10회 측정. 지연이 3초를 넘거나 바뀌지 않으면 활성 슬러그 폴더의 `scandir`를 3초 주기로 직접 돌리는 방식으로 바꾼다 |

차단 여부: 구현 착수를 막는 항목은 없다. M1·M2·M5·M13은 통합 단계 첫 작업으로 실측해야 하며, M2가 실패하면(훅 명령이 실행되지
않으면) F1·F16의 명령 형식을 바꿔야 하므로 **통합 단계의 첫 관문**이다.
