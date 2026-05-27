#!/usr/bin/env python3
"""定时Cookie刷新 - 每6小时运行一次，自动续期"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from cookies.cookie_manager import CookieManager, run_all_refresh

async def main():
    await run_all_refresh()

if __name__ == '__main__':
    asyncio.run(main())
