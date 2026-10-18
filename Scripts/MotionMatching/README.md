# Motion Matching 테스트 스크립트

[Motion Matching 문서](../../Docs/UE/MotionMatching.md)에서 쓴 테스트 스크립트다. UE 5.8.3의 Game Animation Sample을 Unreal MCP로 조작해서 테스트했다. 샘플의 맵, 블루프린트, 애니메이션은 저장하지 않는다.

| 파일 | 역할 |
| --- | --- |
| `register_toolset.py` | 에디터 콘솔에서 `py` 로 실행. `MotionMatchingLabToolset` 을 MCP 툴셋으로 등록한다 |
| `mm_lab_runtime.py` | 툴셋이 부르는 작업들. PIE에 캐릭터·카메라 생성, 입력 주입, AnimBP 변수·발 위치 기록 |
| `mcp_client.py` | Unreal MCP HTTP 클라이언트. 주소는 `MM_MCP_ENDPOINT` (기본 `http://127.0.0.1:8000/mcp`) |
| `run_tests.py` | Dense / Sparse / Extreme Sparse / 상태 머신 모드 × (촬영 1회 + 측정 3회) |
| `export_captures.py` | GIF·정지 이미지와 `Docs/UE/Evidence/MotionMatching/summary.json` 생성 |

에디터 실행 방법은 [Motion Warping 스크립트](../MotionWarping/README.md)와 같다. 등록은 에디터 하단 콘솔에서 한다.

```text
py "D:/Unreal Projects/UnrealEngineLab/Scripts/MotionMatching/register_toolset.py"
```

```powershell
python Scripts/MotionMatching/run_tests.py
python Scripts/MotionMatching/export_captures.py
```

GASP 캐릭터는 기본이 스트레이프 모드라서 `CharacterInputState.WantsToStrafe` 를 끄고 테스트한다. 상태 머신 모드는 `DDCVar.ExperimentalStateMachine.Enable` 과 `DDCVar.LocomotionSetupCMC` 를 둘 다 1로 준다.

에셋 에디터(미리보기 뷰포트가 있는 DB·AnimBP 에디터)를 여러 개 열어 두면 비디오 메모리가 부족해 에디터가 종료될 수 있다. 하나씩 열고 닫는다.
