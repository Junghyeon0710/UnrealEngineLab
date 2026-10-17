# Motion Warping 테스트 스크립트

[Motion Warping 문서](../../Docs/UE/MotionWarping.md)에서 쓴 테스트 스크립트다. UE 5.8.3 에디터를 Unreal MCP로 조작해서 테스트했다.

- 파쿠르: Game Animation Sample(GASP) 프로젝트. 샘플의 맵, 블루프린트, 애니메이션은 저장하지 않는다.
- 전투: 이 저장소 프로젝트. 템플릿 마네킹의 공격 애니메이션으로 몽타주와 테스트 맵을 `Content/MotionWarpingLab/` 에 만든다.

## 파일

| 파일 | 역할 |
| --- | --- |
| `register_toolset.py` | 에디터 안에서 실행. `MotionWarpingLabToolset` 을 MCP 툴셋으로 등록한다 |
| `mw_lab_runtime.py` | 툴셋이 부르는 작업들. PIE에 블록·캐릭터·카메라 생성, 동작 실행, 기록 |
| `mcp_client.py` | Unreal MCP HTTP 클라이언트 |
| `run_sample_tests.py` | 파쿠르. 높이 60 / 100 / 150cm × OFF / ON, 엔진 디버그 2회 |
| `run_combat_tests.py` | 전투. 적 위치 2곳 × OFF / ON |
| `export_captures.py` | 기록한 프레임으로 GIF·비교 이미지를 만들고 측정 요약을 내보낸다 |

## 1. 에디터 실행

엔진에 들어 있는 `ModelContextProtocol`(Unreal MCP) 플러그인과 툴셋 플러그인을 명령줄로 켰다. 이렇게 하면 GASP의 `.uproject` 를 고칠 필요가 없다.

```powershell
$editor = 'D:\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
Start-Process -FilePath $editor -ArgumentList @(
    '"D:\Unreal Projects\GameAnimationSample\GameAnimationSample.uproject"',
    '-EnablePlugins=ModelContextProtocol,EditorToolset,SlateInspectorToolset,PythonScriptPlugin,EditorScriptingUtilities',
    '-ModelContextProtocolStartServer',
    '-ModelContextProtocolPort=8000'
)
```

전투는 `UnrealEngineLab.uproject` 로 같은 명령을 쓴다. 이 프로젝트는 MCP와 `MotionWarping` 플러그인이 이미 켜져 있어서 `-EnablePlugins=SlateInspectorToolset,PythonScriptPlugin,EditorScriptingUtilities` 만 있으면 된다. 템플릿 마네킹은 먼저 복사해 둔다.

```text
D:\Epic Games\UE_5.8\Templates\TemplateResources\High\Characters\Content\Mannequins
  -> Content/Characters/Mannequins
```

다른 포트를 쓰면 `MW_MCP_ENDPOINT` 환경 변수로 알려 준다. 기본값은 `http://127.0.0.1:8000/mcp` 다.

## 2. 실험 툴셋 등록

에디터 하단 콘솔(`Cmd`)에 입력한다. 테스트용 작업을 MCP 툴로 등록하는 스크립트다.

```text
py "D:/Unreal Projects/UnrealEngineLab/Scripts/MotionWarping/register_toolset.py"
```

MCP의 `list_toolsets` 에 `...MotionWarpingLabToolset` 이 보이면 준비된 것이다.

에디터 창이 최소화되어 있으면 PIE가 몇 프레임밖에 돌지 않는다. 실행 스크립트가 시작할 때 창을 복원한다.

## 3. 실행과 내보내기

저장소 루트에서 실행한다. Python 3과 Pillow가 필요하다.

```powershell
python Scripts/MotionWarping/run_sample_tests.py     # GASP 에디터에서
python Scripts/MotionWarping/run_combat_tests.py     # UnrealEngineLab 에디터에서
python Scripts/MotionWarping/export_captures.py      # --only mantle / --only combat
```

`--case mantle_h150_off`, `--case combat_far_on` 처럼 지정한 조건만 다시 돌릴 수 있다. 같은 이름의 이전 기록은 `Saved/MotionWarpingLab/archive/` 로 옮긴다. 조건마다 PIE를 새로 띄워서 테스트했다.

