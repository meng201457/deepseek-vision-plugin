# DeepSeek Vision Plugin for MaiBot

> **⚠️ 本项目完全由 AI 编写（OpenCode + MiMo），人类仅提供需求和测试。**

## 功能

- 自动劫持所有图片消息，调用 DeepSeek 网页 API 识别
- 替换 MaiBot 默认的 VLM 图片描述流程
- 支持密码和 Token 两种认证方式（Token 24h 有效，自动刷新）
- WebUI 配置页面（开关、认证、提示词）
- 手动调用 Tool `deepseek_vision`

## 安装

1. 将 `deepseek-vision` 目录复制到 MaiBot 的 `plugins/` 目录
2. 安装依赖：
   ```bash
   pip install deepseek-pow wasmtime
   ```
3. 编辑 `config.toml` 配置认证信息
4. 重启 MaiBot 或等待热加载

## 配置

编辑 `config.toml`：

```toml
[plugin]
enabled = true

[auth]
# 方式一：密码认证（首次使用自动获取 Token）
auth_method = "mobile"
mobile = "你的手机号"
password = "你的密码"
area_code = "+86"

# 方式二：Token 认证（24h 有效）
# auth_method = "token"
# token = "你的token"

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

## 依赖

- `requests>=2.28.0`
- `deepseek-pow>=0.0.1`
- `wasmtime`（deepseek-pow 的依赖）

## 注意事项

- DeepSeek Token 有效期约 24 小时，首次使用会自动登录获取
- 图片识别使用 DeepSeek 的网页接口，非官方 API
- 需要 DeepSeek 账号

## License

MIT
