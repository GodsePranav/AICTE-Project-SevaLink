"""Fix find_workers.html to add job selector and pass job_id"""
import re

content = open('templates/find_workers.html', 'r', encoding='utf-8').read()

# 1. Replace the Ask to Do Task button with a job-selector dropdown + button
old_button = """{%if request.user.profile.role == 'Job Provider' %}
                    <button onclick="sendTaskRequest('{{ w.user.id }}', this)" class="btn-profile"
                        style="background: linear-gradient(135deg, #059669, #10b981);">📝 Ask to do Task</button>
                    {%endif %}"""

new_button = """{%if request.user.profile.role == 'Job Provider' %}
                    <div style="display: flex; flex-direction: column; gap: 4px; align-items: flex-start;">
                        {%if provider_jobs %}
                        <select id="job-select-{{ w.user.id }}" style="font-size: 11px; border: 1px solid #e2e8f0; border-radius: 8px; padding: 4px 8px; background: white; font-weight: 600; outline: none; max-width: 180px;">
                            {%for pj in provider_jobs %}
                            <option value="{{ pj.id }}">{{ pj.title|truncatewords:5 }}</option>
                            {%endfor %}
                        </select>
                        {%endif %}
                        <button onclick="sendTaskRequest('{{ w.user.id }}', this)" class="btn-profile"
                            style="background: linear-gradient(135deg, #059669, #10b981);">📝 Ask to do Task</button>
                    </div>
                    {%endif %}"""

content = content.replace(old_button, new_button)

# 2. Replace the JS function to include job_id in the POST body
old_js = """fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': '{{ csrf_token }}',
                'Content-Type': 'application/json'
            }
        })"""

new_js = """const jobSelect = document.getElementById(`job-select-${workerId}`);
        const jobId = jobSelect ? jobSelect.value : null;

        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': '{{ csrf_token }}',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({job_id: jobId})
        })"""

content = content.replace(old_js, new_js)

open('templates/find_workers.html', 'w', encoding='utf-8').write(content)
print('Updated find_workers.html successfully!')
