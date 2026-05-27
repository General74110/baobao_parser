#!/usr/bin/env python3
"""
Cookie 设置工具 - 加密存储，防止泄露
"""
import asyncio, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from secure_manager import SecureCookieManager, run_all_refresh

def main():
    cm = SecureCookieManager()
    
    if len(sys.argv) < 3:
        print("🔒 Cookie 管理器（加密存储）")
        print()
        print("用法:")
        print("  python set_cookie.py twitter auth_token=*** ct0=xxx")
        print("  python set_cookie.py instagram sessionid=xxx")
        print("  python set_cookie.py status           # 查看状态")
        print("  python set_cookie.py refresh          # 手动刷新")
        print()
        print("当前状态:")
        st = cm.status()
        if st:
            for k, v in st.items():
                print(f"  {k}: {v}")
        else:
            print("  (无已保存的Cookie)")
        return
    
    cmd = sys.argv[1]
    
    if cmd == 'status':
        st = cm.status()
        print("🔒 Cookie状态:")
        if st:
            for k, v in st.items():
                print(f"  {k}: {v}")
        else:
            print("  (无已保存的Cookie)")
    
    elif cmd == 'refresh':
        print("🔄 手动刷新所有Cookie...")
        asyncio.run(run_all_refresh())
    
    else:
        platform = cmd
        cookie_dict = {}
        for arg in sys.argv[2:]:
            if '=' in arg:
                k, v = arg.split('=', 1)
                cookie_dict[k] = v
        
        if cookie_dict:
            cm.set(platform, cookie_dict)
            print(f"✅ {platform} Cookie已加密保存!")
            print(f"   自动续期已启用，每6小时刷新")
            print(f"   密钥已隔离，不会提交到Git")


if __name__ == '__main__':
    main()
