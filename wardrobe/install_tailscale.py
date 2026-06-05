import paramiko, re, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('123.57.107.21', 22, 'root', 'YuJinZe12@.', timeout=15, allow_agent=False, look_for_keys=False)
ansi = re.compile(r"\x1b\[[0-9;]*m")
def run(c, t=60):
    si, so, se = ssh.exec_command(c, timeout=t)
    out = so.read().decode('utf-8', errors='replace')
    err = se.read().decode('utf-8', errors='replace').strip()
    return out, err

print("==> 检查 Tailscale 是否已装")
o, e = run("which tailscale || echo 'not installed'")
print(o)

if 'not installed' in o:
    print("\n==> 装 Tailscale (官方安装脚本)")
    o, e = run("curl -fsSL https://tailscale.com/install.sh | sh 2>&1 | tail -15", 120)
    print(ansi.sub('', o))
    if e: print('[err]', ansi.sub('', e)[:500])

print("\n==> 验证安装")
o, _ = run("tailscale --version 2>&1 | head -3")
print(o)

print("\n==> 启动 tailscaled")
o, e = run("systemctl enable --now tailscaled 2>&1 || echo 'no systemctl access'")
print(ansi.sub('', o))
if e: print('[err]', ansi.sub('', e)[:300])

print("\n==> tailscale status (登录前应显示未登录)")
o, _ = run("tailscale status 2>&1 | head -5")
print(o)

print("\n" + "="*60)
print("Tailscale 已装, 但需要登录.")
print("="*60)
print("下一步 (在 Mac mini 上同步操作):")
print("  1) 浏览器打开 https://login.tailscale.com/admin/invite 并生成一次性登录链接")
print("  2) 在 Mac mini 和云服务器各跑一次: tailscale up")
print("  3) 在 Tailscale 控制台 https://login.tailscale.com/admin/machines 确认两台都 online")
print("  4) 记下 Mac mini 的 100.x.x.x IP, 填到云端 /etc/systemd/system/wardrobe.service:")
print('       Environment="LLM_REMOTE_URL=http://100.x.x.x:8001"')
print('       Environment="FASHION_CLIP_REMOTE_URL=http://100.x.x.x:8002"')
print("  5) systemctl daemon-reload && systemctl restart wardrobe")

ssh.close()
