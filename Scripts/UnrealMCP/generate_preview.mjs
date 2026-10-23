import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const root = path.resolve(import.meta.dirname, '../..');
const { marked } = await import(pathToFileURL(process.argv[2]).href);
const dest = path.join(root, 'Saved/DocumentationPreview/UnrealMCP');
await fs.mkdir(dest, { recursive: true });
for (const [source, output] of [['UnrealMCP.md', 'index.html'], ['UnrealMCPToolsets.md', 'toolsets.html']]) {
  let md = await fs.readFile(path.join(root, 'Docs/UE', source), 'utf8');
  let body = marked.parse(md).replaceAll('src="Images/', 'src="/Docs/UE/Images/')
    .replaceAll('href="Evidence/', 'href="/Docs/UE/Evidence/')
    .replaceAll('href="UnrealMCPToolsets.md', 'href="toolsets.html')
    .replaceAll('href="UnrealMCP.md', 'href="index.html')
    .replaceAll('href="MotionWarping.md', 'href="/Docs/UE/MotionWarping.md')
    .replaceAll('href="README.md', 'href="/Docs/UE/README.md')
    .replaceAll('href="../../README.md', 'href="/README.md')
    .replaceAll('href="../../Scripts/', 'href="/Scripts/');
  const css = `*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f3f5f7;color:#25313d;font:17px/1.85 'Segoe UI','Malgun Gothic',sans-serif}header{background:#142434;color:#e6f0f7;padding:28px max(25px,calc((100vw - 1180px)/2));border-bottom:4px solid #5a9cca}header b{font-size:22px}header p{margin:5px 0 0;color:#bacbd9;font-size:14px}main{max-width:1180px;margin:30px auto;background:white;padding:45px 60px;border:1px solid #e0e5eb;border-radius:8px}h1{font-size:34px;line-height:1.4;margin:0 0 28px}h2{font-size:27px;margin-top:65px;border-bottom:2px solid #e1e8ee;padding-bottom:12px}h3{font-size:21px;margin-top:35px}p{margin:18px 0}a{color:#176798;text-underline-offset:4px}img{display:block;max-width:100%;height:auto;margin:28px auto;border:1px solid #e1e7ed;border-radius:5px}table{width:100%;border-collapse:collapse;margin:24px 0;font-size:15px;table-layout:fixed}td,th{text-align:left;padding:13px;border:1px solid #dbe3ea;overflow-wrap:anywhere}th{background:#edf3f7}tr:nth-child(even){background:#f8fafc}code{background:#eef2f5;font:14px/1.7 Consolas,monospace;padding:2px 5px;overflow-wrap:anywhere}pre{background:#172330;color:#e3edf7;padding:22px;overflow:auto;border-radius:6px}pre code{background:none;padding:0}blockquote{border-left:4px solid #65a4cf;background:#f1f7fb;padding:4px 22px;margin:22px 0}li{margin:8px 0}a[id]{scroll-margin-top:20px}.top{position:fixed;right:22px;bottom:20px;background:#19384e;padding:9px 18px;color:white;border-radius:25px;text-decoration:none}@media(max-width:800px){main{margin:0;padding:25px 18px}h1{font-size:27px}h2{font-size:23px}table{font-size:13px}td,th{padding:7px}}`;
  await fs.writeFile(path.join(dest, output), `<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Unreal MCP · 연결과 툴셋</title><style>${css}</style><header><b>UnrealEngineLab / Unreal MCP</b><p>UE 5.8.3 · 실제 연결 응답과 에디터 캡처 · 로컬 검토본</p></header><main id="top">${body}</main><a class="top" href="#top">맨 위로 ↑</a></html>`);
}
console.log(dest);
