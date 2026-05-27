#!/usr/bin/env python3
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""
🐣 宝宝去水印 - 多平台解析引擎
自动检测平台，调用对应解析器，下载并发送到Telegram
"""
import asyncio, json, os, re, sys, time
from pathlib import Path
from urllib.parse import urlparse
import importlib.util

HERE = Path(__file__).parent

# ─── 平台路由 ────────────────────────────────────────────

ROUTES = {
    'douyin': {'patterns': [r'douyin\.com', r'iesdouyin', r'v\.douyin'], 'file': 'douyin'},
    'xiaohongshu': {'patterns': [r'xiaohongshu\.com', r'xhslink\.com'], 'file': 'xiaohongshu'},
    'twitter': {'patterns': [r'twitter\.com', r'x\.com/'], 'file': 'twitter'},
    'instagram': {'patterns': [r'instagram\.com'], 'file': 'instagram'},
    'tiktok': {'patterns': [r'tiktok\.com'], 'file': 'tiktok'},
    'bilibili': {'patterns': [r'bilibili\.com', r'b23\.tv'], 'file': 'bilibili'},
    'kuaishou': {'patterns': [r'kuaishou\.com'], 'file': 'kuaishou'},
    'weibo': {'patterns': [r'weibo\.com', r'weibo\.cn'], 'file': 'weibo'},
}


def detect_platform(text: str) -> tuple[str, str] | None:
    """检测平台并提取URL"""
    text_clean = re.sub(r'[^\x20-\x7E\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', '', text)
    
    for platform, config in ROUTES.items():
        for pattern in config['patterns']:
            m = re.search(pattern, text_clean, re.I)
            if m:
                # 提取完整URL
                start = max(0, m.start() - 50)
                remaining = text_clean[start:]
                url_m = re.search(r'https?://[^\s<>"\']+', remaining)
                if url_m:
                    return platform, url_m.group(0).rstrip('/?&')
    return None


def import_platform(platform: str):
    """动态导入平台解析器"""
    file = ROUTES[platform]['file']
    path = HERE / 'platforms' / f'{file}.py'
    if not path.exists():
        raise ImportError(f"平台 {platform} 解析器未实现: {path}")
    
    spec = importlib.util.spec_from_file_location(platform, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ─── 结果模型 ────────────────────────────────────────────

class ParseResult:
    def __init__(self, platform: str, url: str):
        self.platform = platform
        self.source_url = url
        self.success = False
        self.title = ''
        self.video_url = None
        self.images = []
        self.cover_url = None
        self.error = ''
        self.method = ''


# ─── 下载+发送 ──────────────────────────────────────────

class TelegramSender:
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or os.environ.get('BOT_TOKEN', '')
        self.chat_id = chat_id or os.environ.get('CHAT_ID', '')
    
    async def download(self, url: str, headers: dict = None) -> str | None:
        import httpx
        ext = '.mp4' if 'video' in url.lower() or 'mime_type=video' in url else '.jpg'
        path = f'/tmp/baobao_{int(time.time())}{ext}'
        
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            r = await client.get(url, headers=headers or {})
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    f.write(r.content)
                return path
        return None
    
    async def send(self, file_path: str, caption: str = '') -> bool:
        if not self.bot_token:
            return False
        
        import httpx
        is_video = file_path.endswith(('.mp4', '.mov'))
        endpoint = 'sendVideo' if is_video else 'sendPhoto'
        url = f'https://api.telegram.org/bot{self.bot_token}/{endpoint}'
        
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url,
                data={'chat_id': self.chat_id, 'caption': caption[:200]},
                files={'video' if is_video else 'photo': open(file_path, 'rb')})
            return r.json().get('ok', False)


# ─── 主入口 ─────────────────────────────────────────────

async def main():
    if len(sys.argv) < 2:
        print("🐣 宝宝去水印 v1.0")
        print("用法: python baobao.py <链接或文本>")
        print("支持:", ', '.join(ROUTES.keys()))
        sys.exit(1)
    
    text = ' '.join(sys.argv[1:])
    
    detected = detect_platform(text)
    if not detected:
        print("❌ 未识别到支持的平台")
        sys.exit(1)
    
    platform, url = detected
    print(f"🔍 {platform.upper()} | {url}")
    
    try:
        mod = import_platform(platform)
        parser_class = getattr(mod, f'{platform.capitalize()}Parser')
        parser = parser_class()
        result = await parser.parse(url)
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    
    if not result.success:
        print(f"❌ {result.error}")
        sys.exit(1)
    
    print(f"📝 {result.title or '(无标题)'}")
    if result.video_url:
        print(f"🎬 视频: ✅ 最高画质")
    if result.video_url: print(f"🎬 视频: {result.video_url[:80]}...")
    if result.images:    print(f"📸 图片 {len(result.images)}张")
    if result.cover_url: print(f"🖼️ 封面: 有")
    print(f"⚡ 模式: {result.method}")
    
    # 下载+发送
    if result.video_url and 'BOT_TOKEN' in os.environ:
        sender = TelegramSender()
        headers = {'Referer': f'https://www.{platform}.com/'}
        
        print(f"\n📥 下载...")
        path = await sender.download(result.video_url, headers)
        if path:
            print(f"📤 发送到Telegram...")
            if await sender.send(path, result.title[:200]):
                print(f"✅ 搞定!")
            else:
                print(f"❌ 发送失败")
            os.remove(path)


if __name__ == '__main__':
    asyncio.run(main())

# ─── Cookie 管理 ──────────────────────────────────────

def use_cookies(platform: str) -> dict:
    """从CookieManager加载已保存的Cookie"""
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies'))
        from cookie_manager import CookieManager
        cm = CookieManager()
        return cm.get(platform)
    except:
        return {}


async def refresh_cookies_async():
    """异步刷新Cookie"""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies'))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies'))
    from cookie_manager import run_all_refresh
    await run_all_refresh()

