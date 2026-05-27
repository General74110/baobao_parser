# 🐣 宝宝去水印 - 多平台解析器

自动解析抖音、小红书、Twitter、Instagram 等平台的去水印/高清内容。

## 当前状态

| 平台 | 状态 | 说明 |
|------|:----:|------|
| 抖音 | ✅ | 签名算法 + 浏览器回退，可下载无水印视频并发送到Telegram |
| 小红书 | ✅ | 浏览器模式，支持视频+图文解析 |
| Twitter | ⚠️ | 引擎已接入，公开推文可解析，受限内容需登录 |
| Instagram | ⚠️ | 引擎已接入，公共内容可解析，需完善 |

## 快速使用

```bash
pip install -r requirements.txt
playwright install chromium

# 解析抖音
python baobao.py "https://v.douyin.com/xxxxx/"

# 解析小红书
python baobao.py "http://xhslink.com/xxxxx"

# 发送到Telegram（需要环境变量）
export BOT_TOKEN="你的TG_BOT_TOKEN"
export CHAT_ID="你的TG_CHAT_ID"
python baobao.py "https://v.douyin.com/xxxxx/"
```

## 架构

```
用户发链接 → 平台检测 → 签名算法(快速) → 失败?
                                  ↓  是
                             浏览器兜底(慢但稳)
                                  ↓
                             下载 → 发送到Telegram
```

## 依赖

- httpx, playwright — 请求 + 浏览器自动化
- gmssl — SM3 国密哈希（抖音A-Bogus签名）
- instaloader — Instagram API
- loguru — Twitter 引擎日志
