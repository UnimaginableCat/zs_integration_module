from django.db.models.signals import post_save
from django.dispatch import receiver

from integration_api.models import QuantityChecker, PriceChecker
from integration_api.enums import TaskStatus


@receiver(post_save, sender=QuantityChecker)
def create_or_update_periodic_task(sender, instance, created, **kwargs):
    if created:
        instance.setup_task()
    else:
        if instance.task is not None:
            instance.task.enabled = instance.status == TaskStatus.active


@receiver(post_save, sender=PriceChecker)
def create_or_update_periodic_task(sender, instance, created, **kwargs):
    if created:
        instance.setup_task()
    else:
        if instance.task is not None:
            instance.task.enabled = instance.status == TaskStatus.active

