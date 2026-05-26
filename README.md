# B站话题分析 Web 版

输入关键词，抓取 B 站近期相关视频，并使用 OpenAI 兼容 API 的 LLM 生成话题趋势分析报告。

仓库地址：https://github.com/kydzhou/bilibilitopic

## 功能

- Web 界面：输入关键词、调整参数、查看报告与视频样本
- 侧边栏展示 B 站当前热搜，点击可填入关键词
- 保留 CLI 命令行模式
- 支持 OpenAI / DeepSeek / 通义等 OpenAI 兼容 API

## 本地运行（Web）

```bash
git clone https://github.com/kydzhou/bilibilitopic.git
cd bilibilitopic

python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows

pip install -r requirements.txt
cp .env.example .env               # 填入 OPENAI_API_KEY

uvicorn web.app:app --host 0.0.0.0 --port 8000 --reload
```

浏览器打开：http://127.0.0.1:8000

## 环境变量

```env
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
HOST=0.0.0.0
PORT=8000
```

DeepSeek 示例：

```env
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

## CLI 模式（可选）

```bash
python main.py analyze "AI绘画"
python main.py trending
python main.py check
```

## Docker 运行

```bash
cp .env.example .env
docker compose up -d --build
```

访问：http://服务器IP:8000

## ECS 部署

详见 [DEPLOY.md](DEPLOY.md)

## 说明

- B 站搜索接口需要 WBI 签名，工具会自动处理
- LLM 分析基于搜索样本推断，结论受样本量与排序影响
- 请合理控制请求频率，遵守 B 站服务条款
