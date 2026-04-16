#!/bin/bash
# 每日 X 增长例行任务
# 使用方法: ./scripts/daily_routine.sh

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_DIR="/Users/jackwl/Code/gitcode/gitxPost"

cd "$PROJECT_DIR"
source .venv/bin/activate

echo -e "${BLUE}=== 🌅 早晨流程开始 ===${NC}\n"

# 1. 扫描雷达
echo -e "${GREEN}📡 1. 扫描 X 雷达...${NC}"
xpost radar-scan
echo ""

# 2. 生成日报
echo -e "${GREEN}📰 2. 生成雷达日报...${NC}"
xpost radar-daily
echo ""

# 3. 获取粉丝数据
echo -e "${GREEN}👥 3. 获取粉丝数据...${NC}"
python fetch_follower_stats.py jackaiwison
echo ""

# 4. 显示今日日报摘要
echo -e "${BLUE}=== 📋 今日雷达日报摘要 ===${NC}"
TODAY=$(date +%Y-%m-%d)
DAILY_REPORT="xinfo/log/day/${TODAY}.md"

if [ -f "$DAILY_REPORT" ]; then
    echo -e "${YELLOW}"
    head -30 "$DAILY_REPORT"
    echo -e "${NC}"
    echo -e "${GREEN}完整日报: $DAILY_REPORT${NC}\n"
else
    echo -e "${YELLOW}⚠️  今日日报未生成${NC}\n"
fi

# 5. 显示待办事项
echo -e "${BLUE}=== ✅ 今日待办 ===${NC}"
echo "[ ] 早间 Post (08:30) - 基于雷达日报的观点"
echo "[ ] 互动回复 (12:00-12:30) - 至少 10 条有价值回复"
echo "[ ] 午间 Post (12:30) - 互动型内容/提问"
echo "[ ] 晚间 Post (20:30) - 今日总结/项目进展"
echo "[ ] Article 创作 (周一/三/五 20:00-21:30)"
echo ""

# 6. 快速发帖提示
echo -e "${BLUE}=== 🚀 快速发帖命令 ===${NC}"
echo -e "${GREEN}早间 Post:${NC}"
echo 'xpost post "你的内容..." --publish'
echo ""
echo -e "${GREEN}午间 Post:${NC}"
echo 'xpost post "问个问题：..." --publish'
echo ""
echo -e "${GREEN}晚间 Post:${NC}"
echo 'xpost post "今天做了..." --publish'
echo ""

echo -e "${BLUE}=== ✨ 完成！祝你今天增长顺利 ===${NC}"
