from base.models import Config


class ConfigFactory:
    """Factory for base.Config model."""

    counter = 0

    @classmethod
    def create(cls, **overrides):
        cls.counter += 1
        defaults = {
            "name": overrides.pop("name", f"Config {cls.counter}"),
            "slug": overrides.pop("slug", f"config-{cls.counter}"),
            "value": overrides.pop("value", "sample"),
            "enabled": overrides.pop("enabled", True),
        }
        return Config.objects.create(**{**defaults, **overrides})

    @classmethod
    def create_batch(cls, count, **overrides):
        return [cls.create(**overrides) for _ in range(count)] # pragma: no cover
