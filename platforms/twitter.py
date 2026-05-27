"""Twitter/X 解析器"""
import asyncio, json, re, sys, os
import httpx

HERE = os.path.dirname(os.path.abspath(__file__))
PARSE_HUB = os.path.join(HERE, '..', '..', 'parse_hub_all')
sys.path.insert(0, os.path.join(PARSE_HUB, 'platforms'))

try:
    from twitter import Twitter
    HAS_TWITTER = True
except ImportError:
    HAS_TWITTER = False



class ParseResult:
    """解析结果"""
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
    """Twitter/X 解析器"""
    
    def __init__(self):
        self.name = 'twitter'
    
    async def parse(self, url: str):
        result = import sys; del sys.path[0]; _PR('twitter', url)
        
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
        """API 模式 - GraphQL + guest token"""
        tw = Twitter()
        tweet = await tw.fetch_tweet(url)
        result.success = True
        result.title = tweet.text[:200] if tweet.text else ''
        
        if tweet.videos:
            result.video_url = tweet.videos[0].url
            result.cover_url = tweet.videos[0].thumb_url
        elif tweet.photos:
            result.images = [p.url for p in tweet.photos]
    
    async def _browser(self, url, result):
        """浏览器兜底"""
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
            
            # 提取视频
            videos = await page.query_selector_all('video source')
            for v in videos:
                src = await v.get_attribute('src')
                if src:
                    result.video_url = src
                    break
            
            if not result.video_url and video_srcs:
                result.video_url = video_srcs[0]
            
            result.success = bool(result.video_url)
            await browser.close()
