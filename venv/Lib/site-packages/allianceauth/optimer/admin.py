from django.contrib import admin

from allianceauth.optimer.models import OpTimer, OpTimerType

admin.site.register(OpTimerType)
admin.site.register(OpTimer)