### 파쿠르

| 항목 | 값 |
| --- | --- |
| 실험 위치 | `DefaultLevel` 의 빈 바닥, 블록 앞면 X=2500, 중심 Y=-6500 |
| 블록 | `LevelBlock_Traversable`, 깊이 200cm, 폭 300cm, 높이 60 / 100 / 150cm |
| 캐릭터 | `SandboxCharacter_CMC`, 블록 앞면에서 85cm, Yaw 0 |
| 카메라 | 모든 조건에서 같은 CameraActor. 블록 앞면 기준 (+10, +760, 230)에서 (+10, 0, 160)을 봄, FOV 50 |
| 실행 | 0.3초 뒤 `GetTraversalCheckInputs` -> `TryTraversalAction` |
| 기록 | 매 틱 캡슐·`attach` 본·발 본·Warp Target·몽타주 위치. 약 0.05초(게임 시간)마다 `Shot` |
| 촬영 중 시간 배율 | 0.2. 화면 캡처가 프레임을 놓치지 않게 느리게 돌렸다 |

`LevelBlock_Traversable` 을 런타임에 스폰하면 Ledge 스플라인 길이가 갱신되지 않아서 `FrontLedge` 목표가 옆으로 밀린다. 그래서 스폰 직후 `UpdateSpline()` 을 호출한다. 자세한 내용은 문서의 [테스트하다 헤맨 부분](../../Docs/UE/MotionWarping.md#wrong-target)에 적어 두었다.

### 전투

| 항목 | 값 |
| --- | --- |
| 맵 | `/Game/MotionWarpingLab/MotionWarpingCombat` (엔진 Basic 템플릿으로 생성) |
| 몽타주 | `/Game/MotionWarpingLab/AM_Attack_MotionWarping`, 원본 `MM_Attack_02`, Window 0.05 ~ 0.467초, 목표 `AttackTarget` |
| 공격하는 쪽 | `ACharacter` + `SKM_Manny_Simple` + `ABP_Unarmed`, 원점에서 +X를 봄. `MotionWarping` 컴포넌트는 스폰 후 추가 |
| 적 | `ACharacter` + `SKM_Quinn_Simple`, 260cm·35° / 140cm·60° |
| 목표 | 적과 공격자를 잇는 선 위, 적 중심에서 124cm, 적을 바라보는 방향 |
| 기록 | 매 틱 위치·방향·양손 위치·몽타주 위치. 약 0.033초(게임 시간)마다 `Shot` |

테스트용 캐릭터는 메시를 스폰 후에 붙이기 때문에 `CacheInitialMeshOffset()` 을 다시 부르고, `bUseControllerRotationYaw` 를 끈다. 이유는 문서에 적어 두었다.

몽타주를 만드는 작업은 PIE 중에 부르면 안 된다. 에디터 에셋 함수가 PIE에서는 동작하지 않아서, 기존 몽타주를 못 찾고 새로 만들려다 덮어쓰기 확인 창이 뜬다. 스크립트는 PIE를 먼저 멈춘다.

## 출력

- `Saved/MotionWarpingLab/<조건>/`: 원본 PNG와 `measurements.json`. Git에서 제외된다.
- `Docs/UE/Images/motionwarping-mantle-*`, `motionwarping-combat-*`: 문서용 GIF와 비교 이미지.
- `Docs/UE/Evidence/MotionWarping/summary.json`, `combat_summary.json`: 조건별 측정 요약.
- `Docs/UE/Evidence/MotionWarping/montages.json`, `combat_montage.json`: 몽타주의 Window 설정.

내보낼 때 OFF/ON 쌍이 같은 몽타주와 조건을 썼는지, CVar 값이 맞는지 같이 확인한다.

끝나면 PIE를 멈추고 `a.MotionWarping.Disable`, `a.MotionWarping.Debug`, `t.MaxFPS` 를 원래대로 돌려 놓는다. 중간에 멈췄다면 `abort_recording` 으로 기록을 끊고 PIE를 멈춘 뒤 `restore_session` 을 호출하면 된다.
