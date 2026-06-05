"""用新的 hf CLI 下载"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = sys.stdout

import paramiko
import time

HOST = "123.57.107.21"
USER = "root"
PASS = "YuJinZe12@."

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=22, username=USER, password=PASS, timeout=15, allow_agent=False, look_for_keys=False)


def run_long(cmd, timeout=1500):
    print(f"\n>>> {cmd[:100]}...")
    print(f"  [running up to {timeout}s, please wait...]")
    start = time.time()
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    elapsed = time.time() - start
    print(f"  [done in {elapsed:.1f}s]")
    if out.strip():
        lines = out.strip().split("\n")
        for ln in lines[-15:]:
            # 剥离 ANSI 颜色码
            import re
            ln_clean = re.sub(r'\x1b\[[0-9;]*m', '', ln)
            print(f"  {ln_clean}")
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if err:
        for ln in err.split("\n")[-10:]:
            import re
            ln_clean = re.sub(r'\x1b\[[0-9;]*m', '', ln)
            print(f"  [err] {ln_clean}")


def run_quick(cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if out:
        print(out)
    if err:
        print(f"[stderr] {err}")


# 1) 看 hf 能不能用
print("=" * 60)
print("测试 hf CLI")
print("=" * 60)
run_quick("/opt/wardrobe_env/bin/hf --help 2>&1 | head -30")

# 2) 先下 config + tokenizer 试水
print("\n" + "=" * 60)
print("Step 1: 下 config + tokenizer (快速试水)")
print("=" * 60)
run_long(
    "cd /opt/llm_models && "
    "HF_ENDPOINT=https://hf-mirror.com "
    "/opt/wardrobe_env/bin/hf download Qwen/Qwen2.5-0.5B-Instruct "
    "--include config.json tokenizer.json tokenizer_config.json vocab.json merges.txt special_tokens_map.json generation_config.json "
    "--local-dir Qwen2.5-0.5B",
    timeout=60
)
run_quick("ls -la /opt/llm_models/Qwen2.5-0.5B/")

# 3) 下完整模型 (safetensors)
print("\n" + "=" * 60)
print("Step 2: 下完整 safetensors 模型")
print("=" * 60)
run_long(
    "cd /opt/llm_models && "
    "HF_ENDPOINT=https://hf-mirror.com "
    "/opt/wardrobe_env/bin/hf download Qwen/Qwen2.5-0.5B-Instruct "
    "--local-dir Qwen2.5-0.5B",
    timeout=1500
)

# 4) 验证
print("\n" + "=" * 60)
print("Step 3: 验证")
print("=" * 60)
run_quick("du -sh /opt/llm_models/Qwen2.5-0.5B/ 2>/dev/null")
run_quick("ls -la /opt/llm_models/Qwen2.5-0.5B/ 2>/dev/null")
run_quick("free -h")

client.close()
print("\n=== 完成 ===")
