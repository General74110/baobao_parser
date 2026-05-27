#!/usr/bin/env python3
"""小红书解析器"""
import asyncio, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARSE_HUB = os.path.join(HERE, '..', '..', 'parse_hub_all')
sys.path.insert(0, os.path.join(PARSE_HUB, 'platforms'))

try:
    from xhs import XHSAPI
    HAS_XHS = True
except ImportError:
    HAS_XHS = False


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


class XiaohongshuParser:
    def __init__(self):
        self.name = 'xiaohongshu'
    
    async def parse(self, url: str):
        result = ParseResult('xiaohongshu', url)
        try:
            if HAS_XHS:
                await self._algorithm(url, result)
                result.method = 'algorithm'
            else:
                raise RuntimeError('小红书模块不可用')
        except Exception as e:
            result.error = str(e)
            try:
                await self._browser(url, result)
                result.method = 'browser'
            except Exception as e2:
                result.error = f"{e}; browser: {e2}"
        return result
    
    async def _algorithm(self, url, result):
        xhs = XHSAPI(cookie={})
        post = await xhs.extract(url)
        result.success = True
        result.title = post.title or ''
        for media in (post.media or []):
            if media.type in ('video', 'livephoto'):
                result.video_url = media.url  # 最高画质
                if media.thumb_url: result.cover_url = media.thumb_url
            else:
                result.images.append(media.url)
        if not result.images and post.media and post.media[0].type == 'image':
            result.images = [m.url for m in post.media]
    
    async def _browser(self, url, result):
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            ctx = await browser.new_context(
                user_agent='Mozilla/5.0 (iPhone) AppleWebKit/605.1.15',
                viewport={'width':390,'height':844}, is_mobile=True, locale='zh-CN')
            page = await ctx.new_page()
            video_urls = []
            def on_resp(resp):
                ct = resp.headers.get('content-type','')
                if ('video' in ct or 'mp4' in ct) and 'xhscdn' in resp.url.lower():
                    video_urls.append(resp.url)
            page.on('response', on_resp)
            await page.goto(url, timeout=20000, wait_until='commit')
            await page.wait_for_timeout(6000)
            try:
                el = await page.query_selector('title')
                if el: result.title = await el.inner_text()
            except: pass
            if video_urls: result.video_url = video_urls[0]
            imgs = await page.query_selector_all('img[src*="xhscdn"]')
            for img in imgs:
                src = await img.get_attribute('src')
                if src and 'avatar' not in src.lower():
                    result.images.append(src)
            result.success = bool(result.video_url or result.images)
            await browser.close()
        return result
