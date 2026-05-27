#!/usr/bin/env python3
"""抖音解析器 - 签名算法 + 浏览器兜底"""
import asyncio, json, os, re, sys, time
from urllib.parse import urlencode, quote

HERE = os.path.dirname(os.path.abspath(__file__))
PARSE_HUB = os.path.join(HERE, '..', '..', 'parse_hub_all')
sys.path.insert(0, PARSE_HUB)
sys.path.insert(0, os.path.join(PARSE_HUB, 'platforms'))

try:
    from douyin import DouyinWebCrawler
    HAS_ALGORITHM = True
except ImportError:
    HAS_ALGORITHM = False


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


class DouyinParser:
    """抖音解析器"""
    
    def __init__(self):
        self.name = 'douyin'
    
    async def parse(self, url: str):
        result = ParseResult('douyin', url)
        
        try:
            if HAS_ALGORITHM:
                await self._algorithm(url, result)
                result.method = 'algorithm'
            else:
                raise RuntimeError('算法模块不可用')
        except Exception as e:
            result.error = str(e)
            try:
                await self._browser(url, result)
                result.method = 'browser'
            except Exception as e2:
                result.error = f"{e}; browser: {e2}"
        
        return result
    
    async def _algorithm(self, url, result):
        """签名算法模式 - 浏览器拿Cookie + A-Bogus签名调API"""
        from playwright.async_api import async_playwright
        
        # 1. 浏览器拿Cookie
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            ctx = await browser.new_context(
                user_agent='Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/130.0.6728.40',
                viewport={'width':390,'height':844}, is_mobile=True, locale='zh-CN')
            page = await ctx.new_page()
            await page.goto(url, timeout=15000, wait_until='commit')
            await page.wait_for_timeout(3000)
            cookies = await ctx.cookies()
            await browser.close()
        
        cd = {c['name']: c['value'] for c in cookies}
        
        # 2. A-Bogus签名调API
        crawler = DouyinWebCrawler(cookie=cd, proxy=None)
        aweme_id = await crawler.get_aweme_id(url)
        data = await crawler.fetch_one_video(aweme_id)
        detail = data.get('aweme_detail', data)
        
        result.title = detail.get('desc', '')
        result.success = True
        
        video = detail.get('video', {})
        brs = video.get('bit_rate', [])
        if brs:
            best = max(brs, key=lambda x: x.get('play_addr',{}).get('width',0)*x.get('play_addr',{}).get('height',0))
            urls = best.get('play_addr',{}).get('url_list',[])
            if urls:
                result.video_url = urls[0].replace('playwm','play')
        
        cover = video.get('cover',{}).get('url_list',[])
        if cover: result.cover_url = cover[-1]
        
        images = detail.get('images',[]) or [
            i.get('display_image',{}) for i in detail.get('image_post_info',{}).get('images',[])
        ]
        if images: result.images = [i['url_list'][-1] for i in images if i.get('url_list')]
        return result
    
    async def _browser(self, url, result):
        """浏览器兜底模式"""
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            ctx = await browser.new_context(
                user_agent='Mozilla/5.0 Chrome/130',
                viewport={'width':390,'height':844}, is_mobile=True)
            page = await ctx.new_page()
            
            video_srcs = []
            def on_resp(resp):
                ct = resp.headers.get('content-type','')
                if 'video/mp4' in ct and 'douyin' in resp.url.lower():
                    video_srcs.append(resp.url)
            page.on('response', on_resp)
            
            await page.goto(url, timeout=20000, wait_until='commit')
            await page.wait_for_timeout(8000)
            
            try:
                el = await page.query_selector('title')
                if el: result.title = await el.inner_text()
            except: pass
            
            if video_srcs:
                result.video_url = video_srcs[0]
                result.success = True
            
            await browser.close()
        return result
