#!/usr/bin/env python3
"""Twitter/X 解析器"""
import asyncio, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
PARSE_HUB = os.path.join(HERE, '..', '..', 'parse_hub_all')
sys.path.insert(0, os.path.join(PARSE_HUB, 'platforms'))

try:
    from twitter_engine import Twitter
    HAS_TWITTER = True
except ImportError:
    HAS_TWITTER = False


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


class TwitterParser:
    def __init__(self):
        self.name = 'twitter'
    
    async def parse(self, url: str):
        result = ParseResult('twitter', url)
        try:
            if HAS_TWITTER:
                await self._algorithm(url, result)
                result.method = 'algorithm'
            else:
                raise RuntimeError('Twitter模块不可用')
        except Exception as e:
            result.error = str(e)
            try:
                await self._browser(url, result)
                result.method = 'browser'
            except Exception as e2:
                result.error = f"{e}; browser: {e2}"
        return result
    
    async def _algorithm(self, url, result):
        tw = Twitter()
        # 从加密存储加载Cookie
        try:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cookies'))
            from secure_manager import SecureCookieManager
            cm = SecureCookieManager()
            cookies = cm.get('twitter')
            if cookies:
                tw.cookie = cookies
        except: pass
        tweet = await tw.fetch_tweet(url)
        result.success = True
        result.title = (tweet.full_text or '')[:200]
        for m in tweet.media:
            if hasattr(m, 'url') and m.url:
                result.video_url = m.url
            elif hasattr(m, 'url') and not result.video_url:
                result.images.append(m.url)
    
    async def _browser(self, url, result):
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            ctx = await browser.new_context(
                user_agent='Mozilla/5.0 Chrome/130',
                viewport={'width':1280,'height':720})
            page = await ctx.new_page()
            video_srcs = []
            def on_resp(resp):
                ct = resp.headers.get('content-type','')
                if 'video' in ct and 'twimg' in resp.url.lower():
                    video_srcs.append(resp.url)
            page.on('response', on_resp)
            await page.goto(url, timeout=20000, wait_until='commit')
            await page.wait_for_timeout(5000)
            try:
                el = await page.query_selector('title')
                if el: result.title = await el.inner_text()
            except: pass
            videos = await page.query_selector_all('video source')
            for v in videos:
                src = await v.get_attribute('src')
                if src: result.video_url = src; break
            if not result.video_url and video_srcs:
                result.video_url = video_srcs[0]
            result.success = bool(result.video_url)
            await browser.close()
        return result
