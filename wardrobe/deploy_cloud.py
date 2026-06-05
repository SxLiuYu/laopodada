"""
一键部署 wardrobe 到云服务器 123.57.107.21
1) 打包项目（排除 venv/__pycache__/data/uploads/logs）
2) SFTP 上传
3) 服务端执行 setup_linux.sh + install_service.sh
4) 验证

用法: python deploy_cloud.py
"""
import io
import os
import sys
import tarfile
import time
import paramiko

HOST = "123.57.107.21"
USER = "root"
PASS = "YuJinZe12@."
REMOTE_DIR = "/opt/wardrobe"

# 排除的路径
EXCLUDE = {
    ".venv", "__pycache__", "logs", ".git", "data", "static/uploads",
    "*.pyc", "*.log", ".cache", "nul", "*.bak", "*.tmp",
    "flask.out.log", "flask.err.log",
    "test_download_llm.py", "probe_server.py", "probe_marqo.py", "probe_mirrors.py",
}


def make_tarball(src_dir: str) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for root, dirs, files in os.walk(src_dir):
            # 过滤目录
            dirs[:] = [d for d in dirs if d not in EXCLUDE]
            for f in files:
                if any(f.endswith(p.lstrip("*")) for p in EXCLUDE if "*" in p):
                    continue
                if f in EXCLUDE:
                    continue
                full = os.path.join(root, f)
                rel = os.path.relpath(full, src_dir)
                # 去掉 Windows 盘符
                if ":" in rel:
                    rel = rel.split(":", 1)[1].lstrip("/\\")
                rel = rel.replace("\\", "/")
                tf.add(full, arcname=f"wardrobe/{rel}")
    return buf.getvalue()


def sftp_upload(sftp: paramiko.SFTPClient, local_data: bytes, remote_path: str):
    print(f"  upload -> {remote_path} ({len(local_data)/1024:.1f} KB)")
    with sftp.file(remote_path, "wb") as f:
        f.write(local_data)


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 600) -> str:
    print(f"\n>>> {cmd[:140]}{'...' if len(cmd) > 140 else ''}")
    print(f"   [running up to {timeout}s]")
    start = time.time()
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    elapsed = time.time() - start
    print(f"   [done in {elapsed:.1f}s]")
    if out.strip():
        import re
        ansi = re.compile(r"\x1b\[[0-9;]*m")
        for ln in out.strip().split("\n")[-30:]:
            print(f"   {ansi.sub('', ln)}")
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if err:
        import re
        ansi = re.compile(r"\x1b\[[0-9;]*m")
        for ln in err.split("\n")[-10:]:
            print(f"   [err] {ansi.sub('', ln)}")
    return out


def main():
    src = r"D:\AI项目\wardrobe"
    if not os.path.isdir(src):
        print(f"FATAL: {src} 不存在")
        sys.exit(1)

    print("=" * 60)
    print("1. 打包项目")
    print("=" * 60)
    tar_data = make_tarball(src)
    print(f"   打包完成: {len(tar_data)/1024/1024:.2f} MB")

    print("\n" + "=" * 60)
    print(f"2. 连接 {HOST}")
    print("=" * 60)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=22, username=USER, password=PASS, timeout=15,
                allow_agent=False, look_for_keys=False)
    sftp = ssh.open_sftp()
    print("   连接成功")

    print("\n" + "=" * 60)
    print("3. 上传项目包")
    print("=" * 60)
    remote_tar = "/tmp/wardrobe.tar.gz"
    sftp_upload(sftp, tar_data, remote_tar)

    print("\n" + "=" * 60)
    print("4. 解压 + 安装")
    print("=" * 60)
    run(ssh, f"mkdir -p {REMOTE_DIR} && cd /opt && tar xzf {remote_tar} && ls -la {REMOTE_DIR}/ | head -20")
    run(ssh, f"chmod +x {REMOTE_DIR}/*.sh")
    # 注意：data/ 目录在 tarball 里被排除了，部署后重建
    run(ssh, f"mkdir -p {REMOTE_DIR}/data {REMOTE_DIR}/static/uploads {REMOTE_DIR}/logs")
    run(ssh, f"touch {REMOTE_DIR}/static/uploads/.gitkeep")

    print("\n" + "=" * 60)
    print("5. 装 Python 依赖 (会装 torch + transformers, ~5 分钟)")
    print("=" * 60)
    run(ssh, f"cd {REMOTE_DIR} && bash setup_linux.sh", timeout=900)

    print("\n" + "=" * 60)
    print("6. 装 systemd 服务")
    print("=" * 60)
    run(ssh, f"cd {REMOTE_DIR} && bash install_service.sh", timeout=60)

    print("\n" + "=" * 60)
    print("7. 验证部署")
    print("=" * 60)
    run(ssh, "sleep 3 && systemctl status wardrobe.service --no-pager -l | head -15")
    run(ssh, "curl -s http://127.0.0.1:5050/api/ai/status | head -c 1000")
    run(ssh, "curl -s http://127.0.0.1:5050/ -o /dev/null -w 'HTTP %{http_code} | %{size_download} bytes | %{time_total}s\\n'")
    run(ssh, "tail -30 /opt/wardrobe/logs/wardrobe.out.log 2>/dev/null")

    print("\n" + "=" * 60)
    print("部署完成!")
    print("=" * 60)
    print(f"  访问: http://{HOST}:5050")
    print(f"  日志: journalctl -u wardrobe -f")
    print(f"  状态: systemctl status wardrobe")
    print(f"  重启: systemctl restart wardrobe")

    sftp.close()
    ssh.close()


if __name__ == "__main__":
    main()
