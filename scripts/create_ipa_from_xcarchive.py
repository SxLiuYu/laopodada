#!/usr/bin/env python3
"""Build IPA from xcarchive using Python zipfile."""
import zipfile, os, shutil, sys, glob

workspace = os.environ.get('GITHUB_WORKSPACE', os.getcwd())
ios_app = os.path.join(workspace, 'ios', 'App')
xcarchive = os.path.join(ios_app, 'build', 'App.xcarchive')
ipa_path = os.path.join(workspace, 'laopodada.ipa')

print(f"Workspace: {workspace}")
print(f"Archive: {xcarchive}")

# List xcarchive structure
for root, dirs, files in os.walk(xcarchive):
    level = root.replace(xcarchive, '').count(os.sep)
    indent = ' ' * 2 * level
    print(f"{indent}{os.path.basename(root)}/")
    subindent = ' ' * 2 * (level + 1)
    for f in files:
        print(f"{subindent}{f}")

# Find .app
app_path = None
products_apps = os.path.join(xcarchive, 'Products', 'Applications')
if os.path.isdir(products_apps):
    for d in os.listdir(products_apps):
        if d.endswith('.app'):
            app_path = os.path.join(products_apps, d)
            break

if not app_path or not os.path.isdir(app_path):
    print(f"ERROR: .app not found. products_apps={products_apps}, exists={os.path.isdir(products_apps)}")
    sys.exit(1)

print(f"Found .app: {app_path}")

# Create IPA
payload_name = os.path.basename(app_path)
payload_dir = os.path.join(os.path.dirname(ipa_path), 'Payload')
dst = os.path.join(payload_dir, payload_name)
os.makedirs(payload_dir, exist_ok=True)

shutil.copytree(app_path, dst)

with zipfile.ZipFile(ipa_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(payload_dir):
        for f in files:
            full = os.path.join(root, f)
            arcname = os.path.relpath(full, os.path.dirname(payload_dir))
            zf.write(full, arcname)

shutil.rmtree(payload_dir)
print(f"IPA created: {ipa_path}")
print(f"Size: {os.path.getsize(ipa_path)} bytes")
