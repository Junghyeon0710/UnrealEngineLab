# Claude Code용 Unreal Engine Skills 플러그인 — 스킬 목록, 사용법, 효과, 비용

<a id="contents"></a>

## 목차

1. [무엇을 하는 플러그인인가](#what)
2. [들어 있는 것 — 스킬 목록과 훅](#contents-of-plugin)
3. [설치와 사용법](#install)
4. [UE 5.8.4에서 그대로 되는가](#compat)
5. [비용 — 컨텍스트를 얼마나 쓰나](#cost)
6. [효과 — 같은 질문, 플러그인 있을 때와 없을 때](#effect)
7. [좋은 점과 아쉬운 점](#pros-cons)
8. [안전하게 쓰기](#safety)
9. [막히기 쉬운 곳](#pitfalls)
10. [정리](#summary)
11. [검증 기록·재현·참고 자료](#evidence)

---

[Unreal MCP 문서](UnrealMCP.md)에서 에디터와 AI 클라이언트를 연결해 두고 쓰던 중에, Epic이 Claude Code용 플러그인 [unreal-engine-skills-for-claude-code-plugin](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin)을 공개했다. 이름만 보고는 MCP 서버를 하나 더 주는 줄 알았는데, 열어 보니 **도구는 하나도 없고 "도구 쓰는 법"만 들어 있는 플러그인**이었다.

그래서 세 가지가 궁금했다. 무엇이 들어 있는지, 설치하면 Claude가 실제로 다르게 움직이는지, 그 대가로 컨텍스트를 얼마나 쓰는지. 직접 붙여 보고, 같은 질문을 플러그인 있을 때와 없을 때 나눠 물어서 확인했다.

UE **5.8.4 / CL 58902052**(런처 설치본), Windows 10, Claude Code **2.1.251**, 플러그인 **3.1.1**(커밋 `a6aa73a`, 2026-09-17), 측정 모델 `claude-sonnet-5` 기준이다. 2026-10-25에 확인했다.

---

<a id="what"></a>

## 1. 무엇을 하는 플러그인인가

Claude로 에디터를 다루려면 네 가지가 필요하다. 이 플러그인이 주는 것은 그중 마지막 둘뿐이다.

| 필요한 것 | 누가 주나 | 이 플러그인이 주나 |
| --- | --- | --- |
| 에디터 안 MCP 서버 | 엔진의 `ModelContextProtocol` 플러그인 | 아니오 |
| 실제 도구(53개 툴셋, 836개 도구) | `AllToolsets` 등 엔진 툴셋 플러그인 | 아니오 |
| Claude Code 연결 설정(`.mcp.json`) | `ModelContextProtocol.GenerateClientConfig ClaudeCode` | 아니오 |
| 도구를 어떤 순서로, 무엇을 조심하며 쓰는지 | **이 플러그인의 스킬** | 예 |
| 세션 시작 때 "여기는 언리얼 프로젝트"라는 알림 | **이 플러그인의 훅** | 예 |

이 저장소는 이미 `.uproject`에 `ModelContextProtocol`·`AllToolsets`가 켜져 있고, `.mcp.json`에 `unreal-mcp`(`http://127.0.0.1:8000/mcp`)가 등록돼 있었다. 그래서 **설치해도 바꿀 설정이 없었고, 더해지는 건 Claude가 읽는 설명서뿐**이었다.

---

<a id="contents-of-plugin"></a>

## 2. 들어 있는 것 — 스킬 목록과 훅

저장소 전체가 파일 12개, 텍스트 약 64KB다. 실행 파일은 없고, 훅의 bash 스크립트가 유일한 코드다.

| 파일 | 크기 | 언제 읽히나 |
| --- | --- | --- |
| `skills/unreal-mcp/SKILL.md` | 7.1KB (설명 1,015자 + 본문 6,040자) | 에디터를 조작하는 요청일 때 |
| `skills/unreal-mcp/references/setup.md` | 6.1KB | 처음 연결할 때 |
| `skills/unreal-mcp/references/operations.md` | 6.5KB | 도구가 안 보이거나 호출이 실패할 때 |
| `skills/create-toolset/SKILL.md` | 23.3KB | 툴셋을 새로 만들거나 넓힐 때 |
| `skills/unreal-skill/SKILL.md` | 6.9KB | 에디터용 Agent Skill을 만들 때 |
| `hooks/unreal-context.sh` | 3.1KB | 세션 시작(startup·resume·clear)마다 |

스킬의 **설명(description)은 항상 컨텍스트에 실리고, 본문은 Claude가 그 스킬을 부를 때만 실린다.** 이 차이가 5절의 비용에 그대로 나온다.

### 2.1 스킬 목록

| 스킬 | 직접 부를 때 | 하는 일 | 토큰(상시 / 부를 때) |
| --- | --- | --- | --- |
| `unreal-mcp` | `/unreal-engine-skills-for-claude-code:unreal-mcp` | 실행 중인 에디터를 MCP로 조회·수정한다 | 약 430 / 약 2.1천(실측 2,582) |
| `create-toolset` | `/unreal-engine-skills-for-claude-code:create-toolset` | AI가 부를 수 있는 도구(툴셋)를 만들거나 넓힌다 | 약 450 / 약 7.8천 |
| `unreal-skill` | `/unreal-engine-skills-for-claude-code:unreal-skill` | 에디터에 등록되는 Agent Skill을 만들거나 고치거나 검토한다 | 약 440 / 약 2.1천 |

토큰은 설치 후 `claude plugin details unreal-engine-skills-for-claude-code`가 보여 준 추정치다. 상시 합계는 추정 약 1,311, 실측 1,470이다(5절). 차이는 추정에 빠진 훅 문장 몫으로 보인다.

Claude는 요청 내용이 각 스킬의 설명과 맞으면 알아서 부른다. 설명에 적힌 조건을 옮기면 이렇다.

| 스킬 | 저절로 불리는 요청 | 불리지 않는 요청 |
| --- | --- | --- |
| `unreal-mcp` | 레벨 액터 생성·이동·복제, `.uproject` 열기, PlayerStart 주변 배치, 블루프린트·위젯·머티리얼·Niagara·Control Rig·Sequencer·Behavior Tree·GAS 만들기와 편집, 액터 프로퍼티 읽기·쓰기, C++ 수정 후 Live Coding, 메시 에셋 수정. "Unreal"이라는 말이 없어도 `BP_`·`WBP_`·`M_`·`MI_`·`NS_`·`CR_`·`SK_`·`SM_`·`ABP_` 접두사, UE C++ 타입·매크로, Content Browser·Outliner 같은 말이 나오면 해당한다 | 개념·문서 질문, Unity·Godot, 다른 뜻으로 쓴 blueprint·sequencer·widget |
| `create-toolset` | "X에 도구 추가", "MCP로 노출", 새 툴셋·Python 툴셋, `*Tools.cpp/.h/.py`에 static 메서드 추가, `Toolsets/` 폴더 편집 | 이미 있는 도구 호출(`unreal-mcp`), Agent Skill 작성(`unreal-skill`) |
| `unreal-skill` | Agent Skill 만들기·수정·검토, Python 스킬 클래스, 스킬 UAsset, `CreateSkill`·`ListSkills`·`GetSkills`, UE 플러그인의 `Skills/`·`Python/skills/` 안 `SKILL.md` | Claude Code 스킬(`.claude/skills/`) 편집, 툴셋 작성 |

조건이 맞아도 늘 불리지는 않았다. 6절에서 "지침을 찾아 줘" 같은 질문은 스킬 없이 진행됐다. 그럴 때 직접 부르는 방법은 3.6절에 있다.

### 2.2 `unreal-mcp` — 에디터를 다룰 때

핵심은 세 가지다.

**도구는 먼저 찾고 나서 부른다.** 도구 검색이 켜진 서버는 `tools/list`에 `list_toolsets`, `describe_toolset`, `call_tool` 세 개만 보여 준다. `list_toolsets`로 툴셋을 고르고, `describe_toolset`으로 스키마를 읽은 뒤 `call_tool`에 `toolset_name`, `tool_name`, `arguments`를 넣는다. 어떤 툴셋인지 짐작이 가면 목록 조회를 건너뛰고 바로 `describe_toolset`부터 하라고 적혀 있다. 이 흐름은 [Unreal MCP 문서 5절](UnrealMCP.md#discovery)에서 정리한 것과 같다.

**안전 규칙 다섯 개.**

| 규칙 | 내용 |
| --- | --- |
| 저장하고, 또 저장 | 여러 에셋을 건드리기 전과 후에 저장한다. 컴파일을 넘나드는 변경은 되돌리기가 안 될 수 있다 |
| 컴파일 기다리기 | C++이나 셰이더 컴파일 중에는 호출이 멈추거나 이상하게 실패한다. C++ 재빌드는 `LiveCodingToolset.CompileLiveCoding`으로 하고 결과를 기다린다 |
| 호출 순서 지키기 | 서버는 동시 요청을 받지만 완료 순서는 보장하지 않는다. 서로 의존하거나 같은 에셋을 건드리는 호출은 하나씩 보낸다 |
| 결과를 매번 확인 | 블루프린트 컴파일, 위젯 생성처럼 예외 없이 실패 상태만 돌려주는 도구가 있다. 명시적 성공이 아니면 멈춘다 |
| PIE 확인 | 에셋 생성 같은 에디터 전용 도구는 PIE 중에 다르게 동작한다 |

**엔진이 준비한 Agent Skill을 먼저 찾는다.** 엔진과 플러그인은 `AgentSkillToolset`에 작업 지침(Agent Skill)을 등록해 둘 수 있다. 낯선 작업을 시작할 때 `ListSkills`로 목록을 보고, 관련 있으면 `GetSkills`로 읽어서 일반적인 방법보다 우선해 따르라고 한다. **6절에서 플러그인의 효과가 분명하게 나온 건 이 부분 하나였다.**

### 2.3 `create-toolset` — 툴셋을 만들 때

[Unreal MCP 문서 8절](UnrealMCP.md#custom)의 "프로젝트 전용 도구"를 만들 때 쓰는 공식 체크리스트다.

- 좋은 툴셋의 기준: **Clean**(테크니컬 아티스트가 구현을 안 봐도 이해되는 API), **Complete**(set이 있으면 get, create가 있으면 delete), **Composable**(같은 종류에는 같은 타입), **DRY**(`ObjectTools`의 범용 프로퍼티 get/set을 다시 만들지 않는다)
- 만들기 전에: 이미 있는지 → 더 일반적인 문제인지 → 같은 도메인 툴셋이 있는지 → 플러그인을 나눌지 → Python인지 C++인지 순서로 확인한다. Python 스텁(`Intermediate/PythonStub/unreal.py`)에 필요한 API가 있으면 Python을 권한다
- 규칙: 모든 도구는 static, 반환값은 데이터만, 실패는 상태값이 아니라 예외로 알린다. JSON 문자열을 주고받지 말고 실제 타입을 쓴다. 성공 경로와 모든 오류 경로에 테스트를 붙인다(C++ `BEGIN_DEFINE_SPEC`, Python `ToolCallTestCase`)
- 문서 주석: 시그니처만 보고 알 수 있는 내용은 지우고 단위, 범위, 빈 결과의 의미만 남긴다

### 2.4 `unreal-skill` — 에디터용 Agent Skill을 만들 때

Claude Code의 스킬(`.claude/skills/`)이 아니라 **엔진 레지스트리에 등록되는 `UAgentSkill`**을 만드는 법이다. 플러그인 코드와 함께 둘 때는 Python 클래스(`@agent_skill`)로, 프로젝트 전용일 때는 MCP의 `CreateSkill`로 UAsset을 만든다. Novel(도구로 알 수 없는 것만), Durable(바뀌기 쉬운 도구 이름을 박지 않는다), Parsimonious(토큰마다 비용) 같은 원칙이 적혀 있다.

### 2.5 SessionStart 훅

세션이 시작될 때 현재 폴더부터 위로 올라가며 `.uproject`를 찾는다. 이 저장소에서는 다음 문장(372자)을 Claude에게 넣었다.

```text
This working directory is an Unreal Engine project. The project is `UnrealEngineLab.uproject`.
Prefer Unreal Engine conventions (C++/UObject patterns, Slate, UHT reflection) when suggesting code.
Use the `unreal-mcp` skill for tasks that involve driving the Unreal Editor via MCP.
An `.mcp.json` is already present at the project root.
```

`.mcp.json`이 없으면 마지막 문장 대신 `GenerateClientConfig ClaudeCode`를 실행하라는 안내가 들어간다. 언리얼 프로젝트 밖에서는 아무것도 출력하지 않는다. Windows에서는 `bash`가 필요한데, 이 PC는 Git for Windows가 있어서 CLI 실행 기록에 `hook_response`가 `success`로 남았다.

---

<a id="install"></a>

## 3. 설치와 사용법

### 3.1 엔진 쪽을 먼저 맞춘다

플러그인은 `.mcp.json`도 MCP 서버도 주지 않는다. 아래가 이미 돼 있어야 한다. 자세한 과정은 [Unreal MCP 문서 3·4절](UnrealMCP.md#setup)에 있다.

| 항목 | 이 저장소 상태 |
| --- | --- |
| `.uproject`에 `ModelContextProtocol`, `AllToolsets` | 켜져 있음. `AllToolsets`가 없으면 서버는 뜨지만 도구가 0개다 |
| 서버 시작 | 콘솔 `ModelContextProtocol.StartServer`, 실행 옵션 `-ModelContextProtocolStartServer`, 또는 개인 설정 `bAutoStartServer=True` |
| `.mcp.json` | `unreal-mcp`, `http://127.0.0.1:8000/mcp` — 플러그인이 기대하는 이름·포트·경로와 같다 |

### 3.2 설치

혼자 쓸 때는 Claude Code에서 공식 마켓플레이스로 설치한다.

```text
/plugin install unreal-engine-skills-for-claude-code@claude-plugins-official
```

마켓플레이스가 없다고 나오면 먼저 추가한다.

```text
/plugin marketplace add anthropics/claude-plugins-official
```

Claude 앱의 플러그인 목록(Anthropic Directory)에도 Epic 파트너 플러그인 **Unreal Engine Skills**로 올라와 있다.

이 PC에는 터미널에서 CLI로 설치했다. 처음에는 공식 마켓플레이스가 등록돼 있지 않아서 먼저 추가했다.

```powershell
claude plugin marketplace add anthropics/claude-plugins-official
claude plugin install unreal-engine-skills-for-claude-code@claude-plugins-official --scope user
claude plugin list
```

```text
unreal-engine-skills-for-claude-code@claude-plugins-official
  Version: 3.1.1
  Scope: user
  Status: ✔ enabled
```

마켓플레이스 항목은 Epic 저장소의 커밋 `a6aa73a`에 고정돼 있었다. 이 문서에서 읽고 측정한 커밋과 같다. 설치는 **새로 여는 세션부터** 적용된다. 이미 열려 있던 세션에는 스킬이 나타나지 않는다.

팀이나 이 프로젝트에서만 쓰려면 `.claude/settings.json`에 적는다. 폴더를 신뢰한 사람에게 설치 안내가 뜬다.

```json
{
  "enabledPlugins": {
    "unreal-engine-skills-for-claude-code@claude-plugins-official": true
  }
}
```

**사용자 범위로 설치하면 상시 비용 1,470토큰(5절)이 언리얼과 상관없는 프로젝트 세션에도 매번 실린다.** 훅은 `.uproject`가 없으면 조용히 빠지지만 스킬 설명은 그대로다. 이 PC는 언리얼 프로젝트가 여럿이라 사용자 범위로 설치했다. 다른 작업을 더 많이 하는 PC라면 프로젝트 범위가 낫다.

### 3.3 설치 없이 한 세션만 시험하기

설치 전에 시험해 보고 싶으면 저장소를 받아 `--plugin-dir`로 붙인다. 이번 비교도 이렇게 플러그인 유무만 바꿔서 했다.

```powershell
claude --plugin-dir <받은 폴더>
```

### 3.4 확인 순서

1. 에디터를 먼저 켜고 서버를 시작한다(Output Log에서 시작 메시지 확인).
2. Claude Code 세션을 시작한다. 순서가 바뀌면 9절의 첫 번째 증상이 나온다.
3. `/plugin`의 Installed 탭에 `unreal-engine-skills-for-claude-code`가 있는지 본다.
4. `/mcp`에서 `unreal-mcp`가 connected인지 본다.
5. "현재 레벨의 액터 목록 알려줘"처럼 읽기만 하는 요청으로 실제 응답을 확인한다.

### 3.5 에디터 작업 시키기

에디터를 켜 둔 상태에서 평소처럼 요청하면 된다. 대상, 허용할 변경, 확인 방법을 같이 적으면 결과를 비교하기 쉽다.

> 현재 레벨 경로와 액터 이름을 알려줘. 아무것도 수정하거나 저장하지 마.

> `/Game/Blueprints/MovementModes/BP_MovementMode_Slide`의 부모 클래스, 변수, 구현된 함수를 확인해 줘. 수정하지 마.

> 테스트 맵에서 큐브를 하나 만들어 X로 200cm 옮기고, 실제 값을 다시 읽어 확인한 뒤 지워 줘. 맵은 저장하지 마.

위 두 질문처럼 에디터 조작이 분명한 요청에서는 `unreal-mcp` 스킬이 4번 모두 저절로 불렸다(6절). 수정이 들어가는 작업은 스킬의 첫 규칙대로 시작 전에 저장하고 커밋해 둔다.

### 3.6 스킬을 직접 부르기

스킬이 안 불릴 것 같으면 두 가지 방법이 있다.

| 방법 | 예 |
| --- | --- |
| 슬래시 명령 | `/unreal-engine-skills-for-claude-code:unreal-mcp 현재 레벨의 액터 목록 알려줘` |
| 요청 문장에 이름 넣기 | `unreal-mcp 스킬을 참고해서 블루프린트 작업 지침을 찾아 줘` |

설치 후 새 세션에서 슬래시 명령으로 부르자 스킬 본문이 그대로 들어왔다. 문장에 이름을 넣는 방법은 6절에서 2번 중 2번 불렸다. `create-toolset`, `unreal-skill`도 같은 방식으로 부른다.

### 3.7 엔진 Agent Skill 같이 쓰기

블루프린트·머티리얼·Niagara·PCG·야외 조명·Dataflow 작업은 엔진에 지침이 등록돼 있다(4절 목록). 스킬이 로드되면 Claude가 `ListSkills → GetSkills`로 이 지침을 먼저 읽는다.

> unreal-mcp 스킬을 참고해서, 에디터에 등록된 블루프린트 지침을 먼저 읽고 `BP_Door`에 열림 상태 변수를 추가하는 계획만 세워 줘. 아직 수정하지 마.

> unreal-mcp 스킬을 참고해서, Niagara 지침을 확인한 뒤 레벨에 놓을 연기 이펙트 후보만 찾아 줘.

`NiagaraLevelPlacementSkill`은 이펙트를 놓기 전에 "찾기 → 보여 주기 → 확인 받기" 절차를 강제한다. 그래서 바로 배치하지 않고 후보를 먼저 보여 주는 게 정상이다. 첫 호출에서 `AgentSkillToolset` 이름 오류가 나면 9절을 본다.

### 3.8 툴셋 만들기 — `create-toolset`

이 저장소의 `AIWidgetInspector`처럼 프로젝트 전용 도구를 만들 때 쓴다.

> /unreal-engine-skills-for-claude-code:create-toolset AIWidgetInspector 툴셋에 위젯 트리 깊이를 돌려주는 도구를 추가하고 싶어. 먼저 기존 툴셋에 같은 기능이 있는지 확인하고, Python과 C++ 중 무엇이 맞는지 정리해 줘.

스킬은 이 순서로 진행하게 한다.

1. 이미 있는 기능인지 `list_toolsets`·`describe_toolset`이나 `Toolsets/` 폴더에서 찾는다. 있으면 만들지 않는다.
2. 더 일반적인 문제인지 본다. 예를 들어 블루프린트 메타데이터는 블루프린트가 아니라 에셋 전체의 문제라 `AssetTools` 쪽에 둔다.
3. 같은 도메인 툴셋이 있으면 거기에 추가하고, 없으면 플러그인을 나눌지 정한다.
4. 언어를 고른다. `Intermediate/PythonStub/unreal.py`에 필요한 API가 있으면 Python이다. 스텁이 없으면 **Project Settings → Plugins → Python의 Developer Mode**를 켜고 재시작한다.
5. 작성하고 테스트한다. 에디터가 켜져 있으면 `AutomationTestToolset`(`DiscoverTests → ListTests → RunTests → GetTestResults`)으로, 꺼져 있으면 `UnrealEditor-Cmd.exe <프로젝트>.uproject -ExecCmds="Automation RunTests AI.MyToolset;quit" -Unattended -NullRHI`로 돌린다.

C++ 툴셋은 스킬이 `LiveCodingToolset.CompileLiveCoding`으로 컴파일하라고 하는데, 5.8.4에서는 이 툴셋을 따로 켜야 한다(4절).

### 3.9 에디터용 Agent Skill 만들기 — `unreal-skill`

반복하는 작업 순서를 엔진에 지침으로 남길 때 쓴다.

> /unreal-engine-skills-for-claude-code:unreal-skill 파쿠르 코스 측정 절차를 이 프로젝트용 Agent Skill로 만들고 싶어. 비슷한 스킬이 이미 있는지 ListSkills로 먼저 확인해 줘.

| 경로 | 언제 | 만드는 법 |
| --- | --- | --- |
| Python 클래스 | 코드 플러그인과 함께 버전 관리할 때 | `unreal.AgentSkill`을 상속하고 `@agent_skill`을 붙인다. docstring이 설명, `instructions`가 본문이다 |
| UAsset | 이 프로젝트에서만 쓸 때 | MCP의 `CreateSkill`로 `/Game/Skills/` 같은 폴더에 만든다. 코드가 필요 없다 |

이렇게 만든 지침은 Claude Code 스킬과 달리 엔진에 등록된다. 그래서 같은 에디터에 붙는 다른 MCP 클라이언트(Codex 등)도 `ListSkills`로 볼 수 있다.

### 3.10 끄기·업데이트·지우기

```powershell
claude plugin disable unreal-engine-skills-for-claude-code
claude plugin enable unreal-engine-skills-for-claude-code
claude plugin update unreal-engine-skills-for-claude-code
claude plugin uninstall unreal-engine-skills-for-claude-code
```

Claude Code 안에서는 `/plugin` 패널에서 같은 일을 할 수 있다. 훅이 프로젝트를 제대로 찾는지 보려면 환경 변수 `CLAUDE_UE_HOOK_DEBUG`에 아무 값이나 넣고 세션을 시작한다. 탐지 과정이 stderr에 찍힌다.

---

<a id="compat"></a>

## 4. UE 5.8.4에서 그대로 되는가

플러그인 문서에 나오는 명령·설정·도구를 설치된 엔진 소스와 실행 중인 에디터에서 하나씩 찾아봤다.

| 플러그인이 말하는 것 | 5.8.4 설치본 | 확인 방법 |
| --- | --- | --- |
| `StartServer`, `StopServer`, `RefreshTools`, `GenerateClientConfig` | 있음 | 엔진 소스의 콘솔 명령 등록 |
| `GenerateClientConfig` 대상 `ClaudeCode`·`Cursor`·`VSCode`·`Gemini`·`Codex`·`All` | 있음 | 엔진 소스 |
| `bEnableToolSearch`(기본 true), `bAutoStartServer`(기본 false), 8000, `/mcp` | 있음 | `ModelContextProtocolSettings.h` |
| `tools/list`에 메타 도구 3개 | 있음 | 실제 응답 |
| `AgentSkillToolset`의 `ListSkills`·`GetSkills`·`CreateSkill`·`UpdateSkill` | 있음. 엔진 기본 스킬 **20개** 등록 | 실제 호출 |
| `ProgrammaticToolset.execute_tool_script` | 있음 | 실제 호출 |
| `AutomationTestToolset`의 `DiscoverTests → RunTests` | 있음 | 툴셋 목록 |
| `toolset_registry.agent_skill`, `tool_call`, `tests/reload_remote.py` | 있음 | `ToolsetRegistry/Content/Python/` |
| `LiveCodingToolset.CompileLiveCoding` | **엔진에는 있지만 꺼져 있음.** `AllToolsets` 종속성에 없고 `EnabledByDefault`가 false다 | `AllToolsets.uplugin`, 툴셋 목록 |
| `AIAssistantToolset.GetDockedContext` | 이 프로젝트에서는 `AIAssistant` 플러그인이 꺼져 있어 없음 | 툴셋 목록 |
| 프록시 `Extras/Proxy/Bin/Win64/unreal_mcp_proxy.exe` | **런처 설치본에 없음** | `ModelContextProtocol/` 폴더 |

어긋나는 곳은 두 군데였다.

- **Live Coding 컴파일 도구는 따로 켜야 한다.** 스킬은 C++ 재빌드에 `LiveCodingToolset.CompileLiveCoding`을 쓰라고 하지만, `AllToolsets`만 켠 이 프로젝트에서는 목록에 없었다. `.uproject`에 `LiveCodingToolset`을 추가하고 재시작해야 한다.
- **프록시가 없다.** 프록시는 에디터가 꺼졌다 켜져도 Claude 쪽 연결을 유지해 주는 중계 프로그램이다. 이 설치본에는 `Extras` 폴더 자체가 없어서 직접 HTTP 연결을 그대로 써야 했다.

### 엔진에 등록된 Agent Skill 20개

플러그인이 "먼저 찾아보라"고 하는 대상이 이것이다. `ToolsetRegistry.AgentSkillToolset.ListSkills`의 실제 응답을 옮겼다. 켜 둔 플러그인에 따라 목록은 달라지며, 이 프로젝트는 `AllToolsets`로 켰다. 다루는 내용은 각 스킬의 설명을 요약했다.

| 등록한 곳 | 스킬 | 다루는 내용 |
| --- | --- | --- |
| `EditorToolset` | `BlueprintBasicsSkill` | 블루프린트 만들기·수정·검토. 그래프는 DSL로 읽고 쓰기, 노드 타입·핀 이름 추측 금지, 작업 단위가 끝난 뒤 컴파일 |
| `EditorToolset` | `MaterialBasicsSkill` | 머티리얼과 머티리얼 인스턴스 만들기·수정·고르기 |
| `EditorToolset` | `DefaultOutdoorLightingSkill` | 기본 야외 조명(태양, 하늘, 구름, 안개, 노출) 조정 |
| `EditorToolset` | `UnrealSkillBestPracticesSkill` | Agent Skill 작성·수정·검토 원칙 |
| `NiagaraToolsets` | `NiagaraFundamentalsSkill` | 템플릿, 시뮬레이션 대상, 스크립트 스택 순서, 파라미터 네임스페이스, 좌표계 등 기본 규칙 |
| `NiagaraToolsets` | `NiagaraRenderersSkill` | Sprite·Mesh·Ribbon·Light·Decal·Component 렌더러별 설정, 정렬, 조용히 실패하는 머티리얼 의존성 |
| `NiagaraToolsets` | `NiagaraOptimizationSkill` | CPU·GPU 비용 줄이기(시뮬레이션 대상, 이미터 합치기, 바운드, 스케일러빌리티, 풀링) |
| `NiagaraToolsets` | `NiagaraCustomHLSLSkill` | 동적 입력의 인라인 HLSL 문법, CPU VM·GPU 호환, 스코프 규칙 |
| `NiagaraToolsets` | `NiagaraBlueprintInteropSkill` | 블루프린트에서 런타임에 Niagara 구동(스폰 방식, 파라미터 바인딩, 풀링·수명) |
| `NiagaraToolsets` | `NiagaraLevelPlacementSkill` | 연기·불·폭발 같은 게임플레이 VFX 배치 요청 때 "찾기 → 보여 주기 → 확인" 절차 강제 |
| `NiagaraToolsets` | `NiagaraCleanupSkill` | 안 쓰는 모듈·User Parameter를 찾아 지우기 전에 먼저 보여 주기 |
| `PCGToolset` | `Skill_PCGGraphGeneration` | 모든 PCG 그래프 작업의 기본. 반복 패턴·규칙 기반 배치·공간 계산 |
| `PCGToolset` | `Skill_InstantLevelOperations` | 그래프 없이 바로 하는 일괄 배치·트랜스폼·에셋 생성·스플라인 |
| `PCGToolset` | `Skill_PCGAssetZoo` | 에셋을 레벨에 줄 세워 비교하는 에셋 라인업 구성 |
| `PCGToolset` | `Skill_PCGBiomeCore` | PCGBiomeCore 바이옴 시스템 구성 |
| `PCGToolset` | `Skill_PCGBiomeCoreRefinement` | BiomeCore가 아무것도 안 뿌리거나 일부만 생성할 때의 점검 목록 |
| `PCGToolset` | `Skill_PCGInstancingOnMeshActor` | 메시 액터 표면에 인스턴스 뿌리기(그리블). 사용자가 직접 요청할 때만 쓴다 |
| `PCGToolset` | `Skill_PCGMeshPartition` | PCG 기반 3D 지형(MeshPartition) 읽기·쓰기 |
| `PCGToolset` | `Skill_PCGShapeGrammarDefinition` | 스플라인을 따라 절차적으로 레이아웃을 만드는 Shape Grammar |
| `DataflowAgent` | `DataflowGraphEditingSkill` | Dataflow 그래프(시뮬레이션·변형 노드) 생성·편집 |

전체 경로와 원문 설명은 [에디터 확인 결과](Evidence/UnrealEngineSkills/editor_check.json)의 `agent_skills`에 있다.

---

<a id="cost"></a>

## 5. 비용 — 컨텍스트를 얼마나 쓰나

### 5.1 항상 드는 양

도구를 쓰지 않는 질문("OK라고만 답해")을 플러그인 있을 때와 없을 때 한 번씩 보내고, 첫 요청의 입력 토큰을 비교했다.

| 조건 | 플러그인 없음 | 플러그인 있음 | 차이 |
| --- | --- | --- | --- |
| 파일 도구 허용 | 18,636 | 20,106 | **+1,470** |
| MCP 도구만 허용 | 17,174 | 18,644 | **+1,470** |

도구 구성을 바꿔도 차이는 정확히 같았다. 스킬 설명 세 개와 훅 문장이 차지하는 양이다.

### 5.2 스킬을 부를 때

레벨 조회 요청에서 Claude가 `unreal-mcp` 스킬을 부르자 다음 요청의 컨텍스트가 18,706에서 21,288로 **+2,582토큰** 늘었다. 본문 6,318자가 대화에 들어간 것이다.

같은 대화에서 엔진 쪽 조회가 차지한 양과 비교하면 이렇다.

| 들어간 것 | 늘어난 토큰 |
| --- | --- |
| 플러그인 상시 비용 | 1,470 |
| `unreal-mcp` 스킬 본문 | 2,582 |
| `list_toolsets` 응답 한 번 | 6,716 |
| `SceneTools`의 `describe_toolset` 응답 한 번 | 10,680 |

**플러그인 자체는 툴셋 하나의 스키마를 읽는 것보다 작다.** 다만 대화가 길어지면 이 내용이 매 턴 다시 들어가므로 누적량은 더 커진다(6절).

### 5.3 도구 검색이 없었다면

플러그인 스킬이 설명하는 "세 개만 보이는" 구조는 엔진의 도구 검색 기능이다. 플러그인이 없어도 기본으로 켜져 있다. 꺼졌을 때와 비교하면 크기가 이 정도 차이 난다.

| 응답 | 크기 |
| --- | --- |
| 도구 검색이 켜진 `tools/list`(메타 도구 3개) | 1,279 B |
| `list_toolsets`(53개 툴셋 이름·설명) | 15,885 B |
| 836개 도구 스키마 전체 | **1,053,816 B** |

스키마 전체는 1MB가 넘는다. 툴셋 하나도 크다. `BlueprintTools`의 `describe_toolset` 응답은 68,906자여서 Claude Code의 MCP 출력 한도를 넘었고, 결과가 파일로 저장됐다(9절). 크기로 보면 `NiagaraToolset_System`, `SequencerTools`, `ControlRigTools`도 비슷하거나 더 크다.

---

<a id="effect"></a>

## 6. 효과 — 같은 질문, 플러그인 있을 때와 없을 때

### 6.1 어떻게 비교했나

빈 템플릿 맵(`/Engine/Maps/Templates/Template_Default`)을 연 UnrealEngineLab 에디터에 질문 세 개를 각각 두 번씩 물었다. Claude Code를 `claude -p`로 실행하고, 플러그인 유무만 `--plugin-dir`로 바꿨다.

- 저장소의 MCP 문서가 답에 섞이지 않도록 `UnrealEngineLab.uproject`와 `.mcp.json` 사본만 있는 빈 폴더에서 실행했다. 훅은 이 `.uproject`로 언리얼 프로젝트를 인식한다.
- 자동 메모리는 껐고(빈 폴더라 원래 비어 있다), 도구는 Unreal MCP 3개와 `Skill`, `ToolSearch`, `Read`, `Grep`, `Glob`만 허용했다. 수정 도구는 주지 않았다.
- 끝난 뒤 호출 기록과 에셋 dirty 상태를 확인했다. 6.4절까지 합친 30회, `call_tool` 152번 중 저장·수정 호출은 0건이었다.

| 질문 | 정답 |
| --- | --- |
| 1. 현재 레벨 경로와 액터 개수·이름 | `Template_Default`, 16개 |
| 2. `BP_MovementMode_Slide`의 부모 클래스, 변수, 구현된 함수 | `SmoothWalkingMode`, 변수 12개, `GenerateWalkMove` 구현 |
| 3. 블루프린트를 만들기 전에 엔진이 주는 작업 지침 | 엔진 Agent Skill `BlueprintBasicsSkill` |

### 6.2 결과

두 번의 평균이다. 누적 입력 토큰은 매 턴 들어간 컨텍스트를 모두 더한 값이다(대부분 캐시 읽기).

| 질문 | 플러그인 | 정답 | 스킬 호출 | 턴 | MCP 호출 | 도구 오류 | 시간 | 누적 입력 토큰 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1. 레벨 조회 | 없음 | 2/2 | — | 6 | 4 | 0 | 21.9초 | 139,742 |
| 1. 레벨 조회 | 있음 | 2/2 | 2/2 | 8 | 4 | 0 | 22.6초 | 179,573 |
| 2. 블루프린트 조회 | 없음 | 2/2 | — | 17.5 | 9 | 3 | 78.8초 | 397,426 |
| 2. 블루프린트 조회 | 있음 | 2/2 | 2/2 | 21.5 | 12.5 | 5 | 97.7초 | 508,550 |
| 3. 작업 지침 찾기 | 없음 | 0/2 | — | 19 | 2.5 | 0 | 102.2초 | 391,422 |
| 3. 작업 지침 찾기 | 있음 | 0/2 | **0/2** | 18 | 4 | 0.5 | 108.4초 | 720,680 |
| 3. + "unreal-mcp 스킬을 참고해서" | 있음 | **2/2** | 2/2 | 10.5 | 5.5 | 2 | **46.8초** | 238,630 |

질문 3의 "정답"은 엔진의 `BlueprintBasicsSkill`을 찾았는지로 셌다. 못 찾은 실행도 `BlueprintTools`의 그래프 DSL 문서(`get_graph_dsl_docs`)나 도구 설명을 요약해서 답했다. 틀린 내용은 아니지만, 엔진이 블루프린트 작업용으로 따로 준비한 지침은 놓쳤다.

### 6.3 무엇이 달랐나

**도구가 분명한 일은 빨라지지 않았다.** 레벨 조회는 플러그인이 없어도 `list_toolsets → describe_toolset(SceneTools) → get_current_level → find_actors` 네 번 만에 끝났다. 서버가 메타 도구 설명을 충분히 주기 때문이다. 플러그인은 스킬을 읽느라 2턴을 더 썼고 누적 토큰이 **28.5%** 늘었다. 시간 차이는 1초 안쪽이었다.

**블루프린트 조회에서 시간을 잡아먹은 건 플러그인과 상관없는 두 가지였다.** 하나는 68,906자짜리 `BlueprintTools` 스키마가 파일로 넘어가서 Claude가 `Grep`과 `Read`로 다시 뒤져야 했던 것이고, 다른 하나는 `refPath` 형식이다. 네 번 중 세 번(조건과 상관없이)이 `/Game/.../BP_MovementMode_Slide`를 넣었다가 "not a valid object path" 오류를 받고 `...BP_MovementMode_Slide.BP_MovementMode_Slide`로 고쳤다. 스킬에는 이런 세부 내용이 없어서 차이가 나지 않았고, 오히려 플러그인 쪽이 호출을 더 했다.

**차이가 난 건 엔진 Agent Skill이었다.** 스킬이 로드된 실행은 `ListSkills → GetSkills`로 바로 가서 `BlueprintBasicsSkill`을 찾았다. 플러그인이 없는 실행은 다음 절의 실행까지 합쳐 4번 모두 이 목록을 열어 보지 않았다.

**다만 스킬이 자동으로 불리는지는 질문 문구에 달려 있었다.** "에디터에서 확인해서 알려줘"처럼 에디터 조작이 분명한 질문 1·2에서는 4/4 불렸다. 반면 "지침이 있으면 찾아 줘"는 파일을 먼저 뒤지느라 0/2였다. 질문 앞에 "unreal-mcp 스킬을 참고해서"를 붙이자 2/2 불렸고, 시간도 108.4초에서 46.8초로 줄었다.

### 6.4 파일 도구를 막았을 때

처음에는 Claude가 저장소 문서를 못 읽게 하려고 `Read`·`Grep`·`Glob`까지 막고(MCP 도구와 `Skill`, `ToolSearch`만 허용) 저장소 루트에서 돌렸다. 이때는 결과가 꽤 달랐다.

| 질문 | 플러그인 | 정답 | 스킬 호출 | 턴 | 시간 | 누적 입력 토큰 |
| --- | --- | --- | --- | --- | --- | --- |
| 2. 블루프린트 조회 | 없음 | 2/2 | — | 36.5 | 257.8초 | 1,493,462 |
| 2. 블루프린트 조회 | 있음 | 2/2 | 2/2 | 29 | 189.0초 | 1,003,250 |
| 3. 작업 지침 찾기 | 없음 | 0/2 | — | 18 | 176.1초 | 636,355 |
| 3. 작업 지침 찾기 | 있음 | 2/2 | 2/2 | 10.5 | 47.2초 | 222,696 |

파일로 넘어간 스키마를 읽을 수단이 없자 두 조건 모두 없는 도구 이름을 넣어 보며 오류 메시지로 목록을 알아내려 했다. 그 와중에 플러그인 쪽은 스킬을 먼저 읽고 Agent Skill로 바로 갔다. 플러그인이 없는 쪽 하나는 `execute_tool_script`로 저장소의 `Docs/UE/UnrealMCP.md`를 직접 열어 읽었다(8절).

실사용 환경은 `Read`가 열려 있는 6.2절 쪽에 가깝다. **"플러그인이 도구 탐색을 줄여 준다"는 효과는 Claude가 다른 탐색 수단이 없을 때 주로 나타났다.**

---

<a id="pros-cons"></a>

## 7. 좋은 점과 아쉬운 점

### 좋은 점

| 항목 | 내용 |
| --- | --- |
| 엔진 Agent Skill로 가는 길 | 엔진에 이미 등록된 지침 20개를 쓰게 만든다. Niagara·PCG·블루프린트·머티리얼 작업에서 가장 값어치가 있다. 실측에서 효과가 분명했던 유일한 지점 |
| 명시적인 안전 규칙 | 저장, 컴파일 대기, 호출 순서, 결과 확인, PIE 확인. 사람이 매번 말하지 않아도 되는 기본값이 된다 |
| 툴셋·스킬 작성 기준 | `create-toolset`, `unreal-skill`은 이 저장소의 `AIWidgetInspector` 같은 프로젝트 전용 툴셋을 만들 때 그대로 쓸 수 있는 공식 체크리스트다 |
| 설정 변경 없음 | `unreal-mcp`, 8000, `/mcp`로 기존 `.mcp.json`과 맞는다 |
| 가볍고 투명함 | 텍스트 64KB와 bash 훅 하나. MIT 라이선스, Anthropic 디렉터리의 파트너 검토를 받았다. 끄면 바로 원래대로 돌아간다 |
| 팀 공유 | `.claude/settings.json` 한 줄로 프로젝트 전원에게 같은 지침을 준다 |

### 아쉬운 점

| 항목 | 내용 |
| --- | --- |
| 단순 작업에는 오버헤드 | 레벨 조회에서 +2턴, 누적 입력 토큰 +28.5%. 결과는 같았다 |
| 실제로 막힌 곳은 안 다룸 | 큰 스키마가 파일로 넘어가는 문제, `refPath` 객체 경로 형식, 필수 인수 같은 5.8.4 세부는 스킬에 없다 |
| 5.8.4와 어긋나는 이름 | 스킬의 `AgentSkillToolset.ListSkills`는 이 빌드에서 "not found"다. 정식 이름은 `ToolsetRegistry.AgentSkillToolset`이라 매번 한 번 틀리고 고쳤다. Live Coding 도구는 따로 켜야 한다 |
| 자동 호출이 문구에 좌우됨 | 에디터 조작이 분명하지 않은 질문에서는 스킬이 안 불렸다 |
| 연결 문제는 그대로 | 프록시가 없는 설치본에서는 에디터를 먼저 켜야 한다 |
| 상시 1,470토큰 | 작지만, 사용자 범위로 설치하면 언리얼과 상관없는 세션에도 든다 |

---

<a id="safety"></a>

## 8. 안전하게 쓰기

플러그인 README의 보안 항목은 대부분 **MCP로 에디터를 열어 주는 것 자체**에 대한 경고다. 플러그인을 안 써도 해당한다. 요약하면 네 가지다.

- **localhost는 신뢰 경계가 아니다.** 서버는 브라우저 탭의 접근은 막지만, 같은 사용자로 실행된 프로세스는 누구나 접속할 수 있다. 공용 PC에서 켜 두지 않고, 포트를 외부에 열지 않는다.
- **`ProgrammaticToolset.execute_tool_script`는 에디터 권한으로 Python을 실행한다.** 모든 툴셋 API, 에셋 데이터베이스, 디스크의 프로젝트에 접근한다.
- **`--dangerously-skip-permissions`로 실행하지 않는다.** 도구마다 묻는 승인 단계가 사라진다.
- **긴 작업 전에는 저장하고 커밋한다.** 도구 하나로 버전 관리 중인 에셋을 옮기거나 지울 수 있다.

직접 본 것도 두 가지 있다.

**Claude Code에서 파일 읽기를 막아도 에디터를 거쳐 읽을 수 있었다.** 6.4절 측정에서 `Read`·`Grep`·`Glob`을 막았더니, 플러그인이 없는 실행 하나가 `execute_tool_script`로 Python `open()`을 써서 저장소의 `Docs/UE/UnrealMCP.md`를 읽었다. 이 실행 환경은 프로젝트 폴더(`D:\Unreal Projects\UnrealEngineLab`)와 `Saved/` 바깥 경로는 "outside all allowed directories"로 거부했지만, 프로젝트 안의 문서·소스·설정은 그대로 읽혔다.

**`call_tool` 승인 하나가 836개 도구 전체의 문이다.** Claude Code 권한은 MCP 도구 단위로 걸리는데, 도구 검색 모드에서는 모든 도구가 `mcp__unreal-mcp__call_tool` 하나를 거친다. 허용 목록만으로는 조회만 열고 쓰기는 막는 식으로 나눌 수 없다. 나누려면 PreToolUse 훅에서 `call_tool`의 `tool_name`을 검사해야 한다(이번에는 해 보지 않았다). 그래서 이번 측정은 저장하지 않을 템플릿 맵에서만 했다.

---

<a id="pitfalls"></a>

## 9. 막히기 쉬운 곳

| 증상 | 원인 | 해결 |
| --- | --- | --- |
| 세션을 연 뒤 에디터를 켰는데 `unreal-mcp`가 계속 실패 | 직접 HTTP 연결은 세션 시작 때 붙는다. 5.8.4 런처 설치본에는 프록시가 없다 | 에디터와 서버를 먼저 켜고 세션을 시작한다. 이미 열었다면 `/mcp`에서 다시 연결한다 |
| `Toolset 'AgentSkillToolset' not found` | 스킬 문서의 짧은 이름. 5.8.4의 정식 이름은 `ToolsetRegistry.AgentSkillToolset` | `list_toolsets`에 나온 이름을 그대로 쓴다 |
| `GetSkills`에서 `skillPaths` 누락 오류 | 인수 이름이 camelCase(`skillPaths`)다 | `describe_toolset`으로 스키마를 먼저 읽는다 |
| `describe_toolset`이 "exceeds maximum allowed tokens"를 내고 파일로 저장 | `BlueprintTools` 스키마가 68,906자로 Claude Code의 MCP 출력 한도를 넘는다 | `Read`/`Grep`을 허용해 저장된 파일을 읽게 한다. 환경 변수 `MAX_MCP_OUTPUT_TOKENS`로 한도를 올리는 방법도 있다(이번에는 바꾸지 않았다) |
| 저장된 스키마 파일도 `Read`가 거부 | 29,923토큰으로 `Read` 한도(25,000)를 넘는다 | `offset`/`limit`로 나눠 읽거나 `Grep`으로 필요한 도구만 찾는다 |
| `... is not a valid object path for property 'blueprint'` | `refPath`에 패키지 경로(`/Game/X/BP_A`)를 넣었다 | 객체 경로 `/Game/X/BP_A.BP_A`를 넣는다 |
| `find_actors`에 빈 인수를 보내면 오류 | `name`, `tag`, `collision_channels`가 필수다 | 빈 문자열·빈 배열이라도 채운다 |
| `LiveCodingToolset`이 목록에 없음 | `AllToolsets` 종속성에 없고 기본으로 꺼져 있다 | `.uproject`에 `LiveCodingToolset`을 추가하고 재시작한다 |
| 훅 문장이 안 들어감 | Windows에서 `bash`를 못 찾는다 | Git for Windows나 WSL을 쓴다. 훅이 없어도 스킬과 MCP는 동작한다 |
| 스킬이 안 불림 | 질문만 봐서는 에디터 조작인지 분명하지 않다 | "unreal-mcp 스킬을 참고해서"를 붙이거나 `/unreal-engine-skills-for-claude-code:unreal-mcp`로 직접 부른다 |

---

<a id="summary"></a>

## 10. 정리

```text
구성
MCP 서버와 도구는 없다. 엔진 MCP 사용 설명서(스킬 3개)와 시작 훅 1개뿐이다.
.mcp.json에 unreal-mcp가 이미 있다면 바꿀 설정이 없다.

비용
상시 1,470토큰. 스킬을 부르면 2,582토큰이 더 든다.
툴셋 스키마 하나(SceneTools 10,680토큰)보다 작다.
단순 조회에서는 +2턴, 누적 입력 토큰 +28.5%.

효과
엔진 Agent Skill(20개)을 쓰게 만든다. 스킬이 로드되면 4/4, 플러그인이 없으면 0/4.
레벨·블루프린트 조회처럼 도구가 분명한 일은 빨라지지 않았다.
자동 호출은 문구에 좌우된다. 이름을 부르면 확실하다.

사용
에디터를 먼저 켜고 세션을 연다. 에디터 조작이 분명한 요청은 스킬이 저절로 불린다.
엔진 지침이 필요한 작업은 /unreal-engine-skills-for-claude-code:unreal-mcp 로 부르거나
"unreal-mcp 스킬을 참고해서"를 붙인다.

5.8.4에서
프록시가 없다. 에디터를 먼저 켠다.
LiveCodingToolset은 따로 켠다. AgentSkillToolset은 ToolsetRegistry.AgentSkillToolset이다.

안전
call_tool 승인 하나가 836개 도구 전체를 연다.
execute_tool_script는 프로젝트 폴더 안 파일을 읽을 수 있다.
```

설치는 할 만하다. 비용이 툴셋 스키마 하나보다 작고, 끄면 바로 원래대로 돌아간다. 다만 "설치하면 Claude가 에디터를 더 잘 다룬다"를 기대하면 실망한다. 이번에 잰 범위에서는 **도구 탐색은 엔진 MCP가 이미 충분히 안내하고 있었고, 플러그인이 더한 값은 엔진이 숨겨 둔 Agent Skill을 꺼내 쓰게 하는 데 있었다.**

그래서 쓰는 방식을 이렇게 정했다. 이 PC에는 사용자 범위로 설치해 두고, 블루프린트·머티리얼·Niagara·PCG처럼 엔진 스킬이 있는 작업을 시킬 때는 슬래시로 부르거나 요청에 "unreal-mcp 스킬을 참고해서"를 붙인다. 레벨 조회 같은 단순 작업은 그냥 둔다.

질문당 두 번씩 돌린 작은 표본이라 수치는 경향으로만 본다. 수정·저장이 들어가는 작업에서 "저장하고, 또 저장" 같은 안전 규칙이 실제로 지켜지는지는 이번에 재지 않았다.

---

<a id="evidence"></a>

## 11. 검증 기록·재현·참고 자료

### 이번에 확인한 범위

| 항목 | 결과 |
| --- | --- |
| 엔진 | 로컬 `Build.version`: UE 5.8.4 / CL 58902052 |
| 플러그인 | 3.1.1, 커밋 `a6aa73a`(Anthropic 디렉터리 검토 커밋과 같음). 스킬·참고 문서·훅·매니페스트·README 전부 읽음 |
| 설치 | 이 PC에 사용자 범위로 설치. 새 세션에서 스킬 3개 로드, 훅 `success`, 슬래시 호출로 본문 주입 확인 |
| 에디터 | 53개 툴셋, 836개 도구, Agent Skill 20개 조회. 빈 템플릿 맵 |
| 비교 실행 | 30회. 파일 도구 허용 16회(질문 1~3 × 2조건 × 2회, 상시 비용 2회, 스킬 이름 지정 2회), MCP 도구만 허용 14회 |
| 정리 | `call_tool` 152번 중 저장·수정 호출 0건, 조회한 블루프린트와 맵 dirty 아님 |
| 미확인 | 수정·저장이 들어가는 작업, Claude 앱(데스크톱)에서의 훅 동작, 프록시가 있는 소스 빌드, Opus 계열 모델 |

- [에디터 확인 결과](Evidence/UnrealEngineSkills/editor_check.json), [질문별 정답](Evidence/UnrealEngineSkills/ground_truth.json)
- [비교 실행 요약 — 파일 도구 허용](Evidence/UnrealEngineSkills/summary.jsonl), [MCP 도구만 허용](Evidence/UnrealEngineSkills/summary_mcp_only.jsonl)
- [재현 스크립트 안내](../../Scripts/UnrealEngineSkills/README.md)

### 참고 자료

- [EpicGames/unreal-engine-skills-for-claude-code-plugin](https://github.com/EpicGames/unreal-engine-skills-for-claude-code-plugin) — 플러그인 원본, README의 Security 항목
- [Epic: Unreal MCP in Unreal Editor](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-mcp-in-unreal-editor) — 서버·툴셋 공식 안내
- [Unreal MCP 연결하기](UnrealMCP.md), [Unreal MCP 툴셋 전체 목록](UnrealMCPToolsets.md) — 이 저장소의 엔진 쪽 정리

---

[목차로 돌아가기](#contents) · [Unreal Engine 문서 목록](README.md) · [저장소 소개](../../README.md)
