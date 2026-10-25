# Unreal Engine Skills 플러그인 측정 재현

[학습 문서](../../Docs/UE/UnrealEngineSkills.md)의 수치를 만든 스크립트다. Git 커밋·푸시는 하지 않고, 에셋을 수정하는 호출도 하지 않는다.

## 준비

1. 에디터를 빈 템플릿 맵으로 열고 MCP 서버를 8000번 포트로 시작한다.

```powershell
& 'D:\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' `
  'D:\Unreal Projects\UnrealEngineLab\UnrealEngineLab.uproject' /Engine/Maps/Templates/Template_Default `
  -ModelContextProtocolStartServer -ModelContextProtocolPort=8000
```

2. 플러그인 저장소를 측정한 커밋(`a6aa73a`)으로 받아 둔다. 설치하지 않고 `--plugin-dir`로 한 세션에만 붙인다.
3. 빈 폴더를 하나 만들고 `UnrealEngineLab.uproject`와 `.mcp.json` 사본만 넣는다. 저장소 문서가 답에 섞이지 않게 하려는 것이다. 플러그인의 시작 훅은 이 `.uproject`를 보고 언리얼 프로젝트로 인식한다.
4. `claude auth status`로 Claude Code CLI 로그인을 확인한다.

## 실행

에디터 조회만 한다. 정답과 엔진 상태를 `Docs/UE/Evidence/UnrealEngineSkills/`에 기록한다.

```powershell
python Scripts/UnrealEngineSkills/check_editor.py
```

같은 질문을 플러그인 있을 때와 없을 때 번갈아 실행한다. [plan.json](plan.json)에 질문, 모델(`sonnet`), 허용 도구(Unreal MCP 3개, `Skill`, `ToolSearch`, `Read`, `Grep`, `Glob`)가 들어 있다. 수정 도구(`Bash`, `Edit`, `Write`)는 처음부터 주지 않는다.

```powershell
python Scripts/UnrealEngineSkills/run_ab.py --plan Scripts/UnrealEngineSkills/plan.json `
  --plugin-dir <플러그인 폴더> --cwd <빈 폴더>
```

실행마다 stream-json 원본은 `Saved/UnrealEngineSkills/runs/`에, 요약 한 줄은 `Docs/UE/Evidence/UnrealEngineSkills/summary.jsonl`에 쌓인다. 문서의 "파일 도구를 막았을 때" 표는 `plan.json`의 `tools`를 `["Skill", "ToolSearch"]`로 바꾸고 저장소 루트에서 실행한 결과다(`--output summary_mcp_only.jsonl`).

`call_tool`을 허용하면 그 안의 모든 툴셋을 호출할 수 있다. 질문에 "수정하거나 저장하지 마"를 넣었지만 강제 장치는 아니므로 저장하지 않을 테스트 맵에서만 실행한다. 30번 실행하는 데 API 환산 비용으로 약 8.4달러가 들었다.
