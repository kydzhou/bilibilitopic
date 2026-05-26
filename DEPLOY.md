# ECS 部署指南

本文以 **阿里云 ECS + Ubuntu 22.04/24.04** 为例，提供两种部署方式：

1. **Docker 部署（推荐）**：步骤少、易升级
2. **Python + systemd + Nginx**：不依赖 Docker

部署前请先在 GitHub 创建空仓库 `kydzhou/bilibilitopic`，并准备好 LLM 的 `OPENAI_API_KEY`。

---

## 一、服务器准备

### 1. 登录 ECS

```bash
ssh root@你的ECS公网IP
```

### 2. 开放安全组端口

在阿里云控制台 → ECS → 安全组，放行：

| 端口 | 用途 |
|------|------|
| 22 | SSH |
| 80 | HTTP（Nginx 反代，推荐） |
| 443 | HTTPS（可选，配 SSL） |
| 8000 | 直连应用（仅调试，生产建议只走 80/443） |

### 3. 安装基础工具

```bash
apt update && apt upgrade -y
apt install -y git curl
```

---

## 二、方式 A：Docker 部署（推荐）

### 1. 安装 Docker

```bash
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
```

安装 Compose 插件（若尚未安装）：

```bash
apt install -y docker-compose-plugin
```

### 2. 拉取代码

```bash
mkdir -p /opt/bilibilitopic
cd /opt/bilibilitopic
git clone https://github.com/kydzhou/bilibilitopic.git .
```

### 3. 配置环境变量

```bash
cp .env.example .env
nano .env
```

至少填写：

```env
OPENAI_API_KEY=你的key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

### 4. 启动

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f
```

此时可通过 `http://ECS公网IP:8000` 访问。

### 5.（推荐）Nginx 反代到 80 端口

```bash
apt install -y nginx
cp /opt/bilibilitopic/deploy/nginx.conf /etc/nginx/sites-available/bilibilitopic
ln -sf /etc/nginx/sites-available/bilibilitopic /etc/nginx/sites-enabled/bilibilitopic
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

之后用 `http://ECS公网IP` 访问（无需带 `:8000`）。

### 6. 更新版本

```bash
cd /opt/bilibilitopic
git pull
docker compose up -d --build
```

---

## 二、方式 B：Python + systemd + Nginx

适合不想用 Docker 的场景。

### 1. 安装 Python

```bash
apt install -y python3 python3-venv python3-pip nginx
```

### 2. 拉取代码并安装依赖

```bash
mkdir -p /opt/bilibilitopic
cd /opt/bilibilitopic
git clone https://github.com/kydzhou/bilibilitopic.git .

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env
```

### 3. 配置 systemd 服务

```bash
cp deploy/bilibilitopic.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable bilibilitopic
systemctl start bilibilitopic
systemctl status bilibilitopic
```

服务默认监听 `127.0.0.1:8000`，仅本机可访问。

### 4. 配置 Nginx

```bash
cp deploy/nginx.conf /etc/nginx/sites-available/bilibilitopic
ln -sf /etc/nginx/sites-available/bilibilitopic /etc/nginx/sites-enabled/bilibilitopic
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

浏览器访问：`http://ECS公网IP`

### 5. 更新版本

```bash
cd /opt/bilibilitopic
git pull
source .venv/bin/activate
pip install -r requirements.txt
systemctl restart bilibilitopic
```

---

## 三、HTTPS（可选）

若已有域名解析到 ECS，可用 Certbot 申请免费证书：

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d your.domain.com
```

按提示选择自动重定向 HTTP → HTTPS。

---

## 四、健康检查

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/trending?limit=3
```

正常返回 JSON 即表示 B 站接口可用；`llm` 字段为 `ok` 表示 API Key 配置正确。

---

## 五、常见问题

### 1. 分析很慢或超时

LLM 生成报告通常需要 20–60 秒。Nginx 已设置 `proxy_read_timeout 300s`；若仍超时，检查 ECS 出网是否正常、LLM API 是否可达。

### 2. `OPENAI_API_KEY` 未设置

确认 `/opt/bilibilitopic/.env` 存在且已被 Docker Compose 或 systemd 加载。

### 3. B 站接口失败

多为网络或 B 站风控。可重启服务后再试；避免高频请求。

### 4. 端口无法访问

- 检查阿里云安全组是否放行 80/8000
- `ss -lntp | grep 8000` 确认进程在监听
- Docker 方式：`docker compose logs -f`

---

## 六、最小命令速查（Docker）

```bash
cd /opt/bilibilitopic
git clone https://github.com/kydzhou/bilibilitopic.git .   # 首次
cp .env.example .env && nano .env
docker compose up -d --build
```

完成。
