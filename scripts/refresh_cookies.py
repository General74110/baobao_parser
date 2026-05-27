#!/usr/bin/env python3
"""定时Cookie刷新 - 加密存储 + 自动续期"""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../cookies'))

from cookies.secure_manager import run_all_refresh

if __name__ == '__main__':
    asyncio.run(run_all_refresh())
