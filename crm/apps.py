from django.apps import AppConfig

class CrmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm'
    verbose_name = 'CRM'

    def ready(self):
        import uuid
        from django.db.models.signals import pre_save
        from django.dispatch import receiver

        from crm.models import Client

        @receiver(pre_save, sender=Client)
        def assign_client_sync_id(sender, instance, **kwargs):
            if not instance.sync_id:
                instance.sync_id = uuid.uuid4()
