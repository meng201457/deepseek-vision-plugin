"""DeepSeek Vision 插件配置 - WebUI 设置页面"""

from typing import ClassVar, Literal

from pydantic import Field
from maibot_sdk.config import PluginConfigBase


def _schema_i18n(*, label_en: str = "", hint_en: str = "", placeholder_en: str = "") -> dict:
    return {
        "en_US": {"label": label_en, "hint": hint_en, "placeholder": placeholder_en},
    }


class DeepSeekPluginOptions(PluginConfigBase):
    """插件基础设置。"""

    __ui_label__: ClassVar[str] = "插件设置"
    __ui_order__: ClassVar[int] = 0

    enabled: bool = Field(
        default=True,
        description="是否启用 DeepSeek Vision 插件。",
        json_schema_extra={
            "hint": "关闭后插件不会劫持图片识别流程，MaiBot 将使用默认 VLM 处理图片。",
            "label": "启用插件",
            "order": 0,
        },
    )
    config_version: str = Field(
        default="1.1.0",
        description="当前配置结构版本。",
        json_schema_extra={
            "disabled": True,
            "hidden": True,
            "label": "配置版本",
            "order": 99,
        },
    )


class DeepSeekAuthConfig(PluginConfigBase):
    """DeepSeek 认证配置。"""

    __ui_label__: ClassVar[str] = "DeepSeek 认证"
    __ui_order__: ClassVar[int] = 1

    auth_method: Literal["password", "token"] = Field(
        default="token",
        description="认证方式：password 使用手机号密码登录，token 使用已有令牌。",
        json_schema_extra={
            "hint": "token 方式使用已保存的令牌；若令牌过期会自动用密码重新登录并更新令牌。",
            "label": "认证方式",
            "order": 0,
        },
    )
    mobile: str = Field(
        default="",
        description="DeepSeek 账号手机号。",
        json_schema_extra={
            "hint": "auth_method 为 password 时必填。",
            "label": "手机号",
            "order": 1,
            "placeholder": "例如：13800138000",
        },
    )
    area_code: str = Field(
        default="+86",
        description="手机号区号。",
        json_schema_extra={
            "hint": "中国大陆默认 +86，海外手机号请修改。",
            "label": "区号",
            "order": 2,
            "placeholder": "+86",
        },
    )
    password: str = Field(
        default="",
        description="DeepSeek 账号密码。",
        json_schema_extra={
            "hint": "auth_method 为 password 时必填。密码不会上传到任何第三方服务器。",
            "input_type": "password",
            "label": "密码",
            "order": 3,
            "placeholder": "请输入密码",
        },
    )
    token: str = Field(
        default="",
        description="DeepSeek 用户令牌（userToken）。",
        json_schema_extra={
            "hint": "auth_method 为 token 时必填。令牌有效期约24小时，过期需重新获取。",
            "input_type": "password",
            "label": "用户令牌",
            "order": 4,
            "placeholder": "可从浏览器 localStorage 获取",
        },
    )


class DeepSeekVisionConfig(PluginConfigBase):
    """图片识别设置。"""

    __ui_label__: ClassVar[str] = "识别设置"
    __ui_order__: ClassVar[int] = 2

    default_prompt: str = Field(
        default="请描述这张图片的内容",
        description="发送给 DeepSeek 的默认提示词。",
        json_schema_extra={
            "hint": "每次识别图片时附加的提示词，可自定义为更具体的描述要求。",
            "label": "默认提示词",
            "order": 0,
            "placeholder": "请描述这张图片的内容",
        },
    )


class DeepSeekVisionPluginSettings(PluginConfigBase):
    """DeepSeek Vision 插件完整配置。"""

    plugin: DeepSeekPluginOptions = Field(default_factory=DeepSeekPluginOptions)
    auth: DeepSeekAuthConfig = Field(default_factory=DeepSeekAuthConfig)
    vision: DeepSeekVisionConfig = Field(default_factory=DeepSeekVisionConfig)
