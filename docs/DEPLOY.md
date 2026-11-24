# 部署（公网 + 子域名 + HTTPS）

两条路线，选一条即可。共同前提：

- 一台能装 Docker 的 Linux 服务器（1C1G 足够），或有 Python 3.9+ 的机器。
- 一个域名，并能添加 DNS 记录。示例用 `ilab.example.com`。
- 服务器安全组 / 防火墙放行 80 与 443（Let's Encrypt 需要 80 做 HTTP-01 校验）。

先加 DNS：

```
类型   名称    值
A      ilab    <服务器公网 IP>
```

等 `dig +short ilab.example.com` 返回正确 IP 再继续。

---

## 路线 A：Docker + Caddy（推荐）

Caddy 负责 TLS 与反代，应用容器只监听 `127.0.0.1:8900`。

```bash
# 1. 服务器上拉代码
git clone https://github.com/fatherplus/interaction-lab.git /srv/interaction-lab
cd /srv/interaction-lab

# 2. 固定埋点盐（否则每次重建容器访客哈希都会变）
cat > .env <<EOF
ILAB_DOMAIN=ilab.example.com
IL_TELEMETRY_SALT=$(openssl rand -hex 32)
EOF

# 3. 起应用 + Caddy
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml --env-file .env up -d --build

# 4. 验证
curl -fsS https://ilab.example.com/api/health
```

`deploy/docker-compose.prod.yml` 里 Caddy 已挂载 `deploy/Caddyfile`，证书与配置持久化在命名卷 `caddy_data` / `caddy_config`。首次签发证书需要几十秒，`docker compose logs -f caddy` 可看到 ACME 过程。

Caddyfile 内容（`{$ILAB_DOMAIN}` 由环境变量注入）：

```caddyfile
{$ILAB_DOMAIN} {
	encode zstd gzip
	reverse_proxy interaction-lab:8900
}
```

Caddy 会自动透传 `X-Forwarded-Proto` / `X-Forwarded-Host`，`/cli/ilab` 因此会注入正确的 `https://ilab.example.com`。若前面还有 Cloudflare 等 CDN，建议在 Caddy 里加 `trusted_proxies` 并确认 `CF-Connecting-IP` 头能被读取（应用已支持该头用于哈希与限流）。

---

## 路线 B：systemd + Caddy（不用 Docker）

```bash
# 1. 代码与运行用户
sudo useradd --system --home /srv/interaction-lab --shell /usr/sbin/nologin interactionlab
sudo git clone https://github.com/fatherplus/interaction-lab.git /srv/interaction-lab
sudo mkdir -p /var/lib/interaction-lab /etc/interaction-lab
sudo chown -R interactionlab:interactionlab /srv/interaction-lab /var/lib/interaction-lab

# 2. 环境文件
sudo tee /etc/interaction-lab/env >/dev/null <<EOF
IL_HOST=127.0.0.1
IL_PORT=8900
IL_DB_PATH=/var/lib/interaction-lab/telemetry.sqlite
IL_TELEMETRY_SALT=$(openssl rand -hex 32)
EOF
sudo chmod 600 /etc/interaction-lab/env

# 3. 单元
sudo cp deploy/interaction-lab.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now interaction-lab
systemctl status interaction-lab --no-pager
```

Caddy（`/etc/caddy/Caddyfile`）：

```caddyfile
ilab.example.com {
	encode zstd gzip
	reverse_proxy 127.0.0.1:8900
}
```

```bash
sudo systemctl reload caddy
```

> `ExecStartPre` 会在每次启动前重跑 `python3 build.py`，因此升级只需 `git pull && systemctl restart interaction-lab`。

---

## 路线 C：Nginx 替代 Caddy

服务器已有 Nginx 时，直接加一个 vhost，再用 certbot 签证书：

