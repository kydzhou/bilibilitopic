# tools.ryuryu.xyz/btopic 部署指南

将 B 站话题分析工具部署到 `https://tools.ryuryu.xyz/btopic`（与现有程序共存）。

---

## 共存说明

| 资源 | 现有程序 | 本程序 |
|------|----------|--------|
| 域名 | `tools.ryuryu.xyz/` | `tools.ryuryu.xyz/btopic/` |
| 端口 | `127.0.0.1:8000`（uvicorn） | `127.0.0.1:8001`（Docker） |
| Nginx | `/etc/nginx/sites-enabled/steam-review` | 在同一文件追加 location |

---

## 1. 拉取代码

```bash
cd /opt/bilibilitopic
git pull
# 或首次：
# git clone https://github.com/kydzhou/bilibilitopic.git /opt/bilibilitopic
```

---

## 2. 启动 Docker（使用 8001 端口）

```bash
cd /opt/bilibilitopic
docker compose up -d --build
docker compose ps
```

验证：

```bash
curl http://127.0.0.1:8001/btopic/api/health
```

应返回 JSON，而不是 `Not Found`。

---

## 3. 配置 Nginx（追加到 steam-review）

```bash
nano /etc/nginx/sites-enabled/steam-review
```

在 `server { server_name tools.ryuryu.xyz; ... }` 块内**追加**（不要删原有配置）：

```nginx
location = /btopic {
    return 301 /btopic/;
}

location /btopic/ {
    proxy_pass http://127.0.0.1:8001/btopic/;
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

或直接复制仓库文件：

```bash
cat /opt/bilibilitopic/deploy/nginx-tools-btopic.conf
# 把内容粘贴进 steam-review 的 server 块
```

重载：

```bash
nginx -t && systemctl reload nginx
```

若已配 HTTPS，80 和 443 的 `tools.ryuryu.xyz` server 块都要加（或只在 443 加，若 80 已跳转到 443）。

---

## 4. 访问

```
https://tools.ryuryu.xyz/btopic/
```

页面顶部填写 LLM 配置即可使用。

---

## 5. 更新

```bash
cd /opt/bilibilitopic
git pull
docker compose up -d --build
```

---

## 一键命令

```bash
cd /opt/bilibilitopic && git pull && docker compose up -d --build
curl http://127.0.0.1:8001/btopic/api/health
nginx -t && systemctl reload nginx
```

访问：https://tools.ryuryu.xyz/btopic/
