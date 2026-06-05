import paramiko
import time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('123.57.107.21', port=22, username='root', password='YuJinZe12@.', timeout=15, allow_agent=False, look_for_keys=False)

# 等待 pip 后台完成 (轮询 ps)
print("等待 pip 进程结束...")
for i in range(60):  # 最多 20 分钟
    si, so, se = ssh.exec_command("ps -ef | grep -v grep | grep -E 'pip install|setup_linux' | wc -l", timeout=10)
    n = int(so.read().decode().strip() or '0')
    si, so, se = ssh.exec_command("ps -ef | grep -v grep | grep -E 'pip install|setup_linux' | head -3", timeout=10)
    pids = so.read().decode().strip()
    print(f"  [{i*20}s] pip 进程数={n}  {pids[:120]}")
    if n == 0:
        break
    time.sleep(20)

# 检查装好的包
print("\n检查已装包:")
si, so, se = ssh.exec_command("ls /opt/wardrobe_env/lib/python3.12/site-packages/ 2>/dev/null | grep -iE '^(torch|transformers|flask|PIL|numpy|requests|dotenv|safetensors|accelerate|tokenizers|huggingface)' | sort", timeout=15)
print(so.read().decode())

# 检查 setup 日志
si, so, se = ssh.exec_command("tail -30 /tmp/setup_linux.log 2>/dev/null || ls -la /opt/wardrobe/*.log 2>/dev/null", timeout=10)
print("\nsetup 日志:\n", so.read().decode())

ssh.close()
