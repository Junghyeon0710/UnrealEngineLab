// 문서 원문을 읽기 전용 HTML로 렌더링한다. 생성물은 Git에서 제외된 Saved/에 둔다.
// 실행: node Scripts/MotionWarping/generate_preview.mjs <marked의 lib/marked.esm.js 경로>
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

if (!process.argv[2]) throw new Error('marked.esm.js 경로를 인자로 전달하세요.');
const { marked } = await import(pathToFileURL(path.resolve(process.argv[2])).href);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const source = await readFile(path.join(root, 'Docs/UE/MotionWarping.md'), 'utf8');
const output = path.join(root, 'Saved/DocumentationPreview/MotionWarping');
await mkdir(output, { recursive: true });
const body = marked.parse(source, { gfm: true }).replace(
  /\b(src|href)="(?!https?:|#|\/)([^"]+)"/g,
  (_, attribute, value) => `${attribute}="${new URL(value, 'http://localhost/Docs/UE/').pathname}"`
);
const html = `<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Motion Warping — UnrealEngineLab 로컬 검토본</title>
<style>
:root{color-scheme:light;--ink:#192435;--muted:#526578;--line:#dce4ed;--accent:#007d74}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:28px}
body{margin:0;background:#f4f7fa;color:var(--ink);font:16px/1.85 "Malgun Gothic",system-ui,sans-serif;word-break:keep-all;overflow-wrap:anywhere}
header{background:#101925;color:#dce9f8;padding:22px 4vw;border-bottom:3px solid #50dfce}
header strong{font-size:18px;letter-spacing:.05em}header span{display:inline-block;margin-left:22px;color:#b4c7db;font-size:13px}
.layout{max-width:1420px;margin:32px auto;display:grid;grid-template-columns:235px minmax(0,1fr);gap:30px;padding:0 28px}
nav{position:sticky;top:24px;align-self:start;font-size:13px;max-height:94vh;overflow:auto}
nav strong{display:block;color:var(--muted);font-size:12px;letter-spacing:.1em;margin-bottom:14px}nav a{display:block;color:#4c6174;padding:6px 8px;line-height:1.55;border-left:2px solid #dce4ed;text-decoration:none}nav a:hover{color:var(--accent);background:#e5f5f1;border-color:var(--accent)}
article{background:white;border:1px solid var(--line);border-radius:14px;padding:42px 48px;min-width:0;box-shadow:0 4px 24px #172c4510}
h1,h2,h3{line-height:1.5;letter-spacing:-.025em}h1{font-size:32px;margin:0 0 28px}h2{font-size:25px;margin:36px 0 18px;padding-bottom:12px;border-bottom:1px solid var(--line)}h3{font-size:19px;margin:28px 0 12px}
p{margin:16px 0}a{color:var(--accent);text-underline-offset:3px}strong{font-weight:700}em{color:var(--muted);font-size:13px;font-style:normal;line-height:1.7;display:inline-block}
img{display:block;max-width:100%;height:auto;border-radius:9px;margin:20px auto;border:1px solid #d4dfe9}table img{margin:4px auto;border-radius:5px}table{width:100%;border-collapse:collapse;font-size:14px;margin:22px 0}th,td{border:1px solid var(--line);padding:11px 13px;text-align:left;vertical-align:top}th{background:#edf4f7;font-weight:700}tr:nth-child(even) td{background:#f9fbfd}
code{font:13px/1.6 Consolas,"Malgun Gothic",monospace;background:#edf2f7;border-radius:4px;padding:2px 5px}pre{background:#152231;color:#e6edf6;padding:22px;overflow:auto;border-radius:9px;white-space:pre;word-break:normal;overflow-wrap:normal}pre code{background:none;padding:0;color:inherit;font-size:13px}
hr{border:0;border-top:1px solid var(--line);margin:42px 0}li{margin:5px 0}ol,ul{padding-left:26px}footer{font-size:12px;color:var(--muted);text-align:center;padding:15px}
@media(max-width:1100px){.layout{grid-template-columns:1fr;max-width:1000px}nav{display:none}article{padding:30px}}
@media(max-width:600px){body{font-size:15px}.layout{margin:12px auto;padding:0 10px}article{padding:22px 17px}header span{display:block;margin:6px 0 0}h1{font-size:26px}h2{font-size:22px}td,th{padding:8px;font-size:12px}pre{padding:14px}img{border-radius:4px}}
</style></head><body>
<header><strong>UNREAL ENGINE LAB</strong><span>Motion Warping 공부 · 샘플 설정과 실제 비교</span></header>
<div class="layout"><nav aria-label="문서 목차"><strong>CONTENTS</strong><div id="nav"></div></nav><article>${body}</article></div>
<footer>원문: Docs/UE/MotionWarping.md · HTML은 원문에서 생성한 미리보기입니다.</footer>
<script>
const nav = document.querySelector('#nav');
document.querySelectorAll('article h2').forEach((h,i) => {
  h.id = 'preview-section-' + i;
  const a = document.createElement('a'); a.href = '#'+h.id; a.textContent = h.textContent; nav.append(a);
});
</script></body></html>`;
await writeFile(path.join(output, 'index.html'), html, 'utf8');
console.log(path.join(output, 'index.html'));
