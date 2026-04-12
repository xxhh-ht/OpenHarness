#!/bin/bash
# OpenHarness 一键启动脚本
# 功能：自动检测环境、安装依赖、启动应用、打开配置网页

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# 配置
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
# uv 默认使用 .venv，但也可以使用 .openharness-venv
if [ -f "$REPO_DIR/.venv/bin/activate" ]; then
    VENV_DIR="$REPO_DIR/.venv"
else
    VENV_DIR="$REPO_DIR/.openharness-venv"
fi
DOCS_URL="https://github.com/HKUDS/OpenHarness#-quick-start"
CONFIG_DIR="$HOME/.openharness"

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }

# Banner
echo ""
echo -e "${BOLD}${CYAN}  ██████╗ ██╗  ██╗${RESET}"
echo -e "${BOLD}${CYAN} ██╔═══██╗██║  ██║${RESET}"
echo -e "${BOLD}${CYAN} ██║   ██║███████║${RESET}   OpenHarness Launcher"
echo -e "${BOLD}${CYAN} ██║   ██║██╔══██║${RESET}   One-Click Start"
echo -e "${BOLD}${CYAN} ╚██████╔╝██║  ██║${RESET}"
echo -e "${BOLD}${CYAN}  ╚═════╝ ╚═╝  ╚═╝${RESET}"
echo ""

# ============================================
# 1. 检查Python环境
# ============================================
echo -e "${BOLD}==>${RESET} ${BOLD}检查Python环境${RESET}"

PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
        PY_VER=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
        PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
        if [ "${PY_MAJOR}" -ge 3 ] && [ "${PY_MINOR}" -ge 10 ]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    error "Python 3.10+ 未安装"
    echo ""
    echo "  请先安装Python 3.10+:"
    echo "    macOS: brew install python@3.12"
    echo "    Linux: sudo apt update && sudo apt install python3.10"
    echo ""
    echo "  或访问: https://www.python.org/downloads/"
    echo ""
    echo "  按任意键退出..."
    read -n 1
    exit 1
fi

success "找到 $($PYTHON_CMD --version)"

# ============================================
# 2. 检查uv工具
# ============================================
echo -e "${BOLD}==>${RESET} ${BOLD}检查uv包管理器${RESET}"

if ! command -v uv &>/dev/null; then
    info "安装uv包管理器..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

success "uv已就绪"

# ============================================
# 3. 检查/创建虚拟环境
# ============================================
echo -e "${BOLD}==>${RESET} ${BOLD}检查虚拟环境${RESET}"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    info "创建虚拟环境..."
    uv venv --python "$PYTHON_CMD" "$VENV_DIR" --clear
    success "虚拟环境已创建"
fi

# ============================================
# 4. 同步Python依赖
# ============================================
echo -e "${BOLD}==>${RESET} ${BOLD}同步Python依赖${RESET}"

cd "$REPO_DIR"
uv sync
success "Python依赖已就绪"

# ============================================
# 5. 检查Node.js和npm
# ============================================
echo -e "${BOLD}==>${RESET} ${BOLD}检查Node.js环境${RESET}"

if command -v node &>/dev/null; then
    NODE_VER=$(node --version)
    success "Node.js $NODE_VER 已安装"
    
    # 检查前端依赖
    FRONTEND_DIR="$REPO_DIR/frontend/terminal"
    if [ -d "$FRONTEND_DIR" ] && [ -f "$FRONTEND_DIR/package.json" ]; then
        if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
            info "安装前端依赖..."
            (cd "$FRONTEND_DIR" && npm install --silent 2>/dev/null || true)
            success "前端依赖已安装"
        fi
    fi
else
    warn "Node.js未安装，React TUI功能将不可用"
    echo "  如需完整功能，请安装Node.js 18+:"
    echo "    macOS: brew install node"
fi

# ============================================
# 6. 创建配置目录
# ============================================
echo -e "${BOLD}==>${RESET} ${BOLD}初始化配置${RESET}"

mkdir -p "$CONFIG_DIR/skills"
mkdir -p "$CONFIG_DIR/plugins"
success "配置目录已就绪: $CONFIG_DIR"

# ============================================
# 7. 检查API密钥
# ============================================
echo -e "${BOLD}==>${RESET} ${BOLD}检查API密钥${RESET}"

if [ -z "${ANTHROPIC_API_KEY}" ] && [ -z "${OPENAI_API_KEY}" ]; then
    warn "未检测到API密钥环境变量"
    echo ""
    echo "  请选择操作:"
    echo "    1. 打开配置文档网页"
    echo "    2. 继续启动（稍后配置）"
    echo "    3. 退出"
    echo ""
    echo -n "请选择 [1/2/3]: "
    read -r choice
    
    case "$choice" in
        1)
            info "打开配置文档..."
            open "$DOCS_URL"
            echo ""
            echo "  设置API密钥后重新运行此脚本"
            echo "  按任意键退出..."
            read -n 1
            exit 0
            ;;
        2)
            info "继续启动..."
            ;;
        3|*)
            exit 0
            ;;
    esac
else
    if [ -n "${ANTHROPIC_API_KEY}" ]; then
        success "检测到 ANTHROPIC_API_KEY"
    fi
    if [ -n "${OPENAI_API_KEY}" ]; then
        success "检测到 OPENAI_API_KEY"
    fi
fi

# ============================================
# 8. 打开相关网页（可选）
# ============================================
echo ""
echo -e "${BOLD}==>${RESET} ${BOLD}可选操作${RESET}"
echo "  是否打开配置文档？"
echo "    y - 打开文档网页"
echo "    n - 直接启动（默认）"
echo -n "请选择 [y/N]: "
read -r open_docs

if [ "$open_docs" = "y" ] || [ "$open_docs" = "Y" ]; then
    info "打开配置文档..."
    open "$DOCS_URL"
fi

# ============================================
# 9. 启动OpenHarness
# ============================================
echo ""
echo -e "${BOLD}${GREEN}启动OpenHarness...${RESET}"
echo ""
echo "  使用说明:"
echo "    - 直接输入问题或指令"
echo "    - 使用 /help 查看命令"
echo "    - 使用 /setup 配置"
echo "    - 按 Ctrl+C 退出"
echo ""

# 激活虚拟环境并启动
source "$VENV_DIR/bin/activate"
exec oh
