"""DeepSeek Vision 插件 VLM 配置管理。"""

from pathlib import Path


def ensure_vlm_config(logger) -> None:
    """检查并清理 MaiBot model_config.toml 中错误的 VLM 模型配置。

    如果 [model_task_config.vlm] 段的 model_list 包含
    "deepseek-vision-plugin"，将其清除以避免循环调用。

    Args:
        logger: 日志实例。
    """
    try:
        config_path = _find_model_config()
        if not config_path:
            logger.warning("model_config.toml 不存在，跳过 VLM 配置")
            return

        content = config_path.read_text(encoding="utf-8")
        marker = "[model_task_config.vlm]"
        idx = content.find(marker)
        if idx == -1:
            logger.warning("未找到 [model_task_config.vlm] 配置段")
            return

        vlm_section = content[idx:]
        lines = vlm_section.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("model_list"):
                if "deepseek-vision-plugin" in stripped:
                    lines[i] = "model_list = []"
                    new_section = "\n".join(lines)
                    content = content[:idx] + new_section
                    config_path.write_text(content, encoding="utf-8")
                    logger.info("已清理错误的 VLM 模型配置")
                else:
                    logger.info("VLM 配置正常，跳过")
                return

        logger.warning("VLM 配置段未找到 model_list")
    except Exception as e:
        logger.error("自动配置 VLM 失败: %s", e)


def _find_model_config() -> Path | None:
    """按优先级查找 model_config.toml。"""
    candidates = [
        Path(__file__).parent.parent / "config" / "model_config.toml",
        Path(__file__).parent.parent.parent / "config" / "model_config.toml",
        Path("/MaiMBot/config/model_config.toml"),
        Path("/vol2/1000/Docker/maibot/data/config/model_config.toml"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None
