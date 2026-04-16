#!/bin/bash
# 快速发帖模板脚本
# 使用方法:
#   ./scripts/quick_post.sh morning "你的内容"
#   ./scripts/quick_post.sh noon "你的内容"
#   ./scripts/quick_post.sh evening "你的内容"

set -e

PROJECT_DIR="/Users/jackwl/Code/gitcode/gitxPost"
cd "$PROJECT_DIR"
source .venv/bin/activate

TYPE=$1
CONTENT=$2

if [ -z "$TYPE" ] || [ -z "$CONTENT" ]; then
    echo "使用方法: $0 <morning|noon|evening> <内容>"
    echo ""
    echo "示例:"
    echo "  $0 morning \"今天看到一个有趣的观点...\""
    echo "  $0 noon \"问个问题：大家用什么 AI 工具？\""
    echo "  $0 evening \"今天完成了 gitxPost 的新功能\""
    exit 1
fi

case $TYPE in
    morning)
        echo "📅 发布早间 Post (观点型)..."
        xpost post "$CONTENT" --publish
        ;;
    noon)
        echo "💬 发布午间 Post (互动型)..."
        xpost post "$CONTENT" --publish
        ;;
    evening)
        echo "🌙 发布晚间 Post (总结型)..."
        xpost post "$CONTENT" --publish
        ;;
    *)
        echo "❌ 错误: 类型必须是 morning, noon 或 evening"
        exit 1
        ;;
esac

echo "✅ 发布成功！"
echo ""
echo "📊 获取最新粉丝数据..."
python fetch_follower_stats.py jackaiwison --json-only | jq -r '"当前粉丝: \(.followers)"'
