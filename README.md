# monitor_anime_update
这是一个使用 [Bangumi](https://bgm.tv/) API 的番剧更新监控工具，能够在番剧更新时发送邮件通知。

# 部署

去 [Bangumi 开发者平台](https://next.bgm.tv/demo/access-token/create) 申请一个 API_KEY
``` shell
git clone https://github.com/kndxhz/monitor_anime_update
cp .env.example .env
# 编辑 .env 文件，按照模板配置 API_KEY 、SMTP 和要监控的番剧 ID
uv sync
uv run main.py
```

# 协议
[GPL-3.0 License](./LICENSE)