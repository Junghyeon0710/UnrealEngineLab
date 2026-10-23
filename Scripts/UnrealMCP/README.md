# Unreal MCP 문서 재현

[학습 문서](../../Docs/UE/UnrealMCP.md)와 [전체 툴셋 목록](../../Docs/UE/UnrealMCPToolsets.md)의 자료를 만든 스크립트다. Git 커밋·푸시는 수행하지 않는다.

에디터에서 Unreal MCP와 필요한 툴셋을 켜고 서버를 시작한 후 저장소 루트에서 실행한다. Python 3가 필요하며, 이미지 조립에는 Pillow가 필요하다.

```powershell
python Scripts/UnrealMCP/collect_inventory.py --endpoint http://127.0.0.1:8000/mcp
```

위 명령은 조회만 수행하며 `Docs/UE/Evidence/UnrealMCP/`에 스키마와 응답을 기록한다. 현재 목록을 대상으로 매번 순서대로 호출한다.

`record_demo.py`는 **현재 열린 맵에 큐브를 추가하고 제거한다**. 저장하지 않을 테스트 맵에서만 실행한다. 촬영 당시 `/Engine/Maps/Templates/Template_Default`를 사용했다. 실행 후 카메라를 복원하며 맵은 저장하지 않는다. 추가·삭제 때문에 에디터의 맵 dirty 표시가 생길 수 있다. 기존 작업 맵에서 실행하지 않는다.

```powershell
python Scripts/UnrealMCP/record_demo.py
python Scripts/UnrealMCP/build_media.py
```

`build_media.py`는 원본 캡처로 단계별 GIF와 설정 화면 크롭을 만들고, 구조 설명용 도식과 전체 카탈로그를 생성한다. GIF는 실시간 영상이 아닌 도구 호출 단계별 실제 스크린샷이다. 원본 프레임은 `Saved/UnrealMCPDocs/demo/`에 있다.

`mcp_client.py`는 이 로컬 서버 테스트용 소형 HTTP 클라이언트다. 전체 MCP SDK를 대체하는 구현은 아니며, 세션 초기화와 단일 응답 JSON/SSE를 처리한다. 실제 AI 클라이언트 연결 설정은 문서의 Codex 예제를 참고한다.

미리보기: `node Scripts/UnrealMCP/generate_preview.mjs <marked.esm.js의 경로>`. HTML은 `Saved/DocumentationPreview/UnrealMCP/`에 생성한다.
