# DeepSeek Vision Plugin for MaiBot

> 使用 DeepSeek 网页 API 识别图片内容，替代 MaiBot 默认 VLM 流程。

## 功能

- 自动劫持所有图片消息，调用 DeepSeek 网页 API 识别
- 替换 MaiBot 默认的 VLM 图片描述流程
- 支持密码和 Token 两种认证方式（Token 24h 有效，自动刷新）
- WebUI 配置页面（开关、认证、提示词）
- 手动调用 Tool `deepseek_vision`
- 依赖自动安装（内置 wheels，支持 Windows/Linux）

## 安装

1. 将整个 `deepseek-vision-plugin` 目录复制到 MaiBot 的 `plugins/` 目录
2. 复制 `config.toml.example` 为 `config.toml`，填写认证信息
3. 重启 MaiBot 或等待热加载

依赖会在首次加载时自动安装，无需手动操作。

## 配置

复制 `config.toml.example` 为 `config.toml`：

```toml
[plugin]
enabled = true

[auth]
# 方式一：Token 认证（推荐，可从浏览器 localStorage 获取）
auth_method = "token"
token = "你的token"

# 方式二：密码认证（首次使用自动获取 Token）
# auth_method = "password"
# mobile = "你的手机号"
# password = "你的密码"
# area_code = "+86"

[vision]
default_prompt = "请描述这张图片的内容"
```

也可通过 MaiBot WebUI 的插件设置页面配置。

## 工作原理

**MaiBot 原流程：**
```
图片 → VLM 生成描述 → [图片：描述] → LLM
```

**插件劫持后：**
```
图片 → DeepSeek 网页 API 识别 → [图片（by DeepSeek Vision）：描述] → LLM
```

### 技术细节

- **Hook 拦截**：监听 `chat.receive.before_process`，在消息处理前劫持图片组件
- **DeepSeek 网页 API**：逆向工程 DeepSeek 网页接口，包含 PoW (Proof of Work) 挑战
- **VLM 队列管理**：处理完图片后取消 MaiBot 的 VLM 后台任务，避免死循环
- **Token 自动刷新**：Token 过期时自动用密码重新登录

## 项目结构

```
deepseek-vision-plugin/
├── plugin.py              # 插件入口（Hook + Tool 声明）
├── auth.py                # 登录、token 管理与刷新
├── dependencies.py        # 依赖检查与自动安装
├── image_recognizer.py    # 图片识别逻辑
├── vlm_config.py          # VLM 配置段管理
├── config.py              # WebUI 配置模型
├── config.toml.example    # 配置模板
├── deepseek_vision/       # DeepSeek API 核心 SDK
│   ├── client.py          # HTTP 客户端
│   ├── models.py          # 数据模型
│   └── pow_solver.py      # PoW 挑战求解
├── wheels/                # 依赖包（按系统分类）
│   ├── windows/           # Windows 依赖
│   └── linux/             # Linux 依赖
└── requirements.txt       # Python 依赖
```

## 依赖

运行时依赖会自动安装：

- `requests>=2.28.0`
- `deepseek-pow>=0.0.1`
- `wasmtime>=1.0.0`

## 注意事项

- DeepSeek Token 有效期约 24 小时，首次使用会自动登录获取
- 图片识别使用 DeepSeek 的网页接口，非官方 API
- 需要 DeepSeek 账号

## License

MIT
