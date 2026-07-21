"""DeepSeek Vision 插件 - 使用 DeepSeek 网页 API 替代 MaiBot 默认 VLM 识别图片。"""

import base64
import os
import sys
from pathlib import Path
from typing import ClassVar, Optional

# 确保插件目录在 sys.path 中，以便导入同目录下的模块
_plugin_dir = str(Path(__file__).parent)
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

from maibot_sdk import MaiBotPlugin, Tool, HookHandler
from maibot_sdk.types import ToolParameterInfo, ToolParamType

from auth import AuthManager
from dependencies import ensure_dependencies, is_available
from image_recognizer import ImageRecognizer
from vlm_config import ensure_vlm_config


class DeepSeekVisionPlugin(MaiBotPlugin):
    """DeepSeek Vision 插件 - 劫持 MaiBot 的图片识别功能"""

    config_model = None  # 延迟赋值，避免循环导入

    _auth: AuthManager = None
    _recognizer: ImageRecognizer = None

    VLM_MODEL_NAME = "deepseek-vision-plugin"

    async def on_load(self) -> None:
        """插件加载：初始化依赖、客户端、VLM 配置。"""
        self.ctx.logger.info("DeepSeek Vision 插件已加载")
        self._auth = AuthManager()
        self._recognizer = ImageRecognizer(self._auth)

        ensure_dependencies(self.ctx.logger)
        await self._auth.init_client(self.get_plugin_config_data(), self.ctx.logger)
        ensure_vlm_config(self.ctx.logger)

    async def on_unload(self) -> None:
        """插件卸载：清理资源。"""
        self.ctx.logger.info("DeepSeek Vision 插件已卸载")
        if self._auth:
            self._auth.reset()

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        """配置热更新时重新初始化客户端。"""
        if scope == "self" and self._auth and not self._auth._saving_token:
            self.ctx.logger.info("DeepSeek Vision 配置已更新: version=%s", version)
            await self._auth.init_client(config_data, self.ctx.logger)

    @HookHandler("chat.receive.before_process", allow_kwargs_mutation=True)
    async def on_before_process(self, **kwargs):
        """劫持图片识别：在消息处理前，用 DeepSeek 网页 API 替换图片描述。"""
        if not self._auth.client:
            return

        message = kwargs.get("message")
        if not message or not isinstance(message, dict):
            return

        # 递归查找消息中的图片数据
        image_data = self._find_image_in_dict(message)
        if not image_data:
            return

        self.ctx.logger.info("检测到图片，正在使用 DeepSeek 识别...")

        # 记录图片哈希，用于后续取消 VLM 后台任务
        raw_message = message.get("raw_message", [])
        image_hash_to_cancel = None
        if isinstance(raw_message, list):
            for component in raw_message:
                if isinstance(component, dict) and component.get("type") == "image":
                    image_hash_to_cancel = component.get("binary_hash")
                    break

        description = await self._recognizer.recognize_image_bytes(image_data, self.ctx.logger)
        if not description:
            self.ctx.logger.warning("DeepSeek 未返回图片描述")
            return

        # 替换 raw_message 中的图片为文本描述
        if isinstance(raw_message, list):
            for i, component in enumerate(raw_message):
                if isinstance(component, dict) and component.get("type") == "image":
                    raw_message[i] = {"type": "text", "data": f"[图片（by DeepSeek Vision）：{description}]"}
                    self.ctx.logger.info("已替换图片为文本描述: %s...", description[:80])
                    break

        # 取消 VLM 后台任务，避免 "仍有 X 张图片正在等待识别" 警告
        if image_hash_to_cancel:
            await self._cancel_vlm_task(image_hash_to_cancel)

    @Tool(
        "deepseek_vision",
        description=(
            "使用 DeepSeek 识别图片内容。\n"
            "参数说明：\n"
            "- image_url：string，必填。支持以下格式：\n"
            "  - 图片 URL（http:// 或 https:// 开头）\n"
            "  - 本地文件路径（如 /path/to/image.jpg）\n"
            "  - 图片哈希值（从 MaiBot 数据库查找图片）\n"
            "- prompt：string，可选。自定义提示词。"
        ),
        parameters=[
            ToolParameterInfo(
                name="image_url",
                param_type=ToolParamType.STRING,
                description="图片 URL、本地文件路径或图片哈希值",
                required=True,
            ),
            ToolParameterInfo(
                name="prompt",
                param_type=ToolParamType.STRING,
                description="自定义提示词（可选）",
                required=False,
            ),
        ],
    )
    async def handle_vision(self, image_url: str, prompt: str = "", **kwargs):
        """手动调用图片识别的 Tool。"""
        if not self._auth.client:
            return {"success": False, "error": "client_not_initialized"}

        try:
            # Case 1: URL
            if image_url.startswith(("http://", "https://")):
                import requests as req
                resp = req.get(image_url, timeout=30)
                resp.raise_for_status()

                suffix = ".jpg"
                content_type = resp.headers.get("content-type", "")
                if "png" in content_type:
                    suffix = ".png"
                elif "gif" in content_type:
                    suffix = ".gif"

                result = await self._recognizer.recognize_image_bytes(resp.content, self.ctx.logger, suffix=suffix)

            # Case 2: Local file path
            elif os.path.isfile(image_url):
                result = await self._recognizer.recognize_image_file(image_url, self.ctx.logger)

            # Case 3: Try as image hash
            else:
                result = await self._recognizer.recognize_by_hash(image_url, prompt, self.ctx.logger)

            if result:
                return {"success": True, "result": result}
            else:
                return {"success": False, "error": "识别失败或未返回结果"}

        except Exception as e:
            self.ctx.logger.error("图片识别失败: %s", e)
            return {"success": False, "error": str(e)}

    def _find_image_in_dict(self, data) -> Optional[bytes]:
        """递归查找字典/列表中的图片二进制数据。"""
        if isinstance(data, dict):
            if data.get("type") == "image":
                b64 = data.get("binary_data_base64")
                if b64:
                    try:
                        return base64.b64decode(b64)
                    except Exception:
                        pass

            for v in data.values():
                result = self._find_image_in_dict(v)
                if result:
                    return result

        elif isinstance(data, list):
            for item in data:
                result = self._find_image_in_dict(item)
                if result:
                    return result

        return None

    async def _cancel_vlm_task(self, image_hash: str) -> None:
        """尝试取消 VLM 后台任务并标记图片已处理。"""
        try:
            # 通过数据库标记图片已处理，跳过 VLM
            await self.ctx.db.update(
                model_name="Images",
                data={"vlm_processed": True},
                filters={"image_hash": image_hash},
            )
            self.ctx.logger.debug("已标记图片 vlm_processed: %s", image_hash)
        except Exception as e:
            self.ctx.logger.debug("标记 vlm_processed 失败: %s", e)


def create_plugin() -> DeepSeekVisionPlugin:
    """创建 DeepSeek Vision 插件实例。"""
    return DeepSeekVisionPlugin()
