from django.apps import AppConfig
from django.apps import apps


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'
    verbose_name = 'Sản phẩm'

    def ready(self):
        # Keep original app path in INSTALLED_APPS but relabel admin text to Vietnamese.
        try:
            token_blacklist_app = apps.get_app_config('token_blacklist')
            token_blacklist_app.verbose_name = 'Danh sách chặn Token'

            model_labels = {
                'blacklistedtoken': 'Token đã chặn',
                'outstandingtoken': 'Token còn hiệu lực',
            }
            for model in token_blacklist_app.get_models():
                label = model_labels.get(model._meta.model_name)
                if label:
                    model._meta.verbose_name = label
                    model._meta.verbose_name_plural = label
        except LookupError:
            # Token blacklist app may be disabled in some environments.
            pass
