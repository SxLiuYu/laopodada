#!/usr/bin/env python3
"""Build IPA from xcarchive using Python zipfile."""
import zipfile, os, shutil, sys

xcarchive = '/home/runner/work/laopodada/laopodada/ios/App/build/App.xcarchive'
ipa_path = '/home/runner/work/laopodada/laopodada/laopodada.ipa'

try:
    print(f"Archive exists: {os.path.isdir(xcarchive)}")
    
    products_apps = os.path.join(xcarchive, 'Products', 'Applications')
    print(f"Products/Applications exists: {os.path.isdir(products_apps)}")
    
    if not os.path.isdir(products_apps):
        print("ERROR: Products/Applications not found")
        sys.exit(1)
    
    app_names = [f for f in os.listdir(products_apps) if f.endswith('.app')]
    print(f"App names: {app_names}")
    
    if not app_names:
        print("ERROR: No .app found in Products/Applications")
        sys.exit(1)
    
    app_path = os.path.join(products_apps, app_names[0])
    print(f"Using: {app_path}")
    
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
    print(f"SUCCESS: IPA created at {ipa_path} ({os.path.getsize(ipa_path)} bytes)")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
