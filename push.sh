#!/bin/bash
# GitHub 推送脚本

cd /home/admin/openclaw/workspace/invest-autoresearch

echo "📦 准备推送至 GitHub..."
echo "仓库：https://github.com/xiaofeng0920-Happy/invest-autoresearch"
echo ""

# 检查远程仓库
git remote -v

echo ""
echo "🚀 执行推送..."
echo "请输入 GitHub 用户名和 Token/密码"
git push -u origin main

echo ""
echo "✅ 推送完成！"
