import io, os, tarfile, paramiko, time, re

HOST, USER, PASS = "123.57.107.21", "root", "YuJinZe12@."
SRC = r"D:\AI项目\wardrobe"
EXCLUDE = {".venv", "__pycache__", "logs", ".git", "data", "static/uploads",
           "*.pyc", "*.log", ".cache", "nul", "*.bak", "*.tmp",
           "test_download_llm.py", "probe_server.py", "probe_marqo.py", "probe_mirrors.py",
           "deploy_cloud.py", "check_state.py", "wait_install.py", "finish_install.py", "start_service.py"}

def tar_bytes(d):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for r, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if x not in EXCLUDE]
            for f in files:
                if f in EXCLUDE: continue
                if any(f.endswith(p.lstrip("*")) for p in EXCLUDE if "*" in p): continue
                full = os.path.join(r, f)
                rel = os.path.relpath(full, d).replace("\\", "/")
                if ":" in rel: rel = rel.split(":", 1)[1].lstrip("/")
                tf.add(full, arcname=f"wardrobe/{rel}")
    return buf.getvalue()

ansi = re.compile(r"\x1b\[[0-9;]*m")
def run(ssh, cmd, t=120):
    print(f"\n>>> {cmd[:130]}{'...' if len(cmd) > 130 else ''}")
    si, so, se = ssh.exec_command(cmd, timeout=t)
    out = so.read().decode('utf-8', errors='replace')
    for ln in (out.strip().split("\n")[-25:] if out.strip() else []):
        print(f"   {ansi.sub('', ln)}")
    err = se.read().decode('utf-8', errors='replace').strip()
    if err:
        for ln in err.split("\n")[-8:]:
            print(f"   [err] {ansi.sub('', ln)}")
    return out

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, 22, USER, PASS, timeout=15, allow_agent=False, look_for_keys=False)
sftp = ssh.open_sftp()

print("打包...")
data = tar_bytes(SRC)
print(f"  {len(data)/1024:.1f} KB")

print("\n上传...")
with sftp.file("/tmp/wardrobe.tar.gz", "wb") as f:
    f.write(data)
print("  done")

print("\n解压覆盖...")
run(ssh, "rm -rf /opt/wardrobe/ai /opt/wardrobe/app.py && cd /opt && tar xzf /tmp/wardrobe.tar.gz && ls /opt/wardrobe/ai/")
run(ssh, "systemctl restart wardrobe && sleep 8")

print("\n状态:")
run(ssh, "systemctl status wardrobe.service --no-pager -l 2>&1 | head -10")
run(ssh, "curl -s http://127.0.0.1:5050/api/ai/status", 30)
run(ssh, "tail -30 /opt/wardrobe/logs/wardrobe.out.log 2>/dev/null")
run(ssh, "free -h")

sftp.close()
ssh.close()
