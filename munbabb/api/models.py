from django.db import models

class Quote(models.Model):
    code = models.CharField(max_length=6, primary_key=True)
    content = models.TextField()
    created_at = models.IntegerField()

class MarketPrice(models.Model):
    typeID = models.IntegerField(primary_key=True)
    buy_price = models.FloatField(default=0)
    sell_price = models.FloatField(default=0)
    updated_at = models.CharField(max_length=50)
