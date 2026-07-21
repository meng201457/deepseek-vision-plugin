"""DeepSeek Vision 插件图片识别逻辑。"""

import os
import tempfile
from pathlib import Path
from typing import Optional

from .auth import AuthManager


class ImageRecognizer:
    """封装 DeepSeek 图片识别流程。"""

    def __init__(self, auth_manager: AuthManager) -> None:
        self._auth = auth_manager

    async def recognize_image_file(self, image_path: str, logger, _retried: bool = False) -> Optional[str]:
        """从文件路径识别图片。

        Args:
            image_path: 图片文件路径。
            logger: 日志实例。

        Returns:
            识别结果文本，失败返回 None。
        """
        client = self._auth.client
        if not client:
            return None

        try:
            result = client.recognize_image(image_path)
            return result if result else None
        except Exception as e:
            if not _retried and self._is_auth_error(e):
                logger.warning("Token 可能过期，尝试刷新...")
                if await self._auth.refresh_token(logger):
                    return await self.recognize_image_file(image_path, logger, _retried=True)
            logger.error("DeepSeek 图片识别失败: %s", e)
            return None

    async def recognize_image_bytes(
        self, image_data: bytes, logger, suffix: str = ".jpg", _retried: bool = False,
    ) -> Optional[str]:
        """从字节数据识别图片。

        Args:
            image_data: 图片二进制数据。
            logger: 日志实例。
            suffix: 临时文件后缀。

        Returns:
            识别结果文本，失败返回 None。
        """
        client = self._auth.client
        if not client:
            logger.warning("DeepSeek client 未初始化")
            return None

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(image_data)
                tmp_path = tmp.name

            logger.info("临时文件: %s, 大小: %d bytes", tmp_path, len(image_data))
            result = client.recognize_image(tmp_path)
            logger.info("DeepSeek 返回结果: %s", result[:100] if result else "EMPTY")
            return result if result else None
        except Exception as e:
            logger.error("DeepSeek 识别异常: %s", e)
            if not _retried and self._is_auth_error(e):
                logger.warning("Token 可能过期，尝试刷新...")
                if await self._auth.refresh_token(logger):
                    return await self.recognize_image_bytes(image_data, logger, suffix, _retried=True)
            return None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    async def recognize_by_hash(self, message_id: str, prompt: str, logger) -> Optional[str]:
        """通过消息 ID 查找图片并识别。

        Args:
            message_id: 消息 ID。
            prompt: 自定义提示词。
            logger: 日志实例。

        Returns:
            识别结果文本，失败返回 None。
        """
        try:
            from src.common.message_repository import find_messages
        except ImportError as e:
            logger.debug("消息仓库模块不可用: %s", e)
            return None

        messages = find_messages(platform="qq", message_id=message_id, limit=1)
        if not messages:
            logger.warning("未找到消息: %s", message_id)
            return None

        msg = messages[0]

        # 从 raw_message 中提取图片组件
        image_component = None
        if msg.raw_message:
            components = (
                msg.raw_message.components
                if hasattr(msg.raw_message, "components")
                else msg.raw_message
            )
            for component in components:
                if hasattr(component, "type") and component.type == "image":
                    image_component = component
                    break

        if not image_component:
            logger.warning("消息中无图片组件: %s", message_id)
            return None

        image_hash = getattr(image_component, "binary_hash", None)
        if not image_hash:
            logger.warning("图片组件无 binary_hash: %s", message_id)
            return None

        logger.info("找到图片哈希 (MD5): %s", image_hash)

        # 从 data/images 目录查找
        project_root = Path(__file__).parent.parent.parent
        image_dir = project_root / "data" / "images"

        if image_dir.exists():
            # 先用 MD5 哈希匹配文件名
            for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
                image_path = image_dir / f"{image_hash}{ext}"
                if image_path.exists():
                    logger.info("找到图片文件 (MD5): %s", image_path)
                    return await self.recognize_image_file(str(image_path), logger)

            # MD5 未匹配，扫描所有图片计算 MD5
            import hashlib
            for f in image_dir.iterdir():
                if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
                    try:
                        file_md5 = hashlib.md5(f.read_bytes()).hexdigest()
                        if file_md5 == image_hash:
                            logger.info("找到图片文件 (MD5匹配): %s", f)
                            return await self.recognize_image_file(str(f), logger)
                    except Exception:
                        continue

        logger.debug("未找到哈希为 %s 的图片文件", image_hash)
        return None

    @staticmethod
    def _is_auth_error(e: Exception) -> bool:
        """判断是否为认证相关错误。"""
        msg = str(e)
        return "401" in msg or "403" in msg or "token" in msg.lower()
