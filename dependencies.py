"""DeepSeek Vision 插件依赖管理 - 自动检查并安装缺失依赖。"""

import os
import struct
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from maibot_sdk import MaiBotPlugin

PLUGIN_DIR = Path(__file__).parent

_deepseek_vision_loaded: bool = False
DeepSeekClient = None


def is_available() -> bool:
    """检查 deepseek_vision 模块是否已可用。"""
    return _deepseek_vision_loaded


def get_client_class():
    """获取 DeepSeekClient 类，不可用时返回 None。"""
    return DeepSeekClient


def ensure_dependencies(logger) -> bool:
    """检查并自动安装缺失的依赖。

    Args:
        logger: 插件日志实例。

    Returns:
        bool: 依赖是否可用。
    """
    global DeepSeekClient, _deepseek_vision_loaded

    if _deepseek_vision_loaded:
        return True

    try:
        from deepseek_vision import DeepSeekClient as _Client
        DeepSeekClient = _Client
        _deepseek_vision_loaded = True
        return True
    except ImportError:
        pass

    try:
        import deepseek_pow  # noqa: F401
        import wasmtime  # noqa: F401
        from deepseek_vision import DeepSeekClient as _Client
        DeepSeekClient = _Client
        _deepseek_vision_loaded = True
        return True
    except ImportError:
        pass

    logger.info("检测到缺失依赖，正在从本地安装...")

    if not _ensure_pip(logger):
        logger.error("pip 不可用，无法安装依赖")
        return False

    wheels_dir = _resolve_wheels_dir()
    installed = False

    if wheels_dir.exists():
        installed = _install_from_wheels(wheels_dir, logger)

    if not installed:
        installed = _install_online(logger)

    if installed:
        _try_import(logger)

    return _deepseek_vision_loaded


def _ensure_pip(logger) -> bool:
    """确保 pip 可用。"""
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        pass

    try:
        subprocess.check_call(
            [sys.executable, "-m", "ensurepip", "--upgrade"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("已通过 ensurepip 恢复 pip")
        return True
    except Exception as e:
        logger.warning("ensurepip 失败: %s", e)
        return False


def _resolve_wheels_dir() -> Path:
    """根据平台选择合适的 wheels 目录。"""
    is_64 = struct.calcsize("P") * 8 == 64

    if sys.platform == "win32":
        return PLUGIN_DIR / "wheels"
    elif sys.platform == "linux" and is_64:
        linux_dir = PLUGIN_DIR / "wheels_linux"
        if linux_dir.exists():
            return linux_dir

    return PLUGIN_DIR / "wheels"


def _install_from_wheels(wheels_dir: Path, logger) -> bool:
    """从本地 wheels 安装依赖。"""
    try:
        subprocess.check_call(
            [
                sys.executable, "-m", "pip", "install",
                "--no-index", "--find-links", str(wheels_dir),
                "deepseek-pow", "wasmtime",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("本地 wheels 安装完成")
        return True
    except Exception as e:
        logger.warning("wheels 安装失败，尝试在线安装: %s", e)
        return False


def _install_online(logger) -> bool:
    """在线安装依赖。"""
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "deepseek-pow", "wasmtime"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("在线 pip 安装完成")
        return True
    except Exception as e:
        logger.error("pip 安装失败: %s", e)
        return False


def _try_import(logger) -> None:
    """尝试导入 deepseek_vision 模块。"""
    global DeepSeekClient, _deepseek_vision_loaded

    try:
        from deepseek_vision import DeepSeekClient as _Client
        DeepSeekClient = _Client
        _deepseek_vision_loaded = True
    except ImportError:
        logger.error("依赖安装后仍无法导入 deepseek_vision")
