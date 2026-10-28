# -*- coding: utf-8 -*-
"""
HrioAPI 官方 SDK 内置封装模块
无需额外安装外部依赖，内置支持 https://hrioapi.hrio.site 平台各图像大模型调用。
支持文生图、参考图生图（图生图）、多模态媒体输入。
"""

import os
import json
import base64
import mimetypes
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, Tuple, List, Union

DEFAULT_BASE_URL = "https://hrioapi.hrio.site/v1"
OFFICIAL_WEBSITE = "https://hrioapi.hrio.site"


class HrioAPIError(Exception):
    """HrioAPI 平台请求异常"""
    pass


def file_to_data_uri(file_path: str) -> str:
    """将本地图片文件编码为 Data URI (base64)"""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"未找到本地图片文件: {file_path}")
    
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "image/jpeg" if file_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
        
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


class HrioClient:
    """
    轻量自包含 HrioAPI 客户端。
    支持传入 api_key，若未传则自动读取环境变量 HRIO_API_KEY。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 180,
    ):
        self.api_key = (api_key or os.environ.get("HRIO_API_KEY", "")).strip()
        self.base_url = (base_url or os.environ.get("HRIO_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.timeout = timeout

    def check_auth(self):
        if not self.api_key:
            raise HrioAPIError(
                f"\n[错误] 未检测到有效的 API Key！\n"
                f"请前往官方网站注册并获取您的 API Key: {OFFICIAL_WEBSITE}\n"
                f"使用方式：\n"
                f"  1. 环境变量配置：export HRIO_API_KEY=\"sk-xxxx\" 或 set HRIO_API_KEY=\"sk-xxxx\"\n"
                f"  2. 代码传参配置：client = HrioClient(api_key=\"sk-xxxx\")\n"
                f"  3. 命令行参数：python main.py --key \"sk-xxxx\"\n"
            )

    def generate_image(
        self,
        model: str,
        prompt: str,
        images: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        调用图像生成接口。
        支持：
          - 文生图 (仅传 prompt)
          - 图生图 / 参考图生图 (传 images=[local_path_or_url])
        """
        self.check_auth()

        url = f"{self.base_url}/images/generations"
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
        }

        # 处理参考图（支持本地文件路径自动转 base64 data URI 或 http/https 链接）
        if images:
            formatted_images: List[str] = []
            for img in images:
                img_str = str(img).strip()
                if img_str.startswith(("http://", "https://", "data:")):
                    formatted_images.append(img_str)
                elif os.path.isfile(img_str):
                    formatted_images.append(file_to_data_uri(img_str))
                else:
                    formatted_images.append(img_str)
            payload["images"] = formatted_images
            payload["media"] = [{"kind": "image", "url": u} for u in formatted_images]

        if parameters:
            payload.update(parameters)

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "banano2gif-sdk/1.1",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_text = resp.read().decode("utf-8")
                return json.loads(resp_text)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise HrioAPIError(
                f"HTTP 请求失败 ({e.code}): {err_body}\n"
                f"请检查 Key 余额或前往官网管理：{OFFICIAL_WEBSITE}"
            ) from e
        except Exception as e:
            raise HrioAPIError(f"请求失败: {e}") from e

    def extract_image_bytes_or_url(self, resp_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[bytes]]:
        """从响应体中解析图片 URL 或 Base64 图片二进制"""
        if not isinstance(resp_data, dict):
            return None, None

        items = resp_data.get("data")
        if isinstance(items, list) and items:
            first = items[0]
            if isinstance(first, dict):
                if first.get("url"):
                    return first["url"], None
                if first.get("b64_json"):
                    return None, base64.b64decode(first["b64_json"])

        for k in ("url", "image_url", "output_url"):
            val = resp_data.get(k)
            if isinstance(val, str) and val.startswith(("http://", "https://")):
                return val, None

        return None, None
