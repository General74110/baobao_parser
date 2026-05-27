"""Instagram 解析器"""
import asyncio, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARSE_HUB = os.path.join(HERE, '..', '..', 'parse_hub_all')
sys.path.insert(0, os.path.join(PARSE_HUB, 'platforms'))

try:
    from instagram import MyInstaloaderContext, MyPost
    import instaloader
    HAS_INSTAGRAM = True
except ImportError:
    HAS_INSTAGRAM = False



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

class InstagramParser:
    """Instagram 解析器"""
    
    def __init__(self):
        self.name = 'instagram'
    
    async def parse(self, url: str):
        result = import sys; del sys.path[0]; _PR('instagram', url)
        
        try:
            if HAS_INSTAGRAM:
                await self._algorithm(url, result)
                result.method = 'algorithm'
            else:
                raise RuntimeError('Instagram模块不可用')
        except Exception as e:
            result.error = str(e)
            try:
                await self._browser(url, result)
                result.method = 'browser'
            except Exception as e2:
                result.error = f"{e}; browser: {e2}"
        
        return result
    
    async def _algorithm(self, url, result):
        """Instaloader API"""
        ctx = MyInstaloaderContext()
        L = instaloader.Instaloader(context=ctx)
        
        # 提取短代码
        m = re.search(r'/p/([^/?]+)', url) or re.search(r'/reel/([^/?]+)', url)
        if not m:
            raise ValueError("无法提取Instagram短代码")
        
        shortcode = m.group(1)
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        result.success = True
        result.title = (post.caption or '')[:200] if post.caption else ''
        
        if post.is_video:
            result.video_url = post.video_url
            result.cover_url = post.url
        elif post.typename == 'GraphSidecar':
            # 多图/视频
            for node in MyPost(post._full_metadata if hasattr(post, '_full_metadata') else post, L.context).get_sidecar_nodes():
                if node.is_video and node.video_url:
                    result.video_url = node.video_url
                else:
                    result.images.append(node.display_url)
            if result.images:
                result.cover_url = result.images[0]
        else:
            result.images.append(post.url)
            result.cover_url = post.url
    
    async def _browser(self, url, result):
        """浏览器兜底"""
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
            ctx = await browser.new_context(
                user_agent='Mozilla/5.0 Chrome/130',
                viewport={'width':390,'height':844}, is_mobile=True)
            page = await ctx.new_page()
            
            video_urls = []
            def on_resp(resp):
                ct = resp.headers.get('content-type','')
                if 'video' in ct or 'mp4' in ct.lower():
                    if 'cdninstagram' in resp.url or 'fbcdn' in resp.url:
                        video_urls.append(resp.url)
            page.on('response', on_resp)
            
            await page.goto(url, timeout=20000, wait_until='commit')
            await page.wait_for_timeout(6000)
            
            try:
                el = await page.query_selector('title')
                if el: result.title = await el.inner_text()
            except: pass
            
            if video_urls:
                result.video_url = video_urls[0]
                result.success = True
            
            if not result.video_url:
                # 找图片
                imgs = await page.query_selector_all('img[src*="cdninstagram"]')
                for img in imgs:
                    src = await img.get_attribute('src')
                    if src:
                        result.images.append(src)
                if result.images:
                    result.success = True
                    result.cover_url = result.images[0]
            
            await browser.close()
