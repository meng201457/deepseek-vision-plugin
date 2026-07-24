"""DeepSeek Vision 插件依赖检查。"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from maibot_sdk import MaiBotPlugin

_deepseek_vision_loaded: bool = False
DeepSeekClient = None


def is_available() -> bool:
    """检查 deepseek_vision 模块是否已可用。"""
    return _deepseek_vision_loaded


def get_client_class():
    """获取 DeepSeekClient 类，不可用时返回 None。"""
    return DeepSeekClient


def ensure_dependencies(logger) -> bool:
    """检查依赖是否已安装（由 MaiBot manifest 自动安装）。"""
    global DeepSeekClient, _deepseek_vision_loaded

    if _deepseek_vision_loaded:
        return True

    try:
        from deepseek_vision import DeepSeekClient as _Client
        DeepSeekClient = _Client
        _deepseek_vision_loaded = True
        return True
    except ImportError as e:
        logger.error("依赖未安装: %s，请确保 MaiBot 已自动安装 deepseek-pow 和 wasmtime", e)
        return False
