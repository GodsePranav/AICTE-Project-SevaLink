import re
import os

def fix_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    changed = False
    for line in lines:
        # Fix missing spaces in '{% if var==val %}'
        new_line = re.sub(r'\{%\s*if\s+([^ ]+)\s*==\s*\'([^\']+)\'\s*%\}', r"{% if \1 == '\2' %}", line)
        if new_line != line:
            changed = True
        new_lines.append(new_line)
    
    if changed:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"Fixed spaces in {file_path}")

# Run for post_job.html
fix_file('templates/post_job.html')

# Check find_workers.html specifically for tag balance
def check_balance(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    ifs = len(re.findall(r'\{%\s*if\s+', content))
    endifs = len(re.findall(r'\{%\s*endif\s*%\}', content))
    fors = len(re.findall(r'\{%\s*for\s+', content))
    endfors = len(re.findall(r'\{%\s*endfor\s*%\}', content))
    
    print(f"File: {file_path}")
    print(f"  IFs: {ifs}, ENDIFs: {endifs}")
    print(f"  FORs: {fors}, ENDFORs: {endfors}")

check_balance('templates/find_workers.html')
