from django.conf import settings
from django.db import models, transaction


class ScoreTransaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    change = models.IntegerField()
    operation = models.CharField(max_length=255)
    when = models.DateTimeField(auto_now_add=True)

    @transaction.atomic
    def save(self, *args, **kwargs):
        super(ScoreTransaction, self).save(*args, **kwargs)
        profile = self.user.author_profile
        profile.score += self.change
        profile.save()

    def __unicode__(self):
        return u'{operation}: {change} points change'.format(operation=self.operation, change=self.change)

    class Meta:
        get_latest_by = 'pk'
        app_label = 'scoring'