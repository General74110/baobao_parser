# 宝宝去水印 - 多平台解析器 🐣

自动解析抖音、小红书、推特、Instagram 等平台的无水印/高清内容。

## 支持平台

| 平台 | 视频 | 图文 | 去水印 | 模式 |
|------|:----:|:----:|:------:|:----:|
| 抖音 | ✅ | ✅ | ✅ | 签名算法 + 浏览器回退 |
| 小红书 | ✅ | ✅ | ✅ | 签名算法 + 浏览器回退 |
| Twitter/X | ✅ | ✅ | ✅ | API |
| Instagram | ✅ | ✅ | ✅ | API |

## 快速使用

```bash
pip install -r requirements.txt
python baobao.py "https://v.douyin.com/xxx/"
python baobao.py "https://www.xiaohongshu.com/explore/xxx"
```

## 项目结构

```
baobao_parser/
├── baobao.py          # 主入口 - 自动检测平台并解析
├── platforms/
│   ├── douyin.py      # 抖音解析器
│   ├── xiaohongshu.py # 小红书解析器
│   ├── twitter.py     # Twitter 解析器
│   └── instagram.py   # Instagram 解析器
├── requirements.txt
├── README.md
└── scripts/
    └── deploy.sh      # 部署脚本
```

## 架构

```
用户发链接 → 平台检测 → 签名算法(快速) → 失败?
                                  ↓  是
                             浏览器兜底(慢但稳)
                                  ↓
                             下载 → 发送到Telegram
```
