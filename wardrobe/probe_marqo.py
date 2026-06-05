"""深入查 Marqo-FashionCLIP 在国内镜像的可用性"""
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


# ModelScope 上的 marqo 模型
print("=" * 60)
print("ModelScope 上的 Marqo 模型")
print("=" * 60)
run("curl -s -m 10 'https://www.modelscope.cn/api/v1/models?Search=marqo&PageSize=10' 2>&1 | head -c 2000")

print("\n" + "=" * 60)
print("ModelScope 上 fashion 关键词")
print("=" * 60)
run("curl -s -m 10 'https://www.modelscope.cn/api/v1/models?Search=fashion-clip&PageSize=10' 2>&1 | head -c 2000")

print("\n" + "=" * 60)
print("hf-mirror 上 Marqo 完整路径探测")
print("=" * 60)
# 试 hf-mirror 的不同路径
for path in [
    "Marqo/marqo-fashionCLIP",
    "patrickjohncyh/fashion-clip",
    "Marqo/marqo-fashionSigLIP",
]:
    code = run(f"curl -s -o /dev/null -w '%{{http_code}}' -m 8 -L 'https://hf-mirror.com/{path}/resolve/main/config.json'")
    print(f"  -> {code}  {path}")

print("\n" + "=" * 60)
print("GGUF 模型在 hf-mirror")
print("=" * 60)
for path in [
    "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
    "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
    "lmstudio-community/Qwen2.5-0.5B-Instruct-GGUF",
]:
    code = run(f"curl -s -o /dev/null -w '%{{http_code}}' -m 8 -L 'https://hf-mirror.com/{path}/resolve/main/config.json'")
    print(f"  -> {code}  {path}")

# 检查具体 GGUF 文件
print("\n" + "=" * 60)
print("具体 GGUF 文件 (Qwen2.5-0.5B)")
print("=" * 60)
run("curl -s -m 10 'https://hf-mirror.com/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/' 2>&1 | head -c 1500")

# 检查小模型可行性
print("\n" + "=" * 60)
print("更小候选: 通用 CLIP (openai/clip-vit-base-patch32)")
print("=" * 60)
for path in [
    "openai/clip-vit-base-patch32",
    "laion/CLIP-ViT-B-32-laion2B-s34B-b79K",
]:
    code = run(f"curl -s -o /dev/null -w '%{{http_code}}' -m 8 -L 'https://hf-mirror.com/{path}/resolve/main/config.json'")
    print(f"  -> {code}  {path}")

client.close()
