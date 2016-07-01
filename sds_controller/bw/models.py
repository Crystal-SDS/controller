from django.db import models

# Create your models here.
# class UserBW(models.Model):
#     user_name = models.CharField(max_length=100, primary_key=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     version = models.CharField(max_length=10, blank=False)
#     permissions = models.CharField(max_length=4, blank=False, null=True)
#     path = models.CharField(max_length=200, blank=False, null=True)
#     deployed = models.BooleanField(default=False)
#     class Meta:
#         ordering = ('created_at',)


#
# I don't know the OS IP.
# User > Polices > BW assigned
#
class Account(models.Model):
    account_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)


class Policy(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)


class BWAssigned(models.Model):
    account = models.ForeignKey(Account, related_name='account')
    policy = models.ForeignKey(Policy, related_name='policy')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created_at',)
        unique_together = ('account', 'policy')

# {
# "127.0.0.1:6010": {
# "AUTH_test": {
# "gold": 20,
# "silver": 10
# },
# "AUTH_test2": {
# "silver": 25
# }
# },
# "127.0.0.1:6020": {
# "AUTH_test": {
# "gold": 20,
# "silver": 10
# },
# "AUTH_test2": {
# "silver": 25
# }
# }
# }