from __future__ import print_function

from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from hendrix.experience import crosstown_traffic
from protos import protos


class Url(models.Model):
    url = models.URLField(unique=True)
    minute = models.PositiveIntegerField(default=0)
    second = models.PositiveIntegerField(default=0)


class Result(models.Model):
    url = models.ForeignKey(Url)
    title = models.CharField(max_length=500, blank=True, null=True)
    encoding = models.CharField(max_length=100, blank=True, null=True)
    h1 = models.CharField(max_length=500, blank=True, null=True)
    datetime = models.DateTimeField(auto_now_add=True, null=True)
    iscorrect = models.BooleanField(default=False)


def get_results():
    return Result.objects.all()

@receiver(post_save, sender=Url)
def get_html_source(sender, instance, **kwargs):
    print(instance)

    def save_result(response, url, dt):
        if not response:
            new_result = Result(
                url=url,
                iscorrect=False,
                datetime=dt
            )
        else:
            new_result = Result(
                url=url,
                title=response.title,
                encoding=response.original_encoding,
                h1=response.h1,
                iscorrect=True,
                datetime=dt
            )
        new_result.save()

    @crosstown_traffic()
    def get_url_data():
        timeshift = instance.minute*60 + instance.second
        protos.sender(bytes(instance.url), save_result, instance, timeshift)

