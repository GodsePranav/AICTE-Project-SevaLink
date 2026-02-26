from django.contrib import admin
from .models import Post, Comment, Like

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'timestamp', 'has_image', 'has_voice_note')
    list_filter = ('timestamp',)
    search_fields = ('author__username', 'text_content')
    date_hierarchy = 'timestamp'
    
    def has_image(self, obj):
        return bool(obj.image_upload)
    has_image.boolean = True
    
    def has_voice_note(self, obj):
        return bool(obj.voice_upload)
    has_voice_note.boolean = True

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'author', 'timestamp')
    search_fields = ('author__username', 'text_content')

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'timestamp')
    list_filter = ('timestamp',)
