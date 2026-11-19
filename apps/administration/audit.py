from .models import AuditLog

def audit(actor, action, obj, before=None, after=None):
    AuditLog.objects.create(actor=actor if actor and actor.is_authenticated else None, action=action, entity=obj._meta.label, record_id=obj.pk, before=before, after=after)
