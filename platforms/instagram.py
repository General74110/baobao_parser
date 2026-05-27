"""Instagram 解析器"""
import asyncio, os, re, sys, instaloader
from . import ParseResult


class InstagramParser:
    def __init__(self):
        self.name = 'instagram'
    
    def _load_cookies(self) -> dict:
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cookies'))
            from secure_manager import SecureCookieManager
            return SecureCookieManager().get('instagram')
        except:
            return {}
    
    async def parse(self, url: str):
        result = ParseResult('instagram', url)
        try:
            cookies = self._load_cookies()
            L = instaloader.Instaloader()
            if cookies: L.context._session.cookies.update(cookies)
            
            m = re.search(r'/p/([^/?]+)', url) or re.search(r'/reel/([^/?]+)', url)
            if not m: raise ValueError("无法提取短代码")
            
            post = instaloader.Post.from_shortcode(L.context, m.group(1))
            result.success = True
            result.title = (post.caption or '')[:200] if post.caption else ''
            
            if post.is_video:
                result.video_url = post.video_url  # 最高画质
                result.cover_url = post.url
            elif post.typename == 'GraphSidecar':
                for node in instaloader.Post(post, L.context).get_sidecar_nodes():
                    if node.is_video and node.video_url:
                        result.video_url = node.video_url  # 最高画质
                    else:
                        result.images.append(node.display_url)
                if result.images: result.cover_url = result.images[0]
            else:
                result.images.append(post.url)
                result.cover_url = post.url
        except Exception as e:
            result.error = str(e)
        return result
