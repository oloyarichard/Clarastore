from django.apps import AppConfig


class WebappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'webapp'

    def ready(self):
        from django.contrib import admin
        admin.site.site_header = 'Clarastock Admin'
        admin.site.site_title = 'Clarastock Admin'
        admin.site.index_title = 'Dashboard'
