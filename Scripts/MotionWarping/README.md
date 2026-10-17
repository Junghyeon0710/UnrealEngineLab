# GameAnimationSample Motion Warping 실험

UE **5.8.3 / CL 58210709**의 실제 Game Animation Sample을 Unreal MCP로 조작해 Hurdle 동작을 비교한다. 원본 맵, Blueprint, Animation 에셋은 저장하지 않는다.

## 파일

| 파일 | 역할 |
| --- | --- |
| `inspect_sample.py` | 프로젝트 조사, 한시적인 실험 Toolset 등록, MCP 8001 포트 시작 |
| `mw_lab_runtime.py` | 에디터 안에서 실행되는 고정된 실험 작업. 소스 코드나 셸 명령을 MCP 인자로 받지 않음 |
| `mcp_client.py` | 로컬 Unreal MCP 통신과 Toolset 검색 |
| `run_sample_tests.py` | 네 번의 독립 PIE 세션, 실제 CVar 확인, 몽타주·좌표·PNG 기록 |
| `export_captures.py` | 실제 PNG 인코딩, 비교 쌍의 몽타주 일치 검사, 측정 자료 내보내기 |
| `generate_preview.mjs` | Markdown의 로컬 HTML 미리보기 생성. `marked.esm.js` 경로를 인자로 전달 |

## 에디터 실행

현재 문서 저장소와 GameAnimationSample을 별도 에디터로 열고 MCP 포트도 각각 8000 / 8001로 분리했다. GameAnimationSample을 아래처럼 대화형으로 실행한다. 경로는 설치 위치에 맞춘다.

```powershell
$mwEditor = 'D:\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
Start-Process -FilePath $mwEditor -ArgumentList @(
    '"D:\Unreal Projects\GameAnimationSample\GameAnimationSample.uproject"',
    '-EnablePlugins=ModelContextProtocol,EditorToolset,SlateInspectorToolset,PythonScriptPlugin,EditorScriptingUtilities',
    '-ModelContextProtocolStartServer',
    '-ModelContextProtocolPort=8001',
    '-ExecCmds="py D:/Unreal Projects/UnrealEngineLab/Scripts/MotionWarping/inspect_sample.py"'
)
```

명령줄의 `EnablePlugins`를 사용하므로 `.uproject`를 편집할 필요가 없다. 에디터가 이미 열려 있으면 필요한 플러그인을 활성화한 상태에서 `inspect_sample.py`를 에디터 Python으로 실행해도 된다.

`Saved/MotionWarpingLab/sample_inventory.json`이 생성되고 MCP `list_toolsets`에 `PythonTypes.MotionWarpingLabToolset...`이 나타나면 준비된 상태다. 포트 8001은 이 실험에서 시작한 GameAnimationSample용으로 사용한다.

## 실행과 내보내기

프로젝트 루트에서 실행한다. Python 3과 Pillow가 필요하다. `python`은 해당 환경의 Python 실행 파일로 대체할 수 있다.

```powershell
python Scripts/MotionWarping/run_sample_tests.py
python Scripts/MotionWarping/export_captures.py
```

기본 실행은 새 테스트를 수행한다. 기존 생성 폴더는 같은 `Saved/MotionWarpingLab/` 안에 날짜가 붙은 이름으로 보관한다. `--reuse`를 명시하면 이미 완료된 기록을 재사용한다. `--case depth50_on --case depth50_off`처럼 지정한 조건만 다시 실행할 수도 있다.

각 조건은 새 PIE 세션을 사용한다. 샘플 CMC 캐릭터를 초기 위치에 생성·빙의하고, 같은 상대 위치의 카메라를 사용한다. 기존 `GetTraversalCheckInputs → TryTraversalAction` 경로로 장애물 검사·Chooser 선택·몽타주 재생을 실행한다. 시작 이후 캐릭터 위치를 스크립트로 덮어쓰지 않는다.

촬영 전에 열린 에셋 에디터를 저장 없이 닫는다. `Shot`은 다른 렌더링 뷰포트가 열려 있으면 그 화면을 촬영할 수 있으므로, PIE 월드와 CameraActor를 검사하고 실제 이미지에 시험 장애물이 있는지도 확인해야 한다. 각 기록의 `capture_audit`와 `setup`에는 월드·카메라·장애물 경계를 남긴다.

