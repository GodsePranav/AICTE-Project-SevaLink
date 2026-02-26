import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.template.loader import get_template
from django.template import TemplateSyntaxError

template_dir = 'templates'
errors_found = False

print("Checking templates for syntax errors...")
for root, dirs, files in os.walk(template_dir):
    for file in files:
        if file.endswith('.html'):
            rel_path = os.path.relpath(os.path.join(root, file), template_dir)
            template_name = rel_path.replace(os.path.sep, '/')
            try:
                get_template(template_name)
            except TemplateSyntaxError as e:
                print(f"TemplateSyntaxError in {template_name}: {e}")
                errors_found = True
            except Exception as e:
                # Other exceptions during get_template usually indicate missing tags or similar parsing issues
                print(f"Error in {template_name}: {e}")
                errors_found = True

if not errors_found:
    print("All templates parsed successfully!")
