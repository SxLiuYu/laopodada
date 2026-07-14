#!/usr/bin/env python3
"""Build IPA from xcarchive using Python zipfile."""
import zipfile, os, shutil, sys, glob

workspace = os.environ.get('GITHUB_WORKSPACE', os.getcwd())
ios_app = os.path.join(workspace, 'ios', 'App')
xcarchive = os.path.join(ios_app, 'build', 'App.xcarchive')
ipa_path = os.path.join(workspace, 'laopodada.ipa')

print(f"Workspace: {workspace}")
print(f"Archive: {xcarchive}")

# Find .app in xcarchive
app_candidates = [
    os.path.join(xcarchive, 'Products', 'Applications', 'App.app'),
    os.path.join(xcarchive, 'Products', 'Applications', '*.app'),
]

app_path = None
for candidate in app_candidates:
    if os.path.isdir(candidate):
        app_path = candidate
        break
    elif '*' in candidate:
        matches = glob.glob(candidate)
        if matches:
            app_path = matches[0]
            break

if not app_path:
    print("ERROR: .app not found in xcarchive")
    # List what we have
    for root, dirs, files in os.walk(xcarchive):
        for f in files:
            print(f"  {os.path.join(root, f)}")
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
