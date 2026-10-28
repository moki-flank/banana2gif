# -*- coding: utf-8 -*-
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from banano2gif import Banano2Gif, ACTION_PRESETS, OFFICIAL_WEBSITE, DEFAULT_BASE_URL, DEFAULT_MODEL


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def _inline_generated_images(resp_obj: dict) -> dict:
    """Download remote image URLs in /images/generations response on backend to prevent browser Canvas CORS tainting."""
    if not isinstance(resp_obj, dict):
        return resp_obj
    items = resp_obj.get("data")
    if not isinstance(items, list):
        return resp_obj
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("b64_json") and not item.get("data_url"):
            item["data_url"] = f"data:image/png;base64,{item['b64_json']}"
            continue
        img_url = item.get("url")
        if isinstance(img_url, str) and img_url.startswith(("http://", "https://")) and not item.get("b64_json"):
            try:
                req = urllib.request.Request(
                    img_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) banano2gif-proxy/1.1",
                        "Referer": "https://hrioapi.hrio.site/",
                    },
                )
                with urllib.request.urlopen(req, timeout=120) as r:
                    raw = r.read()
                    ctype = (r.headers.get("Content-Type") or "image/png").split(";")[0].strip()
                b64_str = base64.b64encode(raw).decode("ascii")
                item["b64_json"] = b64_str
                item["data_url"] = f"data:{ctype};base64,{b64_str}"
            except Exception:
                pass
    return resp_obj


