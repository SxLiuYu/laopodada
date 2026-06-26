"""uploader.py — laopodada-api HTTP 客户端(节 2.3, 节 3.4 通道 1)

4 个 POST + 4 个 GET(幂等检查)。SSL 跳过(自签证书)。
"""
import io
import json
import ssl
import urllib.error
import urllib.request
import uuid


class APIError(Exception):
    pass


class APIClientError(APIError):
    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"{status}: {body[:200]}")


class APIServerError(APIError):
    pass


class APITimeout(APIError):
    pass


class LaopodadaClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE

    def _request_json(self, method, path, body=None):
        url = f"{self.base_url}{path}"
        data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={"Content-Type": "application/json", "User-Agent": "laopodada-seed/1.0"},
        )
        try:
            with urllib.request.urlopen(req, context=self._ctx, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            raise APIClientError(e.code, body) from e
        except urllib.error.URLError as e:
            raise APITimeout(str(e)) from e
        except TimeoutError as e:
            raise APITimeout(str(e)) from e

    def _request_multipart(
        self, path, fields, file_field, file_bytes, filename, content_type,
    ):
        boundary = uuid.uuid4().hex
        body = io.BytesIO()
        for k, v in fields.items():
            body.write(f"--{boundary}\r\n".encode())
            body.write(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
            body.write(str(v).encode("utf-8"))
            body.write(b"\r\n")
        body.write(f"--{boundary}\r\n".encode())
        body.write(
            f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode()
        )
        body.write(f"Content-Type: {content_type}\r\n\r\n".encode())
        body.write(file_bytes)
        body.write(b"\r\n")
        body.write(f"--{boundary}--\r\n".encode())
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(
            url, data=body.getvalue(), method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with urllib.request.urlopen(req, context=self._ctx, timeout=self.timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            b = e.read().decode("utf-8", "replace")
            raise APIClientError(e.code, b) from e
        except urllib.error.URLError as e:
            raise APITimeout(str(e)) from e

    # ---------- 4 个 POST ----------
    def upload_item(
        self, file_bytes, category, title,
        brand="", color="", season="",
    ):
        return self._request_multipart(
            "/api/v1/items",
            fields={
                "category": category,
                "title": title,
                "brand": brand or "",
                "color": color or "",
                "season": season or "",
            },
            file_field="file",
            file_bytes=file_bytes,
            filename=f"{uuid.uuid4().hex}.jpg",
            content_type="image/jpeg",
        )

    def create_recipe(self, recipe):
        return self._request_json("POST", "/api/v1/recipes", recipe)

    def create_health_article(self, article):
        return self._request_json("POST", "/api/v1/health/articles", article)

    def generate_outfit(self, occasion, season=None, weather=None):
        """调 /api/v1/outfits/recommend(入 db)而不是 /generate(不入 db)。"""
        body = {"occasion": occasion}
        if season:
            body["season"] = season
        if weather:
            body["weather"] = weather
        return self._request_json("POST", "/api/v1/outfits/recommend", body)

    # ---------- 4 个 GET(幂等) ----------
    def get_items(self, limit=500):
        return self._request_json("GET", f"/api/v1/items?limit={limit}")

    def get_recipes(self, limit=500):
        # /api/v1/recipes GET 返 {"recipes":[...]} 无 count,用 len 算
        d = self._request_json("GET", f"/api/v1/recipes?limit={limit}")
        return {"count": len(d.get("recipes", [])), "recipes": d.get("recipes", [])}

    def get_health_articles(self, limit=100):
        # /api/v1/health/articles GET 返 {"articles":[...]} 无 count,用 len 算
        d = self._request_json("GET", f"/api/v1/health/articles?limit={limit}")
        return {"count": len(d.get("articles", [])), "articles": d.get("articles", [])}

    def get_outfits(self, limit=20):
        # /api/v1/outfits GET 返 {"outfits":[...]},用 len 算 count
        d = self._request_json("GET", f"/api/v1/outfits?limit={limit}")
        return {"count": len(d.get("outfits", [])), "outfits": d.get("outfits", [])}

    def health(self):
        # /health 走 nginx 8088 的 location / 会返 SPA index.html,
        # 改用 /api/v1/items?limit=1 验后端真活着(nginx /api/ 反代 8097)
        return self._request_json("GET", "/api/v1/items?limit=1")
