# MVVM 실험 스크립트

[UMG Viewmodel(MVVM) 문서](../../Docs/UE/MVVM.md)에서 쓴 스크립트다.

| 파일 | 역할 |
| --- | --- |
| `build_assets.py` | 에디터 콘솔에서 `py` 로 실행. `/Game/MVVMLab` 에 위젯 세 개와 맵을 만든다 |
| `register_toolset.py` | 에디터 콘솔에서 `py` 로 실행. `MVVMLabToolset` 을 MCP 툴셋으로 등록한다 |
| `mvvm_lab_runtime.py` | 툴셋이 부르는 작업. PIE 상태, 게임 모드 함수 호출, 녹화 |
| `mcp_client.py` | Unreal MCP HTTP 클라이언트. 주소는 `MVVM_MCP_ENDPOINT` (기본 `http://127.0.0.1:8000/mcp`) |
| `run_tests.py` | 호출 횟수 측정, 한 프레임 여러 번 변경, 버튼 클릭이 들어간 데모 녹화 |
| `export_captures.py` | `Docs/UE/Images/mvvm-demo.gif` 와 `Docs/UE/Evidence/MVVM/summary.json` 생성 |

위젯의 배치와 바인딩은 `Source/UnrealEngineLabEditor/MVVMLab/MVVMLabEditorLibrary` 가 만든다. MVVM 에디터 서브시스템에서 바인딩 경로를 정하는 함수가 C++에만 열려 있어서, 그 부분을 C++로 감싸 Python에서 부른다.

## 다시 돌려 보기

C++를 빌드하고 에디터를 MCP 서버와 함께 띄운다.

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
py "D:/Unreal Projects/UnrealEngineLab/Scripts/MVVMLab/build_assets.py"
py "D:/Unreal Projects/UnrealEngineLab/Scripts/MVVMLab/register_toolset.py"
```

`L_MVVMLab` 이 열린 상태에서:

```powershell
python Scripts/MVVMLab/run_tests.py
python Scripts/MVVMLab/export_captures.py
```

## 메모

- UMG 위젯은 뷰포트 위에 Slate로 그려져서 `Shot` 에 안 찍힌다. `Shot showui` 는 에디터 창 전체를 찍으므로, `export_captures.py` 가 뷰포트의 위젯 부분만 자른다(`CROP`). 에디터 배치가 다르면 이 값을 바꿔야 한다.
- 캡처 중에는 스크린샷이 위젯을 한 번 더 그려서 속성 바인딩 호출 수가 늘어난다. 호출 수는 캡처를 끈 `measure` 에서 읽는다.
