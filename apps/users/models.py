from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


def valid_email(value):
    try:
        validate_email(value)
        return True
    except ValidationError:
        return False

def get_user_profile(user):
    try:
        return user.get_profile()
    except UserProfile.DoesNotExist:
        return UserProfile.objects.create(user=user)

@receiver(post_save, sender=User)
def force_profile_creation(sender, instance, **kwargs):
    # django-auth-ldap needs to to map stuff like 'manager' and 'office'
    get_user_profile(instance)

class UserProfile(models.Model):
    user = models.ForeignKey(User)
    manager = models.CharField(max_length=100, blank=True)
    manager_user = models.ForeignKey(User, blank=True, null=True,
                                     on_delete=models.SET_NULL,
                                     related_name='manager_user')
    office = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    def __repr__(self):
        return "<UserProfile: %s>" % self.user

@receiver(pre_save, sender=UserProfile)
def explode_office_to_country_and_city(sender, instance, **kwargs):
    if instance.office and ':::' in instance.office:
        city, country = instance.office.split(':::')
        instance.city = city
        instance.country = country

@receiver(pre_save, sender=UserProfile)
def explode_find_manager_user(sender, instance, **kwargs):
    if instance.manager and valid_email(instance.manager):
        for user in User.objects.filter(email__iexact=instance.manager):
            instance.manager_user = user
