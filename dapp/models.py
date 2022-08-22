from operator import mod
from unicodedata import name
from django.db import models

# Create your models here.

class Dao(models.Model):
    name = models.CharField(max_length=250)
    dao_id = models.BigIntegerField()

    def __str__(self) -> str:
        return self.name

class Proposal(models.Model):
    dao_id = models.BigIntegerField()
    name = models.CharField(max_length=250)