class Banano2GifRequestHandler(SimpleHTTPRequestHandler):
    """内置支持 HrioAPI 全接口代理 (/api/v1/*, /v1/*) 与远程媒体无损代理 (/api/proxy, /api/proxy_js) 的本地消跨域服务"""

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def _is_hrio_api_path(self) -> bool:
        p = self.path.split("?", 1)[0]
        return p.startswith("/api/v1/") or p.startswith("/v1/")

    def _handle_hrio_api_proxy(self, method: str):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        clean_path = parsed.path
        if clean_path.startswith("/api/v1/"):
            subpath = clean_path[len("/api/v1/"):]
        elif clean_path.startswith("/v1/"):
            subpath = clean_path[len("/v1/"):]
        else:
            subpath = clean_path.lstrip("/")

        target_base = (
            self.headers.get("X-Target-Base-Url")
            or (qs.get("target_base") or [""])[0]
            or os.environ.get("HRIO_BASE_URL")
            or DEFAULT_BASE_URL
        ).strip().rstrip("/")

        forward_qs = {k: v for k, v in qs.items() if k not in ("target_base", "api_key")}
        query_str = urllib.parse.urlencode(forward_qs, doseq=True)
        target_url = f"{target_base}/{subpath}"
        if query_str:
            target_url = f"{target_url}?{query_str}"

        auth_header = (self.headers.get("Authorization") or "").strip()
        if not auth_header or auth_header.lower() == "bearer":
            q_key = (qs.get("api_key") or [""])[0].strip()
            env_key = os.environ.get("HRIO_API_KEY", "").strip()
            use_key = q_key or env_key
            if use_key:
                auth_header = use_key if use_key.lower().startswith("bearer ") else f"Bearer {use_key}"

        length = int(self.headers.get("Content-Length", "0") or "0")
        body_bytes = self.rfile.read(length) if length > 0 else None

        req_headers = {
            "User-Agent": "banano2gif-proxy/1.1",
            "Accept": "application/json, */*",
        }
        if self.headers.get("Content-Type"):
            req_headers["Content-Type"] = self.headers.get("Content-Type")
        elif body_bytes is not None:
            req_headers["Content-Type"] = "application/json"
        if auth_header:
            req_headers["Authorization"] = auth_header

        req = urllib.request.Request(
            target_url,
            data=body_bytes,
            headers=req_headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                resp_bytes = resp.read()
                status_code = resp.status
                ctype = resp.headers.get("Content-Type", "application/json; charset=utf-8")
        except urllib.error.HTTPError as e:
            resp_bytes = e.read()
            status_code = e.code
            ctype = e.headers.get("Content-Type", "application/json; charset=utf-8") if e.headers else "application/json; charset=utf-8"
        except Exception as e:
            err_payload = json.dumps({"error": {"message": f"本地代理请求上游失败: {e}"}}, ensure_ascii=False).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(err_payload)))
            self.end_headers()
            self.wfile.write(err_payload)
            return

        if status_code == 200 and "images/generations" in subpath:
            try:
                resp_obj = json.loads(resp_bytes.decode("utf-8"))
                resp_obj = _inline_generated_images(resp_obj)
                resp_bytes = json.dumps(resp_obj, ensure_ascii=False).encode("utf-8")
                ctype = "application/json; charset=utf-8"
            except Exception:
                pass

        self.send_response(status_code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.end_headers()
        self.wfile.write(resp_bytes)

    def do_POST(self):
        if self._is_hrio_api_path():
            self._handle_hrio_api_proxy("POST")
            return
        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        if self._is_hrio_api_path():
            self._handle_hrio_api_proxy("GET")
            return

        if self.path.startswith("/api/ping"):
            env_key = os.environ.get("HRIO_API_KEY", "").strip()
            body = json.dumps({
                "ok": True,
                "service": "banano2gif-proxy",
                "has_env_key": bool(env_key),
                "default_key": env_key,
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path.startswith("/api/proxy_js") or self.path.startswith("/api/proxy"):
            is_js = self.path.startswith("/api/proxy_js")
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            target_url = (qs.get("url") or [""])[0].strip()
            req_id = (qs.get("id") or ["cb"])[0].strip()

            if not target_url.startswith(("http://", "https://")):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid target url")
                return

            try:
                req = urllib.request.Request(
                    target_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) banano2gif/1.1",
                        "Referer": "https://hrioapi.hrio.site/",
                    },
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = resp.read()
                    ctype = resp.headers.get("Content-Type", "application/octet-stream")

                if is_js:
                    b64_str = base64.b64encode(data).decode("ascii")
                    payload_obj = json.dumps({"ok": True, "mime": ctype, "b64": b64_str})
                    payload_js = (
                        f"(window.__B2G_PROXY_RESOLVE || window.__B2L_PROXY_RESOLVE) && "
                        f"(window.__B2G_PROXY_RESOLVE || window.__B2L_PROXY_RESOLVE)({json.dumps(req_id)}, {payload_obj});"
                    ).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/javascript; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload_js)))
                    self.end_headers()
                    self.wfile.write(payload_js)
                else:
                    self.send_response(200)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
            except Exception as e:
                if is_js:
                    err_obj = json.dumps({"ok": False, "error": str(e)})
                    payload_js = (
                        f"(window.__B2G_PROXY_RESOLVE || window.__B2L_PROXY_RESOLVE) && "
                        f"(window.__B2G_PROXY_RESOLVE || window.__B2L_PROXY_RESOLVE)({json.dumps(req_id)}, {err_obj});"
                    ).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/javascript; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload_js)))
                    self.end_headers()
                    self.wfile.write(payload_js)
                else:
                    err_bytes = json.dumps({"ok": False, "error": str(e)}).encode("utf-8")
                    self.send_response(502)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(err_bytes)))
                    self.end_headers()
                    self.wfile.write(err_bytes)
            return

        if self.path in ("/", "/index.html"):
            self.path = "/web/index.html"
        return super().do_GET()


