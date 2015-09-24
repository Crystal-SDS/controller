from django.db import models

# Create your models here.
class UserBW(models.Model):
    user_name = models.CharField(max_length=100, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.CharField(max_length=10, blank=False)
    permissions = models.CharField(max_length=4, blank=False, null=True)
    path = models.CharField(max_length=200, blank=False, null=True)
    deployed = models.BooleanField(default=False)
    class Meta:
        ordering = ('created_at',)
