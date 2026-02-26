from django.contrib import admin
from .models import Message

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'timestamp', 'is_read', 'has_attachment', 'has_voice_note')
    list_filter = ('is_read', 'timestamp')
    search_fields = ('sender__username', 'receiver__username', 'content')
    date_hierarchy = 'timestamp'

    def has_attachment(self, obj):
        return bool(obj.attachment)
    has_attachment.boolean = True
    
    def has_voice_note(self, obj):
        return bool(obj.voice_note)
    has_voice_note.boolean = True
