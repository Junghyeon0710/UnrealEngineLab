# GameplayMessage 실험 스크립트

[Lyra의 GameplayMessage로 시스템끼리 메시지 주고받기](../../Docs/UE/GameplayMessage.md)에서 쓴 스크립트다.

| 파일 | 역할 |
| --- | --- |
| `build_assets.py` | 에디터 콘솔에서 `py` 로 실행. `/Game/GameplayMessageLab` 에 킬 피드 위젯과 맵을 만든다 |
| `register_toolset.py` | 에디터 콘솔에서 `py` 로 실행. `GMLabToolset` 을 MCP 툴셋으로 등록한다 |
| `gm_lab_runtime.py` | 툴셋이 부르는 작업. PIE 상태, 게임 모드 함수 호출, 로그 스위치, 녹화 |
| `mcp_client.py` | Unreal MCP HTTP 클라이언트. 주소는 `GM_MCP_ENDPOINT` (기본 `http://127.0.0.1:8000/mcp`) |
| `run_tests.py` | 데모 녹화, 호출 순서·타입 불일치 실험, 델리게이트와 비용 비교 |
| `export_captures.py` | `Docs/UE/Images/gameplaymessage-*` 와 `Docs/UE/Evidence/GameplayMessage/summary.json` 생성 |

킬 피드 위젯의 위젯 트리와 "Listen for Gameplay Messages" 노드는 `Source/UnrealEngineLabEditor/GameplayMessageLab/GMLabEditorLibrary` 가 만든다. 블루프린트 그래프에 노드를 놓고 핀을 잇는 API가 C++에만 있어서, 그 부분을 C++로 감싸 Python에서 부른다.

## 다시 돌려 보기

Lyra 프로젝트의 `Plugins/GameplayMessageRouter` 가 이 저장소의 `Plugins/` 에 들어 있어야 한다. C++를 빌드하고 에디터를 MCP 서버와 함께 띄운다.

```powershell
& "D:\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" UnrealEngineLabEditor Win64 Development "-Project=D:\Unreal Projects\UnrealEngineLab\UnrealEngineLab.uproject"

$editor = 'D:\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
Start-Process -FilePath $editor -ArgumentList @(
    '"D:\Unreal Projects\UnrealEngineLab\UnrealEngineLab.uproject"',
    '-EnablePlugins=SlateInspectorToolset,PythonScriptPlugin,EditorScriptingUtilities',
    '-ModelContextProtocolStartServer',
    '-ModelContextProtocolPort=8000'
)
```

에디터 하단 콘솔에서:

```text
py "D:/Unreal Projects/UnrealEngineLab/Scripts/GameplayMessageLab/build_assets.py"
py "D:/Unreal Projects/UnrealEngineLab/Scripts/GameplayMessageLab/register_toolset.py"
```

`L_GameplayMessageLab` 이 열린 상태에서:

```powershell
python Scripts/GameplayMessageLab/run_tests.py
python Scripts/GameplayMessageLab/export_captures.py
```

`export_captures.py` 는 에디터 캡처 두 장도 자른다. `Saved/GameplayMessageLab/editor/` 에 SlateInspector `Screenshot` 으로 찍은 에디터 창을 넣어 둔다.

```text
wbp_graph.png    WBP_GMLabFeed 그래프 탭
output_log.png   run_mismatch_test 뒤, 출력 로그를 LogGameplayMessageSubsystem 으로 거른 화면
```

## 메모

- UMG 위젯은 `Shot` 에 안 찍혀서 `Shot showui` 로 에디터 창 전체를 찍고 뷰포트만 자른다(`VIEWPORT`). 에디터 배치가 다르면 이 값을 바꿔야 한다.
- 위젯 블루프린트 에디터 탭이 열려 있으면 `Shot showui` 가 뷰포트만 찍고 UMG가 빠졌다. 녹화 전에 닫는다.
- 라이브 코딩으로 `UGMLabFeedWidget` 을 바꾼 직후에는 `build_assets.py` 가 위젯 블루프린트를 지우지 못했다(재인스턴싱이 참조를 잡고 있음). 런타임 모듈을 고쳤으면 에디터를 껐다 켜고 돌린다.
