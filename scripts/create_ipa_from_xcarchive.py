#!/usr/bin/env python3
"""Build IPA from xcarchive."""
import zipfile, os, shutil, sys

xcarchive = '/home/runner/work/laopodada/laopodada/ios/App/build/App.xcarchive'
ipa_path = '/home/runner/work/laopodada/laopodada/laopodada.ipa'

print(f"Archive: {xcarchive}")
print(f"Exists: {os.path.isdir(xcarchive)}")

# List xcarchive
for root, dirs, files in os.walk(xcarchive):
    level = root.replace(xcarchive, '').count(os.sep)
    indent = ' ' * 2 * level
    print(f"{indent}{os.path.basename(root)}/")
    subindent = ' ' * 2 * (level + 1)
    for f in files[:5]:
        print(f"{subindent}{f}")

# Find .app
products_apps = os.path.join(xcarchive, 'Products', 'Applications')
print(f"\nProducts/Applications exists: {os.path.isdir(products_apps)}")

if not os.path.isdir(products_apps):
    print("ERROR: Products/Applications not found")
    sys.exit(1)

app_names = [d for d in os.listdir(products_apps) if d.endswith('.app')]
print(f"App names: {app_names}")

if not app_names:
    print("ERROR: No .app found")
    sys.exit(1)

app_path = os.path.join(products_apps, app_names[0])
print(f"Using: {app_path}")

# Create IPA
payload_dir = '/home/runner/work/laopodada/laopodada/Payload'
os.makedirs(payload_dir, exist_ok=True)
shutil.copytree(app_path, os.path.join(payload_dir, app_names[0]))

with zipfile.ZipFile(ipa_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(payload_dir):
        for f in files:
            full = os.path.join(root, f)
            arcname = os.path.relpath(full, payload_dir)
            zf.write(full, os.path.join('Payload', arcname))

shutil.rmtree(payload_dir)
print(f"IPA created: {ipa_path}")
print(f"Size: {os.path.getsize(ipa_path)} bytes")
