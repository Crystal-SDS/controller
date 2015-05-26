from django.db import models

class Dependency(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.CharField(max_length=10, blank=False)
    permissions = models.CharField(max_length=4, blank=False, null=True)
    deployed = forms.BooleanField(initial=False)
    class Meta:
        ordering = ('created_at',)

# Create your models here.
class Storlet(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=False)
    path = models.CharField(max_length=200, blank=False, null=True)
    lenguage = models.CharField(max_length=20, blank=False)
    interface_version = models.CharField(max_length=10, blank=False)
    object_metadata = models.CharField(max_length=200, blank=False)
    main_class = models.CharField(max_length=200, blank=False)
    dependency = models.CharField(max_length=200, blank=False)
    deployed = forms.BooleanField(initial=False)
    class Meta:
        ordering = ('created_at',)