```bash
sudo cp deploy/nginx.conf /etc/nginx/conf.d/interaction-lab.conf
sudo sed -i 's/ilab.example.com/你的子域名/' /etc/nginx/conf.d/interaction-lab.conf
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d 你的子域名
```

注意 `proxy_set_header Host $host;` 与 `X-Forwarded-Proto` 必须保留，否则 `/cli/ilab` 注入的地址会是 `http://127.0.0.1`。

---

## 备份与恢复

SQLite 在 WAL 模式下不能直接 `cp` 热文件，用在线备份：

```bash
# 备份
docker compose exec interaction-lab python3 - <<'PY'
import sqlite3
src = sqlite3.connect("/data/telemetry.sqlite")
dst = sqlite3.connect("/data/backup.sqlite")
src.backup(dst); dst.close(); src.close()
PY
docker compose cp interaction-lab:/data/backup.sqlite ./telemetry-$(date +%F).sqlite

# 恢复（先停服务）
docker compose stop interaction-lab
cp telemetry-2026-11-24.sqlite ./telemetry-data/telemetry.sqlite
docker compose start interaction-lab
```

非 Docker 部署把路径换成 `IL_DB_PATH` 即可。建议加一条 cron 每日备份到对象存储。

## 升级与回滚

- 升级：`git pull && docker compose up -d --build`（镜像重建后 `HEALTHCHECK` 会自动判定新容器健康）。
- 回滚：`git checkout <上一个 tag> && docker compose up -d --build`；数据库向后兼容，无需迁移。
- 查看日志：`docker compose logs -f interaction-lab`；关闭访问日志可设 `IL_QUIET=1`。

## 本项目的实际线上部署（参考）

当前线上站：**https://ilab.hongme.xyz**（华为云 Flexus L，Ubuntu 24.04，Nginx + Let's Encrypt）。

不用 Docker，走 systemd + 系统 Python，内存占用约 40 MB：

| 项 | 路径 / 值 |
| :--- | :--- |
| 代码与构建产物 | `/opt/interaction-lab`（属主 `ilab`，`dist/` 由启动前构建） |
| 数据 | `/var/lib/interaction-lab/telemetry.sqlite`（WAL，`750`） |
| 环境变量 | `/etc/interaction-lab/env`（`600`，含固定 `IL_TELEMETRY_SALT`） |
| 服务 | `systemctl status interaction-lab`（`127.0.0.1:8900`，启动前跑 `build.py`） |
| Nginx | `/etc/nginx/sites-available/ilab.hongme.xyz.conf`（80 跳转 + ACME，443 反代 8900） |
| 证书 | acme.sh HTTP-01：`/root/.acme.sh/ilab.hongme.xyz_ecc/` → `/etc/nginx/ssl/ilab.hongme.xyz.crt` |

发布只需要：

```bash
rsync -az --delete --exclude '.git/' --exclude 'dist/' --exclude 'telemetry-data/' \
  ./ root@<server>:/opt/interaction-lab/
ssh root@<server> 'chown -R ilab:ilab /opt/interaction-lab && systemctl restart interaction-lab'
```

一个部署细节：`build.py` 只清空 `dist/` 的内容、不删除目录本身，这样 systemd 的
`ReadWritePaths=/opt/interaction-lab/dist`（以及容器卷挂载）不会因为目录被删而失效。

## 上线检查清单

- [ ] `curl -fsS https://<域名>/api/health` 返回 `{"status":"ok",...}`
- [ ] `curl -fsS https://<域名>/ | head` 有 HTML
- [ ] `curl -fsS https://<域名>/api/categories | head -c 200` 有 6 个分类
- [ ] `curl -fsS https://<域名>/cli/ilab | grep DEFAULT_URL` 指向公网域名而不是 127.0.0.1
- [ ] 浏览器打开展廊，标本可操作，⌘K 搜索可用
- [ ] `IL_TELEMETRY_SALT` 已固定并记录在密钥管理里
- [ ] 数据库目录在备份计划内
