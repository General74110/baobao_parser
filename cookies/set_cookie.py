#!/usr/bin/env python3
"""
Cookie 设置工具 - 一个命令设置Twitter/Instagram Cookie
"""
import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cookie_manager import CookieManager

def main():
    cm = CookieManager()
    
    if len(sys.argv) < 3:
        print("🐣 Cookie 管理器")
        print()
        print("用法:")
        print("  python set_cookie.py twitter auth_token=xxx ct0=xxx")
        print("  python set_cookie.py instagram sessionid=xxx")
        print("  python set_cookie.py status          # 查看状态")
        print("  python set_cookie.py refresh         # 手动刷新")
        print()
        print("当前状态:")
        for k, v in cm.status().items():
            print(f"  {k}: {v}")
        return
    
    cmd = sys.argv[1]
    
    if cmd == 'status':
        print("📋 Cookie状态:")
        for k, v in cm.status().items():
            print(f"  {k}: {v}")
    
    elif cmd == 'refresh':
        print("🔄 手动刷新所有Cookie...")
        asyncio.run(refresh_all(cm))
    
    else:
        # 设置Cookie: twitter auth_token=xxx ct0=xxx
        platform = cmd
        cookie_dict = {}
        for arg in sys.argv[2:]:
            if '=' in arg:
                k, v = arg.split('=', 1)
                cookie_dict[k] = v
        
        if cookie_dict:
            cm.set(platform, cookie_dict)
            print(f"✅ {platform} Cookie已设置!")
            print(f"   自动续期已启用，每天刷新保证不过期")


async def refresh_all(cm):
    from cookie_manager import auto_refresh_twitter, auto_refresh_instagram
    
    if cm.is_valid('twitter') or cm.get('twitter'):
        print("  Twitter: ", end='')
        ok = await auto_refresh_twitter(cm)
        print(f"  {'✅' if ok else '❌'}")
    
    if cm.is_valid('instagram') or cm.get('instagram'):
        print("  Instagram: ", end='')
        ok = await auto_refresh_instagram(cm)
        print(f"  {'✅' if ok else '❌'}")


if __name__ == '__main__':
    main()
