# 파쿠르 타임어택 스크립트

[파쿠르 타임어택 문서](../../Docs/UE/ParkourTimeAttack.md)에서 쓴 스크립트다. Game Animation Sample(GASP)의 Mover 캐릭터를 이 프로젝트로 가져와서, C++ 게임 규칙과 코스 맵을 얹었다.

| 파일 | 역할 |
| --- | --- |
| `gasp_packages.txt` | 가져온 GASP 패키지 2,030개. `SandboxCharacter_Mover`, `PC_Sandbox`, `IMC_Sandbox`, 레벨 블록이 하드 참조하는 전부 |
| `import_gasp_assets.py` | 위 목록대로 GASP `Content` 에서 같은 경로로 복사한다. 다른 파일이 이미 있으면 멈춘다 |
| `register_toolset.py` | 에디터 콘솔에서 `py` 로 실행. `ParkourLabToolset` 을 MCP 툴셋으로 등록한다 |
| `pk_lab_runtime.py` | 툴셋이 부르는 작업들. 의존성 조사, 코스 배치·저장, PIE 자동 플레이·기록·캡처 |
| `mcp_client.py` | Unreal MCP HTTP 클라이언트. 주소는 `PK_MCP_ENDPOINT` (기본 `http://127.0.0.1:8000/mcp`) |
| `course_layout.json` | 코스 배치. 바닥·경사로·옆 경사·장애물·체크포인트를 cm 단위로 적었다 |
| `build_course.py` | `course_layout.json` 대로 `L_ParkourCourse` 를 다시 만들고 저장한다 |
| `run_tests.py` | PIE 자동 주행 녹화, 발 디딤을 끈 주행, 낙하 시험, Control Rig·Motion Warping 디버그 캡처, 에디터 전경 캡처 |
| `export_captures.py` | GIF·사진과 `Docs/UE/Evidence/ParkourCourse/summary.json`, `systems.json` 생성 |

## 처음부터 다시 만들기

GASP 에셋과 코스 맵은 저장소에 들어 있어서, 클론한 뒤 C++만 빌드하면 바로 열린다. 아래는 처음 만들 때의 순서다.

```powershell
# 1. 에디터를 닫은 상태에서 GASP 에셋 복사 (GASP 5.8 프로젝트 경로)
python Scripts/ParkourCourse/import_gasp_assets.py "D:/Unreal Projects/GameAnimationSample"

# 2. C++ 빌드
& "D:\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" UnrealEngineLabEditor Win64 Development "-Project=D:\Unreal Projects\UnrealEngineLab\UnrealEngineLab.uproject"
```

에디터는 MCP 서버를 켜서 띄운다.

```powershell
$editor = 'D:\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
Start-Process -FilePath $editor -ArgumentList @(
    '"D:\Unreal Projects\UnrealEngineLab\UnrealEngineLab.uproject"',
    '-EnablePlugins=SlateInspectorToolset,PythonScriptPlugin,EditorScriptingUtilities',
    '-ModelContextProtocolStartServer',
    '-ModelContextProtocolPort=8000'
)
```

에디터 하단 콘솔에서 툴셋을 등록하고, 코스를 만들고, 녹화한다.

```text
py "D:/Unreal Projects/UnrealEngineLab/Scripts/ParkourCourse/register_toolset.py"
```

```powershell
python Scripts/ParkourCourse/build_course.py
python Scripts/ParkourCourse/run_tests.py
python Scripts/ParkourCourse/export_captures.py
```

## 메모

- 플러그인(`PoseSearch`, `Chooser`, `Mover`, `MovieSceneAnimMixer` 등)과 설정(데이터 기반 CVar, 충돌 채널 `Traversable`/`Mouse`/`Obstacle`, PoseSearch, 게임플레이 태그, NetworkPrediction)은 GASP 5.8과 같게 맞췄다. 충돌 채널은 에셋이 번호(`GameTraceChannel1~3`)로 저장하기 때문에 순서까지 같아야 한다.
- `DDCvar.LocomotionSetupMover` 기본값만 GASP와 다르게 0으로 두었다. GASP 기본 1은 상태 머신 + Chooser 방식이라 Motion Matching 노드를 쓰지 않는다.
- 스크립트로 놓은 `LevelBlock_Traversable` 은 Ledge 스플라인 길이가 템플릿 값(100cm)에 머문다. `place_actor` 에서 `UpdateSpline()` 을 불러 고친다. 안 하면 넘기 목표가 블록 폭의 20%만큼 옆으로 잡힌다.
- 에디터가 뒤에 있으면 PIE가 초당 몇 프레임만 돌고, 그러면 Mover 캐릭터가 게임 시간만큼 움직이지 못한다. `configure_view` 가 `bThrottleCPUWhenNotForeground` 를 끈다.
- 다른 프로젝트 에디터가 켜져 있으면 Live Coding 때문에 명령줄 빌드가 막힌다.
