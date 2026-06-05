import paramiko
import time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('123.57.107.21', port=22, username='root', password='YuJinZe12@.', timeout=15, allow_agent=False, look_for_keys=False)

# 1. 装服务
print(">>> 装 systemd 服务")
si, so, se = ssh.exec_command("cd /opt/wardrobe && bash install_service.sh 2>&1", timeout=30)
print(so.read().decode())
err = se.read().decode('utf-8', errors='replace').strip()
if err: print('[err]', err[:500])

# 2. 等几秒让 app 启动
print("\n>>> 等 5 秒让 app 启动...")
time.sleep(5)

# 3. 状态
print("\n>>> systemctl status")
si, so, se = ssh.exec_command("systemctl status wardrobe.service --no-pager -l 2>&1 | head -25", timeout=15)
print(so.read().decode())

# 4. 端口
print("\n>>> 端口监听")
si, so, se = ssh.exec_command("ss -tlnp | grep -E ':5050'", timeout=10)
print(so.read().decode())

# 5. AI 状态
print("\n>>> /api/ai/status")
si, so, se = ssh.exec_command("curl -s http://127.0.0.1:5050/api/ai/status", timeout=30)
out = so.read().decode('utf-8', errors='replace')
print(out)

# 6. 首页
print("\n>>> GET /")
si, so, se = ssh.exec_command("curl -s -o /dev/null -w 'HTTP %{http_code} | %{size_download} bytes | %{time_total}s\\n' http://127.0.0.1:5050/", timeout=15)
print(so.read().decode())

# 7. 日志
print("\n>>> logs")
si, so, se = ssh.exec_command("tail -30 /opt/wardrobe/logs/wardrobe.out.log 2>/dev/null", timeout=10)
print(so.read().decode())
si, so, se = ssh.exec_command("tail -30 /opt/wardrobe/logs/wardrobe.err.log 2>/dev/null", timeout=10)
print(so.read().decode())

# 8. 内存
print("\n>>> 内存")
si, so, se = ssh.exec_command("free -h", timeout=10)
print(so.read().decode())

ssh.close()
