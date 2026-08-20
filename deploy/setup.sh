#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# 诗象志 · 一键部署脚本（Ubuntu 22.04 LTS / 2C2G 起步）
# 用法：  sudo bash deploy/setup.sh
# 可选环境变量： DOMAIN=example.com   ADMIN_TOKEN=xxxx
# 部署后编辑 /opt/poetic-imagery/backend/.env 填入 API Key
# ═══════════════════════════════════════════════════════════
set -euo pipefail

APP_DIR="/opt/poetic-imagery"
DOMAIN="${DOMAIN:-}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

echo "==> [1/8] 系统依赖"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y build-essential python3-venv python3-pip python3-dev \
  nginx git curl ca-certificates gnupg ufw

echo "==> [2/8] 创建 2G Swap（2G 内存机器防 OOM）"
if ! swapon --show | grep -q swapfile; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile
  mkswap /swapfile && swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> [3/8] 开启 BBR（提升网络吞吐）"
if ! grep -q bbr /etc/sysctl.conf 2>/dev/null; then
  echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf
  echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf
  sysctl -p || true
fi

echo "==> [4/8] 部署代码到 ${APP_DIR}"
mkdir -p "${APP_DIR}"
if [ -f "./backend/app/main.py" ]; then
  rsync -a --exclude='backend/.venv' --exclude='frontend/node_modules' --exclude='frontend/dist' \
    --exclude='backend/chroma_data' --exclude='backend/*.db' --exclude='backend/.env' \
    --exclude='.git' ./ "${APP_DIR}/"
else
  git clone https://github.com/huke06/poetic-imagery.git "${APP_DIR}"
fi

echo "==> [5/8] 后端：Python 虚拟环境 + 依赖"
cd "${APP_DIR}/backend"
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip -q
./.venv/bin/pip install -r requirements.txt -q
if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "⚠  请编辑 backend/.env 填入 EMBEDDING_API_KEY（Qwen）等密钥"
fi
if [ -n "${ADMIN_TOKEN}" ]; then
  echo "ADMIN_TOKEN=${ADMIN_TOKEN}" >> .env
fi

echo "==> [6/8] 前端：Node 20 + 构建"
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi
cd "${APP_DIR}/frontend"
npm install --no-audit --no-fund -q
npm run build

echo "==> [7/8] Nginx + systemd"
cp "${APP_DIR}/deploy/poetic-imagery.service" /etc/systemd/system/poetic-imagery.service
if [ -n "${DOMAIN}" ]; then
  sed "s/__DOMAIN__/${DOMAIN} www.${DOMAIN}/" "${APP_DIR}/deploy/poetic-imagery.conf" > /etc/nginx/sites-available/poetic-imagery
else
  sed "s/__DOMAIN__/_/" "${APP_DIR}/deploy/poetic-imagery.conf" > /etc/nginx/sites-available/poetic-imagery
fi
ln -sf /etc/nginx/sites-available/poetic-imagery /etc/nginx/sites-enabled/poetic-imagery
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

systemctl daemon-reload
systemctl enable poetic-imagery
systemctl restart poetic-imagery

echo "==> [8/8] 防火墙（放行 22/80/443）"
ufw allow 22/tcp || true
ufw allow 80/tcp || true
ufw allow 443/tcp || true
echo "y" | ufw enable || true

echo ""
echo "✅ 部署完成！"
echo "   - 后端健康检查 : curl http://127.0.0.1:8000/api/health"
echo "   - 页面地址     : http://<服务器IP>/   （域名解析后可用 http://${DOMAIN}/）"
if [ -n "${DOMAIN}" ]; then
  echo "   - 配置 HTTPS  : sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
fi
echo "   - 别忘了编辑 /opt/poetic-imagery/backend/.env 填入 API Key 后 systemctl restart poetic-imagery"
