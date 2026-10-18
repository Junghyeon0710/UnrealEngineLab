# Control Rig 테스트 스크립트

[Control Rig 문서](../../Docs/UE/ControlRig.md)에서 쓴 테스트 스크립트다. UE 5.8.3의 Game Animation Sample을 Unreal MCP로 조작해서 테스트했다. 샘플의 맵, 블루프린트, 리그는 저장하지 않는다.

| 파일 | 역할 |
| --- | --- |
| `register_toolset.py` | 에디터 콘솔에서 `py` 로 실행. `ControlRigLabToolset` 을 MCP 툴셋으로 등록한다 |
| `cr_lab_runtime.py` | 툴셋이 부르는 작업들. 리그 구조 읽기, PIE 캐릭터 배치·입력, 발 높이·본 방향 기록, 화면 캡처 |
| `mcp_client.py` | Unreal MCP HTTP 클라이언트. 주소는 `CR_MCP_ENDPOINT` (기본 `http://127.0.0.1:8000/mcp`) |
| `run_foot_tests.py` | 발 디딤. 경사 0~40° × Control Rig 켬/끔, 디버그 캡처, 30° 가로질러 걷기 |
| `run_lookat_tests.py` | 시선. LookAtPOI_Level에서 플레이어 캐릭터가 NPC 둘레를 걷는 동안 켬/끔 |
| `export_captures.py` | 이미지·GIF와 `Docs/UE/Evidence/ControlRig/*.json` 생성 |

에디터 실행 방법은 [Motion Warping 스크립트](../MotionWarping/README.md)와 같다. 등록은 에디터 하단 콘솔에서 한다.

```text
py "D:/Unreal Projects/UnrealEngineLab/Scripts/ControlRig/register_toolset.py"
```

```powershell
python Scripts/ControlRig/run_foot_tests.py
python Scripts/ControlRig/run_lookat_tests.py
python Scripts/ControlRig/export_captures.py
```

## 메모

- 발 디딤 리그는 Mover 캐릭터에만 있다. `DDCvar.PawnClass 1` 로 PIE를 시작하고, 리그는 `a.AnimNode.FootPlacement.Enable` 로 켜고 끈다.
- Mover 캐릭터는 `TeleportTo` 를 한 번만 받아들인다. GASP 캐릭터의 `CustomTeleport` 로 옮긴다.
- Mover 캐릭터는 `AddMovementInput` 을 무시한다. `IA_Move` 를 Enhanced Input에 매 틱 주입한다.
- 기본 맵 램프 입구(1600, 1600)에 텔레포터가 있다. 걷기 테스트는 램프 위에서만 한다.
- PIE에서 리그 디버그를 보려면 `ControlRig.EnableDrawInterfaceInGame 1`, `a.AnimNode.ControlRig.Debug 1`, `a.AnimNode.FootPlacement.Debug 1` 이 모두 필요하다.
- LookAtPOI 변수는 인스턴스에서 편집할 수 없어서 Python으로 직접 넣을 수 없다. 샘플 컨트롤러의 `Zone Was Selected` 를 불러 켜고, 목표 기즈모를 옮긴다.
- 에셋 에디터(미리보기 뷰포트가 있는 AnimBP·리그 에디터)를 여러 개 열어 두면 비디오 메모리가 부족해질 수 있다. 하나씩 열고 닫는다.
