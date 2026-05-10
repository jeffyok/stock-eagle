@echo off
chcp 65001 >nul
title StockEagle 后端服务
cd /d E:\pycharm_workspace\stock-eagle
echo 启动后端 FastAPI (端口 8000)...
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
