import paramiko
import time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('123.57.107.21', port=22, username='root', password='YuJinZe12@.', timeout=15, allow_agent=False, look_for_keys=False)

# 补装 requirements
print(">>> 补装 requirements.txt (transformers, flask, etc.)")
cmd = "cd /opt/wardrobe && /opt/wardrobe_env/bin/pip install -r requirements.txt --quiet 2>&1 | tail -10"
si, so, se = ssh.exec_command(cmd, timeout=900)
out = so.read().decode('utf-8', errors='replace')
print(out)
err = se.read().decode('utf-8', errors='replace').strip()
if err: print('[err]', err[:500])

# 验证
print("\n>>> 验证包都装了")
si, so, se = ssh.exec_command("/opt/wardrobe_env/bin/pip list 2>/dev/null | grep -iE '^(torch|transformers|flask|Pillow|numpy|requests|dotenv|safetensors|accelerate|tokenizers|huggingface)' | sort", timeout=15)
print(so.read().decode())

# 验证 Python 能 import
print("\n>>> 验证 import")
cmd = "/opt/wardrobe_env/bin/python -c \"import torch, transformers, flask, PIL, numpy, requests, safetensors, accelerate; print('torch', torch.__version__); print('transformers', transformers.__version__); print('flask', flask.__version__); print('OK')\""
si, so, se = ssh.exec_command(cmd, timeout=30)
print(so.read().decode())
err = se.read().decode('utf-8', errors='replace').strip()
if err: print('[err]', err[:500])

ssh.close()
