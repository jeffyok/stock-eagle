@echo off
chcp 65001 >nul
title StockEagle 前端服务
cd /d E:\pycharm_workspace\stock-eagle
echo 启动前端 Streamlit (端口 8501)...
python -m streamlit run web/web_main.py --server.port 8501