def main():
    parser = argparse.ArgumentParser(
        description="banano2gif: 支持 3x3 (9帧) 与 4x4 (16帧)、4K超高分、文生、图生、视频生、动作迁移、智能透明背景的 AI 动图引擎",
        epilog=f"获取官方 API Key 请访问: {OFFICIAL_WEBSITE}",
    )
    parser.add_argument("prompt", nargs="?", default="", help="动作或表情包描述（选填）")
    parser.add_argument("--grid", choices=["3x3", "4x4", "9", "16"], default="3x3", help="网格控制精度：3x3 (9帧经典微动) 或 4x4 (16帧高帧率超丝滑，默认 3x3)")
    parser.add_argument("--image", default="", help="【图生/动作迁移】目标角色人设参考图路径或 URL (进行锁脸/锁人设)")
    parser.add_argument("--motion-source", default="", help="【动作迁移】提供动作模板来源的动图/视频文件 (.gif, .webp, .mp4)，从中抽取动作九/十六宫格迁移给 --image 目标角色")
    parser.add_argument("--video", default="", help="【视频生动图】传入本地视频文件路径 (.mp4, .mov 等) 直接转为表情包 GIF/WebP")
    parser.add_argument("--preset", choices=list(ACTION_PRESETS.keys()), help="选择内置微动作模板 (waving, petting, laughing, crying, heart_wink, thumbs_up)")
    parser.add_argument("--list-presets", action="store_true", help="查看所有支持的内置动作模板")
    parser.add_argument("--4k", action="store_true", dest="is_4k", help="【4K 超高清规格】开启 4096x4096 极致九/十六宫格生图与高精度自适应切图")
    parser.add_argument("--export-size", type=int, default=None, help="导出动图单帧尺寸（如 320 或 480，适合表情包体积限制；不传则保持原生分辨率）")
    parser.add_argument("--transparent", action="store_true", help="【智能去底】自动识别外围纯色背景并透明化（输出含 Alpha 通道的高清透明 WebP 与 GIF）")
    parser.add_argument("--style", default="High-end 3D animation render, soft ambient lighting, clean solid white background, Pop Mart collectible figurine style", help="画面风格")
    parser.add_argument("--key", default="", help=f"HrioAPI Key (未指定则读取环境变量 HRIO_API_KEY，可在 {OFFICIAL_WEBSITE} 获取)")
    parser.add_argument("--base-url", default="", help=f"API 基址 (默认: {DEFAULT_BASE_URL})")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"生图模型 (默认: {DEFAULT_MODEL})")
    parser.add_argument("--duration", type=int, default=None, help="每帧毫秒数 (3x3默认 180ms, 4x4默认 100ms)")
    parser.add_argument("--fps", type=int, default=10, help="视频转动图时的采样帧率 (默认 10 FPS)")
    parser.add_argument("--out", default="output", help="产物输出目录 (默认 output/)")
    parser.add_argument("--serve", nargs="?", const=8096, type=int, default=None, help="启动内置防跨域 Web 工作台服务 (默认端口 8096)")
    parser.add_argument("--no-browser", action="store_true", help="配合 --serve 使用，启动服务时不自动弹出浏览器")

    args = parser.parse_args()

    if args.serve is not None:
        port = int(args.serve)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        os.chdir(project_root)
        url = f"http://127.0.0.1:{port}/web/index.html"
        print(f"\n🍌 banano2gif Web 工作台与防跨域代理服务已启动: {url}")
        print(f"   - HrioAPI 跨域代理: http://127.0.0.1:{port}/api/v1/images/generations")
        print(f"   - 媒体二进制代理:   http://127.0.0.1:{port}/api/proxy?url=...")
        if not args.no_browser:
            try:
                webbrowser.open(url)
            except Exception:
                pass
        server = ThreadedHTTPServer(("127.0.0.1", port), Banano2GifRequestHandler)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止 banano2gif Web 服务。")
        return

    if args.list_presets:
        print("\n=== banano2gif 内置微动作预设 ===")
        for k, v in ACTION_PRESETS.items():
            print(f"  * {k:12s} - {v['title']} ({v['description']})")
        print(f"\n使用示例: python main.py \"可爱的柴犬\" --preset waving --grid 4x4 --transparent\n")
        return

    app = Banano2Gif(
        api_key=args.key,
        base_url=args.base_url,
        model=args.model,
    )

    try:
        # 模式 1: 动作生成迁移 (Motion Transfer)
        if args.motion_source and args.image:
            res = app.transfer_motion(
                source_media=args.motion_source,
                target_image=args.image,
                action_hint=args.prompt or "transfer the exact motion and poses from the motion guide to the target character",
                grid=args.grid,
                style=args.style,
                output_dir=args.out,
                duration_ms=args.duration,
                transparent=args.transparent,
                is_4k=args.is_4k,
                export_size=args.export_size,
            )
            print("\n" + "=" * 50)
            print("🎉 动作迁移大功告成！")
            print(f"🎥 源动作媒体: {res['source_media']}")
            print(f"🖼️ 目标角色图: {res['target_image']}")
            print(f"📐 网格规格:   {res['grid']}")
            print(f"📁 生成的迁移图: {res['grid_image']}")
            print(f"✨ 最终迁移 GIF: {res['gif_path']}")
            print(f"🌐 最终迁移 WebP: {res.get('webp_path')}")
            print(f"🔍 透明化去底: {'已开启' if args.transparent else '未开启'}")
            print("=" * 50 + "\n")
            return

        # 模式 2: 纯视频转动图 (Video-to-GIF)
        if args.video:
            out_file = os.path.join(args.out, "video_animation.gif")
            res = app.video_to_gif(video_path=args.video, output_path=out_file, fps=args.fps)
            print("\n" + "=" * 50)
            print("🎉 视频转 GIF 成功！")
            print(f"🎥 输入视频: {res['video_input']}")
            print(f"✨ 最终动图: {res['gif_path']}")
            print("=" * 50 + "\n")
            return

        # 模式 3: 图生动图 (参考图)
        if args.image:
            res = app.image_to_gif(
                image_path=args.image,
                prompt=args.prompt or "smiling and waving happily",
                preset=args.preset,
                grid=args.grid,
                style=args.style,
                output_dir=args.out,
                duration_ms=args.duration,
                transparent=args.transparent,
                is_4k=args.is_4k,
                export_size=args.export_size,
            )
            print("\n" + "=" * 50)
            print("🎉 图生动图制作成功！")
            print(f"🖼️ 参考图片: {args.image}")
            print(f"📐 网格规格: {res['grid']} (共 {res['total_frames']} 帧)")
            print(f"📁 原图路径: {res['grid_image']}")
            print(f"✨ GIF 动图: {res['gif_path']}")
            print(f"🌐 WebP 动图: {res.get('webp_path')}")
            print(f"🔍 透明去底: {'已开启 (含Alpha通道)' if args.transparent else '未开启'}")
            print("=" * 50 + "\n")
            return

        if not args.prompt and not args.preset:
            parser.print_help()
            print(f"\n提示：请输入动作描述，或指定 --image 参考图，或使用 --motion-source 进行动作迁移。\n官方平台与 API Key 获取地址: {OFFICIAL_WEBSITE}\n")
            sys.exit(1)

        # 模式 4: 文生动图
        res = app.text_to_gif(
            prompt=args.prompt,
            preset=args.preset,
            grid=args.grid,
            style=args.style,
            output_dir=args.out,
            duration_ms=args.duration,
            transparent=args.transparent,
            is_4k=args.is_4k,
            export_size=args.export_size,
        )
        print("\n" + "=" * 50)
        print("🎉 文生动图制作成功！")
        print(f"📐 网格规格: {res['grid']} (共 {res['total_frames']} 帧)")
        print(f"📁 原图路径: {res['grid_image']}")
        print(f"✨ GIF 动图: {res['gif_path']}")
        print(f"🌐 WebP 动图: {res.get('webp_path')}")
        print(f"🔍 透明去底: {'已开启 (含Alpha通道)' if args.transparent else '未开启'}")
        print("=" * 50 + "\n")

    except Exception as e:
        print(f"\n[错误] {e}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
