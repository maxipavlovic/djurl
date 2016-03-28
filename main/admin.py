from django.contrib import admin
from main.models import Url

class UrlModel(admin.ModelAdmin):

    def has_change_permission(self, request, obj=None):
        return False

admin.site.register(Url, UrlModel)
