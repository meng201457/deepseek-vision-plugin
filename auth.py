"""DeepSeek Vision 插件认证管理 - 登录、token 刷新与持久化。"""

import re
from pathlib import Path
from typing import Optional

from .dependencies import get_client_class

PLUGIN_DIR = Path(__file__).parent


class AuthManager:
    """管理 DeepSeek 认证状态。"""

    def __init__(self) -> None:
        self._client = None
        self._mobile: str = ""
        self._password: str = ""
        self._area_code: str = "+86"
        self._saving_token: bool = False

    @property
    def client(self):
        """当前 DeepSeek 客户端实例。"""
        return self._client

    @property
    def mobile(self) -> str:
        return self._mobile

    @property
    def password(self) -> str:
        return self._password

    @property
    def area_code(self) -> str:
        return self._area_code

    async def init_client(self, config_data: dict, logger) -> bool:
        """根据配置初始化客户端。

        Args:
            config_data: 插件配置字典。
            logger: 日志实例。

        Returns:
            bool: 初始化是否成功。
        """
        DeepSeekClient = get_client_class()
        if DeepSeekClient is None:
            logger.error("deepseek_vision 模块不可用，请检查依赖安装")
            return False

        # 兼容旧格式（扁平）和新格式（嵌套）
        auth_cfg = config_data.get("auth", config_data)
        token = auth_cfg.get("token", config_data.get("token", ""))
        mobile = auth_cfg.get("mobile", config_data.get("mobile", ""))
        password = auth_cfg.get("password", config_data.get("password", ""))
        area_code = auth_cfg.get("area_code", config_data.get("area_code", "+86"))

        self._mobile = mobile
        self._password = password
        self._area_code = area_code

        try:
            if token:
                self._client = DeepSeekClient(token=token)
                logger.info("DeepSeek 客户端初始化成功 (auth=token)")
                return True
            elif mobile and password:
                self._client = DeepSeekClient(
                    mobile=mobile, password=password, area_code=area_code,
                )
                new_token = await self._try_login_with_retry(self._client, logger)
                if new_token:
                    self._save_token(new_token)
                    logger.info("DeepSeek 客户端初始化成功 (auth=password, token已保存)")
                    return True
                else:
                    logger.warning("DeepSeek 登录失败，插件将不可用直到手动重启")
                    return False
            else:
                logger.warning("未配置认证信息（需要 token 或 mobile+password）")
                return False
        except Exception as e:
            logger.error("DeepSeek 客户端初始化失败: %s", e)
            self._client = None
            return False

    async def _try_login_with_retry(self, client, logger, max_retries: int = 3, delay: int = 10):
        """尝试登录，限流时自动等待重试。"""
        import asyncio

        for attempt in range(max_retries):
            try:
                token = client.login()
                return token
            except Exception as e:
                if "TOO_MANY_REQUESTS" in str(e) and attempt < max_retries - 1:
                    logger.warning(
                        "登录限流，%d秒后重试 (%d/%d)...",
                        delay, attempt + 1, max_retries,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("登录失败: %s", e)
                    return None
        return None

    async def refresh_token(self, logger) -> bool:
        """尝试用密码重新登录并更新 token。

        Returns:
            bool: 刷新是否成功。
        """
        DeepSeekClient = get_client_class()
        if DeepSeekClient is None:
            return False

        if not self._mobile or not self._password:
            logger.warning("无法刷新 token：未配置手机号或密码")
            return False

        try:
            client = DeepSeekClient(
                mobile=self._mobile,
                password=self._password,
                area_code=self._area_code,
            )
            new_token = await self._try_login_with_retry(client, logger, max_retries=2, delay=15)
            if new_token:
                self._client = client
                self._save_token(new_token)
                return True
            return False
        except Exception as e:
            logger.error("刷新 token 失败: %s", e)
            return False

    def _save_token(self, token: str) -> None:
        """将 token 持久化到 config.toml。"""
        if self._saving_token:
            return

        try:
            self._saving_token = True
            config_path = PLUGIN_DIR / "config.toml"
            if not config_path.exists():
                return

            content = config_path.read_text(encoding="utf-8")
            content = re.sub(
                r'^token\s*=\s*".*?"',
                f'token = "{token}"',
                content,
                flags=re.MULTILINE,
            )
            config_path.write_text(content, encoding="utf-8")
        except Exception:
            pass
        finally:
            self._saving_token = False

    def reset(self) -> None:
        """重置认证状态。"""
        self._client = None