카메라는 시작점 기준 X +120cm, Y -530cm, 월드 Z 230cm에서 X +120cm, 같은 Y, 월드 Z 95cm를 본다. FOV는 50도다. 시험 대상과 바닥 이외의 LevelBlock은 PIE에서 렌더링만 숨긴다. 충돌·Trace 설정은 바꾸지 않으며 원본 월드를 저장하지 않는다.

Unreal `DrawDebug`로 노란 FrontLedge 목표, 하늘색 `attach` 본과 연결선, 초록 BackFloor 목표를 실제 월드 좌표에 표시한다. 구체와 선은 Foreground로 그려 가려지지 않게 하며 이동에는 관여하지 않는다. `attach`는 애니메이션의 기준 본으로, 손바닥 위치 자체는 아니다.

| 이름 | 장애물 / 초기 위치 | `a.MotionWarping.Disable` |
| --- | --- | --- |
| `depth50_on` | `LevelBlock_Traversable_C_4`, `(2300, -2400, 90)` | 0 |
| `depth50_off` | 위와 같음 | 1 |
| `depth20_on` | `LevelBlock_Traversable_C_7`, `(2330, -2600, 90)` | 0 |
| `depth20_off` | 위와 같음 | 1 |

캡처 중 게임 시간 배율은 0.25, 프레임 상한은 30이다. GIF는 게임 시간 간격으로 인코딩하고 마지막 프레임을 잠시 유지한다. 실제 렌더링 프레임 외의 중간 포즈는 만들지 않는다.

`*-comparison.gif`는 Traversal 호출 이후 같은 시간에 가장 가까운 캡처를 나란히 배치한다. 0.5배 속도로 재생하고 접촉·착지 부근에서 잠시 멈춘다. 프레임 선택 기록은 `*_comparison_frames.json`에 둔다. 확대 스틸은 FrontLedge Window 끝에 가까운 이미지에서 양쪽의 같은 영역을 자른 것으로, 정확히 같은 몽타주 프레임을 강제한 촬영은 아니다.

녹화에 사용한 에디터 세션에서 Texture/Shadow/GI/Reflection 품질을 1로, Texture Streaming Pool을 1000MB로 설정했다. 백그라운드 CPU 제한은 촬영 중 해제하고 끝나면 원래 값으로 복구한다. 이 값들은 테스트 중 해당 에디터 인스턴스에 적용하며 프로젝트 설정 파일에는 저장하지 않는다.

실행이 끝나면 PIE를 중지하고 Warping 비활성화 CVar와 프레임 상한을 해제한다. 중간에 테스트를 중단했다면 MCP의 `abort_recording` 작업으로 콜백을 해제한 뒤 PIE를 중지하고 `restore_session`을 호출할 수 있다.

## 출력과 측정 기준

- `Saved/MotionWarpingLab/<조건>/`: 원본 PNG, 매 Tick의 실제 위치·본 위치·몽타주 시간·Warp Target 기록. Git 제외.
- `Docs/UE/Images/motionwarping-gas-*`: 문서용 실제 캡처와 GIF.
- `Docs/UE/Evidence/MotionWarping/`: 원본 수치 기록, 몽타주의 실제 Window, 요약 JSON.

FrontLedge는 마지막 FrontLedge Window 종료 시점에 가까운 `attach` 본의 3D 오차를 사용한다. BackFloor는 해당 Window 종료 시점에 가까운 캐릭터 발 기준 위치의 XY 오차를 사용한다. 종료 시점과 정확히 일치한 프레임을 강제로 만든 결과는 아니다. 선택된 샘플의 실제 몽타주 시간도 요약에 보존한다.

50cm 조건에서는 오른발, 20cm 조건에서는 왼발 버전이 선택됐다. 내보낼 때는 각 ON/OFF 쌍이 같은 몽타주를 사용했는지 검사한다. 몽타주가 달라진 쌍을 보정만의 차이로 비교하지 않는다.

[정리 글](../../Docs/UE/MotionWarping.md)
