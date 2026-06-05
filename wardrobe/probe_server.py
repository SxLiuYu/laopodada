"""探测远程服务器环境"""
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
print("1. 系统信息")
print("=" * 60)
run("uname -a")
run("cat /etc/os-release 2>/dev/null | head -10")
run("whoami && pwd && hostname")

print("\n" + "=" * 60)
print("2. CPU / 内存 / 磁盘")
print("=" * 60)
run("nproc")
run("free -h")
run("df -h / /tmp /root 2>/dev/null | head -10")

print("\n" + "=" * 60)
print("3. GPU (CUDA)")
print("=" * 60)
run("lspci 2>/dev/null | grep -iE 'vga|3d|nvidia' | head -5")
run("nvidia-smi 2>&1 | head -20")
run("which nvcc && nvcc --version 2>&1 | head -3")

print("\n" + "=" * 60)
print("4. Python 环境")
print("=" * 60)
run("which python3 && python3 --version")
run("which pip3 && pip3 --version")
run("ls -la /usr/bin/python* /usr/local/bin/python* 2>/dev/null")

print("\n" + "=" * 60)
print("5. 关键工具")
print("=" * 60)
for cmd in ["git", "curl", "wget", "ffmpeg", "docker", "systemctl", "nginx", "ufw"]:
    p = run(f"which {cmd} 2>/dev/null && echo OK || echo MISSING")
    if "MISSING" in p:
        pass  # skip

print("\n" + "=" * 60)
print("6. 网络 (能否访问 HuggingFace)")
print("=" * 60)
run("curl -s -o /dev/null -w 'http_code=%{http_code} time=%{time_total}s\\n' -m 10 https://huggingface.co/ 2>&1")
run("curl -s -o /dev/null -w 'http_code=%{http_code} time=%{time_total}s\\n' -m 10 https://github.com/ 2>&1")
run("curl -s -o /dev/null -w 'http_code=%{http_code} time=%{time_total}s\\n' -m 10 https://wttr.in/Beijing?format=j1 2>&1")

client.close()
print("\n=== 探测完成 ===")
