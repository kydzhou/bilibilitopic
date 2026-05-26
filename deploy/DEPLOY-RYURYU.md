# ryuryu.xyz/btopic 部署指南

将 B 站话题分析工具部署到 `https://ryuryu.xyz/btopic`（Ubuntu ECS）。

---

## 1. 登录 ECS

```bash
ssh root@你的ECS公网IP
```

---

## 2. 安装 Docker（若未安装）

```bash
apt update && apt upgrade -y
apt install -y git curl
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin nginx
```

---

## 3. 拉取代码

```bash
rm -rf /opt/bilibilitopic
mkdir -p /opt/bilibilitopic
cd /opt/bilibilitopic
git clone https://github.com/kydzhou/bilibilitopic.git .
ls -la docker-compose.yml
```

必须能看到 `docker-compose.yml`，否则不要继续。

---

## 4. 启动 Docker 服务

```bash
cd /opt/bilibilitopic
docker compose up -d --build
docker compose ps
docker compose logs -f
```

本地验证：

```bash
curl http://127.0.0.1:8000/btopic/api/health
curl "http://127.0.0.1:8000/btopic/api/trending?limit=3"
```

---

## 5. 配置 Nginx（ryuryu.xyz/btopic）

找到 ryuryu.xyz 的 Nginx 配置文件：

```bash
ls /etc/nginx/sites-enabled/
# 常见：default 或 ryuryu.xyz
nano /etc/nginx/sites-enabled/default
```

在 `server { server_name ryuryu.xyz ... }` 块内，**追加**以下内容（或直接复制 `deploy/nginx-ryuryu-btopic.conf`）：

```nginx
location = /btopic {
    return 301 /btopic/;
}

location /btopic/ {
    proxy_pass http://127.0.0.1:8000/btopic/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 300s;
    proxy_connect_timeout 60s;
    proxy_send_timeout 300s;
}
```

检查并重载：

```bash
nginx -t && systemctl reload nginx
```

---

## 6. HTTPS（若已有证书）

如果 ryuryu.xyz 已配置 Certbot SSL，把上面的 `location` 块加到 **443 端口的 server {}** 里，而不是只加在 80 端口。

查看配置：

```bash
grep -R "server_name ryuryu.xyz" /etc/nginx/sites-enabled/
```

两个 server 块（80 和 443）都需要 `/btopic/` 反代，或者 80 已自动跳转到 443 则只配 443 即可。

---

## 7. 访问

浏览器打开：

```
https://ryuryu.xyz/btopic/
```

首次使用在页面顶部填写 LLM 配置（保存在浏览器本地）。

---

## 8. 更新

```bash
cd /opt/bilibilitopic
git pull
docker compose up -d --build
```

---

## 常见问题

| 问题 | 原因 / 处理 |
|------|-------------|
| `no configuration file provided` | 目录里没有代码，重新 `git clone ... .` |
| 404 Not Found | Nginx 未配置 `/btopic/`，或 Docker 未设置 `BASE_PATH=/btopic` |
| 静态资源 404 | 确认访问地址带 `/btopic/` 前缀 |
| 502 Bad Gateway | `docker compose ps` 看容器是否运行 |
| 分析超时 | LLM 响应慢，Nginx 已设 300s 超时；检查 ECS 出网 |

---

## 一键命令（首次部署）

```bash
apt update && apt install -y git curl docker-compose-plugin nginx
curl -fsSL https://get.docker.com | sh

mkdir -p /opt/bilibilitopic && cd /opt/bilibilitopic
git clone https://github.com/kydzhou/bilibilitopic.git .
docker compose up -d --build

# 然后手动把 deploy/nginx-ryuryu-btopic.conf 的内容加入 ryuryu.xyz 的 server 块
nginx -t && systemctl reload nginx
```

访问：https://ryuryu.xyz/btopic/
