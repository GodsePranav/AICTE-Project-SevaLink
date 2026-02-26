import os
import re

def fix_split_tags(file_path):
    print(f"Checking {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix {{ ... }} by joining multi-line content into a single line
    # We use non-greedy matching and DOTALL to span multiple lines
    new_content = re.sub(r'\{\{\s*(.+?)\s*\}\}', lambda m: '{{ ' + ' '.join(m.group(1).split()) + ' }}', content, flags=re.DOTALL)
    
    # Fix {% ... %}
    new_content = re.sub(r'\{%\s*(.+?)\s*%\}', lambda m: '{% ' + ' '.join(m.group(1).split()) + ' %}', new_content, flags=re.DOTALL)
    
    if new_content != content:
        print(f"Fixed tags in {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

templates_dir = 'templates'
for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith('.html'):
            fix_split_tags(os.path.join(root, file))

# Also check other app template dirs
for app in ['services', 'social', 'accounts']:
    app_templates = os.path.join(app, 'templates')
    if os.path.exists(app_templates):
        for root, dirs, files in os.walk(app_templates):
            for file in files:
                if file.endswith('.html'):
                    fix_split_tags(os.path.join(root, file))
