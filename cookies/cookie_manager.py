"""
Cookie管理 - 自动刷新+不过期
"""
import json, os, time, base64
from pathlib import Path
from datetime import datetime, timezone

COOKIE_DIR = Path(__file__).parent

class CookieManager:
    """Cookie 管理器 - 存储+验证+自动刷新"""
    
    def __init__(self):
        self.cookies_file = COOKIE_DIR / 'cookies.json'
        self.cookies = self._load()
    
    def _load(self) -> dict:
        if self.cookies_file.exists():
            try:
                return json.loads(self.cookies_file.read_text())
            except: pass
        return {'twitter': {}, 'instagram': {}, 'douyin': {}, 'xhs': {}}
    
    def _save(self):
        self.cookies_file.write_text(json.dumps(self.cookies, indent=2, ensure_ascii=False))
    
    def set(self, platform: str, cookie_dict: dict):
        """设置Cookie"""
        entry = {
            'cookies': cookie_dict,
            'set_at': time.time(),
            'last_refresh': time.time(),
            'expires_at': time.time() + 86400 * 90,  # 默认90天
        }
        self.cookies[platform] = entry
        self._save()
        print(f"✅ {platform} Cookie已保存 ({len(cookie_dict)}个字段)")
    
    def get(self, platform: str) -> dict:
        """获取Cookie"""
        entry = self.cookies.get(platform, {})
        return entry.get('cookies', {})
    
    def is_valid(self, platform: str) -> bool:
        """检查Cookie是否有效"""
        entry = self.cookies.get(platform, {})
        if not entry or not entry.get('cookies'):
            return False
        # 检查是否过期
        expires = entry.get('expires_at', 0)
        if time.time() > expires:
            return False
        return True
    
    def refresh(self, platform: str, new_cookies: dict):
        """刷新Cookie（续命）"""
        entry = self.cookies.get(platform, {})
        if entry:
            # 合并新旧cookie
            entry['cookies'].update(new_cookies)
            entry['last_refresh'] = time.time()
            entry['expires_at'] = time.time() + 86400 * 90
            self._save()
            return True
        return False
    
    def remove(self, platform: str):
        """删除Cookie"""
        if platform in self.cookies:
            self.cookies[platform] = {}
            self._save()
    
    def status(self) -> dict:
        """返回所有平台Cookie状态"""
        result = {}
        for platform, entry in self.cookies.items():
            if not entry or not entry.get('cookies'):
                result[platform] = '❌ 未配置'
                continue
            set_at = entry.get('set_at', 0)
            last = entry.get('last_refresh', 0)
            expires = entry.get('expires_at', 0)
            now = time.time()
            
            if now > expires:
                result[platform] = f'❌ 已过期 ({len(entry["cookies"])}个字段)'
            else:
                days_left = int((expires - now) / 86400)
                result[platform] = f'✅ 有效 ({len(entry["cookies"])}个字段, 剩余{days_left}天)'
        return result


# ─── 自动续期 ──────────────────────────────────────────

async def auto_refresh_twitter(cm: CookieManager):
    """浏览器访问Twitter保持Cookie活跃"""
    from playwright.async_api import async_playwright
    
    cookies = cm.get('twitter')
    if not cookies:
        return False
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            ctx = await browser.new_context(
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) AppleWebKit/605.1.15',
                viewport={'width':390,'height':844}, is_mobile=True)
            
            # 注入Cookie
            for name, value in cookies.items():
                await ctx.add_cookies([{
                    'name': name, 'value': value,
                    'domain': '.twitter.com', 'path': '/'
                }])
            
            page = await ctx.new_page()
            await page.goto('https://twitter.com/home', timeout=15000, wait_until='commit')
            await page.wait_for_timeout(3000)
            
            # 提取最新的Cookie
            new_cookies = await ctx.cookies()
            cookie_dict = {c['name']: c['value'] for c in new_cookies}
            
            # 更新
            if 'auth_token' in cookie_dict:
                cm.refresh('twitter', cookie_dict)
                print(f"  ✅ Twitter Cookie 已续期 ({len(cookie_dict)}个字段)")
                await browser.close()
                return True
            
            await browser.close()
            return False
    except Exception as e:
        print(f"  ❌ Twitter 续期失败: {e}")
        return False


async def auto_refresh_instagram(cm: CookieManager):
    """浏览器访问Instagram保持Cookie活跃"""
    from playwright.async_api import async_playwright
    
    cookies = cm.get('instagram')
    if not cookies:
        return False
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            ctx = await browser.new_context(
                user_agent='Mozilla/5.0 (iPhone) AppleWebKit/605.1.15',
                viewport={'width':390,'height':844}, is_mobile=True)
            
            for name, value in cookies.items():
                await ctx.add_cookies([{
                    'name': name, 'value': value,
                    'domain': '.instagram.com', 'path': '/'
                }])
            
            page = await ctx.new_page()
            await page.goto('https://www.instagram.com/', timeout=15000, wait_until='commit')
            await page.wait_for_timeout(3000)
            
            new_cookies = await ctx.cookies()
            cookie_dict = {c['name']: c['value'] for c in new_cookies}
            
            if 'sessionid' in cookie_dict:
                cm.refresh('instagram', cookie_dict)
                print(f"  ✅ Instagram Cookie 已续期 ({len(cookie_dict)}个字段)")
                await browser.close()
                return True
            
            await browser.close()
            return False
    except Exception as e:
        print(f"  ❌ Instagram 续期失败: {e}")
        return False


async def run_all_refresh():
    """执行所有平台Cookie续期"""
    cm = CookieManager()
    print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] Cookie续期检查...")
    
    # Twitter
    if cm.is_valid('twitter') or cm.get('twitter'):
        print("  Twitter: ", end='')
        await auto_refresh_twitter(cm)
    else:
        print("  Twitter: 跳过（未配置）")
    
    # Instagram
    if cm.is_valid('instagram') or cm.get('instagram'):
        print("  Instagram: ", end='')
        await auto_refresh_instagram(cm)
    else:
        print("  Instagram: 跳过（未配置）")
    
    # 输出状态
    print(f"\n📋 Cookie状态:")
    for k, v in cm.status().items():
        print(f"  {k}: {v}")
