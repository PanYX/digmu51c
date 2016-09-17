from __future__ import unicode_literals
from django.contrib import admin
from .models import PlayList, Artist, Album, Song, Mv, Tag


# Register your models here.

@admin.register(PlayList, Artist, Album, Song, Mv)
class NeteaseMusicAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'modified')
    search_fields = ('id', 'name')

    def link(self, obj):
        return '<a href="{}">{}</a>'.format(obj.netease_url, obj.id)

    link.short_description = 'Link'
    link.allow_tags = True


@admin.register(Tag)
class Tag(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
