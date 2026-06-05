"""测试国内镜像可达性 + 评估 LLM/FashionCLIP 内存可行性"""
import sys
import paramiko

HOST = "123.57.107.21"
USER = "root"
PASS = "YuJinZe12@."

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15, allow_agent=False, look_for_keys=False)


def run(cmd, timeout=15):
    print(f"\n$ {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if out:
        print(out)
    if err:
        print(f"[stderr] {err}")
    return out


print("=" * 60)
print("1. 模型下载镜像测试")
print("=" * 60)
mirrors = [
    "https://hf-mirror.com/",
    "https://www.modelscope.cn/",
    "https://hf-mirror.com/Marqo/marqo-fashionCLIP/resolve/main/config.json",
    "https://hf-mirror.com/lmstudio-community/Qwen3-4B-Thinking-2507-MLX-4bit/resolve/main/config.json",
    "https://www.modelscope.cn/api/v1/models/Marqo/marqo-fashionCLIP",
    "https://hf-mirror.com/microsoft/Phi-3-mini-4k-instruct/resolve/main/config.json",
    "https://hf-mirror.com/Qwen/Qwen2.5-1.5B-Instruct/resolve/main/config.json",
    "https://hf-mirror.com/Qwen/Qwen2.5-0.5B-Instruct/resolve/main/config.json",
]
for url in mirrors:
    code = run(f"curl -s -o /dev/null -w '%{{http_code}}' -m 8 -L '{url}' 2>&1", timeout=12)
    print(f"  -> {code}  {url}")

print("\n" + "=" * 60)
print("2. 内存评估 (1.6GB 服务器能跑多小的模型?)")
print("=" * 60)
print("规则模式:        ~50MB  ✅")
print("FashionCLIP fp16: ~600MB ✅ (Flask + 系统 剩 ~300MB)")
print("FashionCLIP q8:   ~300MB ✅")
print("Qwen2.5-0.5B Q4:  ~400MB ✅ (Flask+CLIP+LLM 紧)")
print("Qwen2.5-1.5B Q4:  ~1.0GB ❌ (超 1.6GB)")
print("Qwen3-4B Q4:      ~2.3GB ❌ (远超)")

print("\n" + "=" * 60)
print("3. 方案: 改用更小的模型组合")
print("=" * 60)
print("  视觉: Marqo-FashionCLIP (Q8 量化 ~300MB, 或 fp16 ~600MB)")
print("  LLM:  Qwen2.5-0.5B-Instruct Q4 (~400MB) — 中文够用")
print("  Flask + 系统 留 600MB")
print("  → 总占用约 1.4GB，刚好跑得动")

print("\n" + "=" * 60)
print("4. 端口与公网访问检查")
print("=" * 60)
run("ip addr show 2>/dev/null | grep 'inet ' | head -3")
run("curl -s -m 5 http://ifconfig.me 2>/dev/null || curl -s -m 5 https://api.ipify.org")
run("iptables -L INPUT -n 2>/dev/null | head -10")
run("ufw status 2>&1 | head -5")
run("ss -tlnp 2>/dev/null | head -10 || netstat -tlnp 2>/dev/null | head -10")

print("\n" + "=" * 60)
print("5. apt 是否能装系统包")
print("=" * 60)
run("apt list --installed 2>/dev/null | grep -iE 'python3-venv|build-essential' | head -5")
run("apt-cache search python3.12-venv 2>/dev/null | head -3")

client.close()
print("\n=== 探测完成 ===")
