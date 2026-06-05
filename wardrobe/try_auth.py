import paramiko, re
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('123.57.107.21', 22, 'root', 'YuJinZe12@.', timeout=15, allow_agent=False, look_for_keys=False)
ansi = re.compile(r"\x1b\[[0-9;]*m")
def run(c, t=30):
    si, so, se = ssh.exec_command(c, timeout=t)
    out = so.read().decode('utf-8', errors='replace')
    err = se.read().decode('utf-8', errors='replace').strip()
    return out, err

# 后台跑 tailscale up, 捕获 auth URL
print("==> 启动 tailscale up, 捕获登录 URL")
# 用 nohup 避免阻塞
run("nohup tailscale up > /tmp/ts_up.log 2>&1 &", 5)
import time
time.sleep(3)
out, _ = run("cat /tmp/ts_up.log")
print(ansi.sub('', out))

# 也试一次前台 (15s 超时)
print("\n==> 试前台 tailscale up, 看看提示")
si, so, se = ssh.exec_command("timeout 10 tailscale up 2>&1", timeout=20)
try:
    out = so.read().decode('utf-8', errors='replace')
    print(ansi.sub('', out)[:1500])
except Exception as e:
    print(f"[超时, 这是正常的] {e}")

# 取状态
print("\n==> tailscale status")
o, _ = run("tailscale status 2>&1")
print(o[:500])

ssh.close()
