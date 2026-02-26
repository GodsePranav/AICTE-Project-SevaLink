import os

def rename_brand(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple replacement for common variations
    new_content = content.replace('SevLink', 'SevaLink')
    new_content = new_content.replace('sevlink', 'sevalink')
    new_content = new_content.replace('SEVLINK', 'SEVALINK')
    
    if new_content != content:
        print(f"Renamed in {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

# Scan through key directories
dirs_to_scan = ['templates', 'accounts', 'services', 'config', 'social']

for d in dirs_to_scan:
    if not os.path.exists(d):
        continue
    for root, dirs, files in os.walk(d):
        for file in files:
            if file.endswith(('.html', '.py', '.txt', '.md', '.css', '.js')):
                rename_brand(os.path.join(root, file))

# Also check root for userinfo.txt or other relevant files
for file in os.listdir('.'):
     if file.endswith(('.txt', '.md')) and os.path.isfile(file):
         rename_brand(file)
