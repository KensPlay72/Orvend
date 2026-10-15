from django.core.cache import cache
from django.db import models

CLAVE_CONFIG_PERMISION = "accounts:permision:v1"


class permision(models.Model):
    login_manager = models.BooleanField(default=False)
    home_page = models.BooleanField(default=False)
    ecommerce = models.BooleanField(default=False)

    class Meta:
        db_table = "accounts_permision"

    def __str__(self):
        return f"Permission: {self.login_manager}, {self.home_page}, {self.ecommerce}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(CLAVE_CONFIG_PERMISION)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        cache.delete(CLAVE_CONFIG_PERMISION)

    @classmethod
    def get_config(cls):
        config = cache.get(CLAVE_CONFIG_PERMISION)
        if config is not None:
            return config
        try:
            config = cls.objects.first()
            if not config:
                config = cls.objects.create(
                    login_manager=False,
                    home_page=True,
                    ecommerce=True,
                )
            cache.set(CLAVE_CONFIG_PERMISION, config, timeout=60)
            return config
        except Exception:
            return cls(login_manager=False, home_page=True, ecommerce=True)

    @classmethod
    def ecommerce_activo(cls):
        try:
            return cls.get_config().ecommerce
        except Exception:
            return True

    @classmethod
    def resolver_destino_raiz(cls):
        try:
            config = cls.get_config()
            if config.login_manager:
                return "login"
            if config.home_page:
                return "home"
            if config.ecommerce:
                return "tienda"
            return "login"
        except Exception:
            return "home"