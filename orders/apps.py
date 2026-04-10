from django.apps import AppConfig

class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'
    verbose_name = 'Заказы'

    def ready(self):
        import uuid
        from django.db.models.signals import pre_save
        from django.dispatch import receiver

        from orders.models import Order

        @receiver(pre_save, sender=Order)
        def assign_order_sync_id(sender, instance, **kwargs):
            if not instance.sync_id:
                instance.sync_id = uuid.uuid4()
