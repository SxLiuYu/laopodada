#!/usr/bin/env python3
"""Create IPA from .app bundle."""
import zipfile, os, shutil, sys

app_path = sys.argv[1]
output_path = sys.argv[2]

print(f"App: {app_path}")
print(f"Output: {output_path}")

if not os.path.isdir(app_path):
    print(f"ERROR: {app_path} not found")
    sys.exit(1)

app_name = os.path.basename(app_path)
payload_dir = os.path.join(os.path.dirname(output_path), "Payload")
os.makedirs(payload_dir, exist_ok=True)

dst = os.path.join(payload_dir, app_name)
shutil.copytree(app_path, dst)

with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(payload_dir):
        for f in files:
            full = os.path.join(root, f)
            arcname = os.path.relpath(full, os.path.dirname(payload_dir))
            zf.write(full, arcname)
            print(f"  packed: {arcname}")

shutil.rmtree(payload_dir)
print(f"IPA created: {output_path}")
size = os.path.getsize(output_path)
print(f"Size: {size} bytes")
