"""Assemble real captures, an explicitly schematic diagram, and the live tool index."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "Docs/UE/Images"
FONT = "C:/Windows/Fonts/malgun.ttf"


def main():
    Image.open(IMAGES / "unreal-mcp-settings.png").crop((20, 75, 1450, 350)).save(IMAGES / "unreal-mcp-settings-detail.png")
    frames = []
    labels = ["생성 / 위치 (0, 0, 100)", "실제 Transform 읽기", "X = 100 cm", "X = 200 cm", "Z = 180 cm", "Yaw = 45°", "Yaw = 90° / 결과 확인"]
    for path, label in zip(sorted((ROOT / "Saved/UnrealMCPDocs/demo").glob("*.png")), labels):
        source = Image.open(path).convert("RGB")
        source.thumbnail((1000, 640))
        frame = Image.new("RGB", (1000, 700), "#111923")
        frame.paste(source, ((1000-source.width)//2, 60))
        ImageDraw.Draw(frame).text((25, 15), "실제 Unreal MCP 호출 · " + label, font=ImageFont.truetype(FONT, 23), fill="white")
        frames.append(frame)
    frames[0].save(IMAGES / "unreal-mcp-cube-demo.gif", save_all=True, append_images=frames[1:], duration=[1200]*6+[2000], loop=0)
    canvas = Image.new("RGB", (1400, 610), "#101923")
    draw = ImageDraw.Draw(canvas)
    def label(pos, text, size=24, fill="#e7eff8"):
        draw.text(pos, text, font=ImageFont.truetype(FONT, size), fill=fill)
    label((45, 28), "Unreal MCP · 요청이 실제 에디터 작업이 되기까지", 32)
    boxes = [(45,130,330,290), (420,130,745,290), (835,130,1355,290)]
    titles = [("AI 클라이언트", "Codex / Claude Code 등"), ("Unreal MCP 서버", "ModelContextProtocol"), ("Toolset Registry", "등록된 툴셋 + 함수 스키마")]
    for box, (title, sub) in zip(boxes, titles):
        draw.rounded_rectangle(box, radius=12, fill="#203448", outline="#5c9cd0", width=2)
        label((box[0]+22,box[1]+30),title,27)
        label((box[0]+22,box[1]+85),sub,21)
    for x1,x2 in [(335,415),(750,830)]:
        draw.line((x1,210,x2,210), fill="#75b9ed", width=4)
        draw.polygon([(x2,210),(x2-14,202),(x2-14,218)], fill="#75b9ed")
    label((48,320),"HTTP / JSON-RPC → http://127.0.0.1:8000/mcp",23)
    label((48,363),"list_toolsets → describe_toolset → call_tool",24, "#9dd7be")
    draw.line((1090,295,1090,410),fill="#75b9ed",width=4)
    draw.rounded_rectangle((730,410,1355,550), radius=12, fill="#203448", outline="#5c9cd0",width=2)
    label((755,431),"SceneTools / BlueprintTools / SlateInspector …",23)
    label((755,477),"게임 스레드에서 에디터 API 실행 → 결과 반환",22)
    label((48,550),"구조 설명용 도식 · 실제 화면 캡처는 본문의 설정 화면과 데모 GIF",19,"#a3b4c5")
    canvas.save(IMAGES / "unreal-mcp-architecture.png")
    catalog = json.loads((ROOT / "Docs/UE/Evidence/UnrealMCP/catalog.json").read_text(encoding="utf-8"))
    lines = ["# Unreal MCP 툴셋 전체 목록", "", "[연결·구조·사용 예제 본문](UnrealMCP.md)", "",
             "2026-10-23 UE 5.8.3 실행 세션의 실제 `describe_toolset` 응답에서 생성했다. 53개 툴셋, 836개 도구다. 목록 조회는 전체 완료했으며, 모든 도구를 실행 검증한 것은 아니다. 이름을 클릭하면 원본 스키마를 볼 수 있다. `AIWidgetInspector`는 프로젝트 전용 확장이다.", ""]
    for item in catalog:
        name = item["name"]
        lines += ["## " + name.rsplit(".",1)[-1], "", f"식별자: `{name}` · {len(item['tools'])}개 도구", "", item["description"], "",
                  f"[원본 입력·반환 스키마](Evidence/UnrealMCP/{name}.json)", "", "도구: " + ", ".join("`"+x+"`" for x in item["tools"]), ""]
    (ROOT / "Docs/UE/UnrealMCPToolsets.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
