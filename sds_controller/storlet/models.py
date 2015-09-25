from django.db import models

class Dependency(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.CharField(max_length=10, blank=False)
    permissions = models.CharField(max_length=4, blank=False, null=True)
    path = models.CharField(max_length=200, blank=False, null=True)
    class Meta:
        ordering = ('created_at',)

# Create your models here.
class Storlet(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=False)
    path = models.CharField(max_length=200, blank=False, null=True)
    language = models.CharField(max_length=20, blank=False)
    interface_version = models.CharField(max_length=10, blank=False)
    object_metadata = models.CharField(max_length=200, blank=False)
    main_class = models.CharField(max_length=200, blank=False)
    dependency = models.CharField(max_length=200, blank=False)
    class Meta:
        ordering = ('created_at',)

class StorletUser(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    storlet = models.ForeignKey(Storlet, related_name='storlet')
    user_id = models.CharField(max_length=200, blank=False)
    parameters = models.CharField(max_length=400, blank=False, null=True)
    class Meta:
        ordering = ('created_at',)
        unique_together = ('storlet', 'user_id')

class DependencyUser(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    dependency = models.ForeignKey(Storlet, related_name='dependency')
    user_id = models.CharField(max_length=200, blank=False)
    class Meta:
        ordering = ('created_at',)
        unique_together = ('dependency', 'user_id')
