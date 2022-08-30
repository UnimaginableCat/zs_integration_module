from django_celery_beat.models import IntervalSchedule
import json
from django.db import models
from enumchoicefield import EnumChoiceField
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from django.utils import timezone

from integration_api.enums import TimeInterval, TaskStatus


class QuantityChecker(models.Model):
    retail_address = models.CharField(max_length=70, blank=False)
    retail_api_key = models.CharField(max_length=100, blank=False)
    access_token = models.TextField(null=True)
    refresh_token = models.TextField(null=True)
    period = EnumChoiceField(TimeInterval, default=TimeInterval.one_min)
    status = EnumChoiceField(TaskStatus, default=TaskStatus.active)
    products = models.TextField(null=True)
    task = models.OneToOneField(
        PeriodicTask,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    def delete(self, *args, **kwargs):
        if self.task is not None:
            self.task.delete()
        return super(self.__class__, self).delete(*args, **kwargs)

    @property
    def interval_schedule(self):
        match self.period:
            case TimeInterval.one_min:
                return IntervalSchedule.objects.get(every=1, period='minutes')
            case TimeInterval.five_minutes:
                return IntervalSchedule.objects.get(every=5, period='minutes')
            case TimeInterval.fifteen_minutes:
                return IntervalSchedule.objects.get(every=15, period='minutes')
            case TimeInterval.one_hour:
                return IntervalSchedule.objects.get(every=1, period='hours')
            case TimeInterval.one_day:
                return IntervalSchedule.objects.get(every=1, period='days')

    def setup_task(self):
        self.task = PeriodicTask.objects.create(
            name=f"Task-quantity-update: {self.retail_address} #{QuantityChecker.objects.filter(retail_address=self.retail_address).count().__str__()}",
            task='update_products_quantity',
            interval=self.interval_schedule,
            args=json.dumps([self.retail_address, self.retail_api_key, self.access_token, self.refresh_token,
                             self.products]),
            start_time=timezone.now()
        )
        self.save()


class PriceChecker(models.Model):
    retail_address = models.CharField(max_length=70, blank=False)
    retail_api_key = models.CharField(max_length=100, blank=False)
    access_token = models.TextField(null=True)
    refresh_token = models.TextField(null=True)
    period = EnumChoiceField(TimeInterval, default=TimeInterval.one_min)
    status = EnumChoiceField(TaskStatus, default=TaskStatus.active)
    products = models.TextField(null=True)
    task = models.OneToOneField(
        PeriodicTask,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    def delete(self, *args, **kwargs):
        if self.task is not None:
            self.task.delete()
        return super(self.__class__, self).delete(*args, **kwargs)

    @property
    def interval_schedule(self):
        match self.period:
            case TimeInterval.one_min:
                return IntervalSchedule.objects.get(every=1, period='minutes')
            case TimeInterval.five_minutes:
                return IntervalSchedule.objects.get(every=5, period='minutes')
            case TimeInterval.fifteen_minutes:
                return IntervalSchedule.objects.get(every=15, period='minutes')
            case TimeInterval.one_hour:
                return IntervalSchedule.objects.get(every=1, period='hours')
            case TimeInterval.one_day:
                return IntervalSchedule.objects.get(every=1, period='days')

    def setup_task(self):
        self.task = PeriodicTask.objects.create(
            name=f"Task-price-update: {self.retail_address} #{PriceChecker.objects.filter(retail_address=self.retail_address).count().__str__()}",
            task='update_products_price',
            interval=self.interval_schedule,
            args=json.dumps([self.retail_address, self.retail_api_key, self.access_token, self.refresh_token,
                             self.products]),
            start_time=timezone.now()
        )
        self.save()
