from django.db import models

class Sessions(models.Model):
    dummy = models.IntegerField(default = 0)

    class Meta:
        db_table = "sessions"

class Fields (models.Model):
    session = models.ForeignKey(Sessions)
    key     = models.CharField(max_length = 64)
    value   = models.CharField(max_length = 64)

    class Meta:
        db_table = "fields"
