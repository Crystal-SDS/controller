from django.db import models

# Create your models here.
class Storlet(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=False)
    path = models.CharField(max_length=200, blank=False)

    class Meta:
        ordering = ('created_at',)
