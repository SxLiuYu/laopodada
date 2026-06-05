import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('123.57.107.21', port=22, username='root', password='YuJinZe12@.', timeout=15, allow_agent=False, look_for_keys=False)
cmds = [
    'ls /opt/wardrobe_env/bin/ 2>/dev/null | head -20',
    'ls /opt/wardrobe_env/lib/python3.12/site-packages/ 2>/dev/null',
    'systemctl status wardrobe.service --no-pager -l 2>&1 | head -20',
    'ss -tlnp 2>/dev/null',
    'ps -ef | grep -v grep | grep -E "python|wardrobe"',
    'tail -20 /opt/wardrobe/logs/wardrobe.out.log 2>/dev/null',
    'tail -20 /opt/wardrobe/logs/wardrobe.err.log 2>/dev/null',
    'free -h',
    'ls /opt/llm_models/Qwen2.5-0.5B/',
    'df -h /opt',
]
for c in cmds:
    print(f'\n>>> {c}')
    si, so, se = ssh.exec_command(c, timeout=30)
    out = so.read().decode('utf-8', errors='replace')
    print(out)
    err = se.read().decode('utf-8', errors='replace').strip()
    if err: print('[err]', err[:500])
ssh.close()
