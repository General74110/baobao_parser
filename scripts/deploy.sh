#!/bin/bash
# 部署脚本
pip install -r requirements.txt
playwright install chromium
echo "部署完成!"
