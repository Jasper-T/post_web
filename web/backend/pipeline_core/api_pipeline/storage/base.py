from abc import ABC, abstractmethod


class BaseStorage(ABC):

    @abstractmethod
    def save(self, save_name: str, data: list):
        pass


class StorageRegistry:
    _registry = {}

    @classmethod
    def register(cls, name: str):
        def wrapper(storage_cls):
            cls._registry[name] = storage_cls
            return storage_cls

        return wrapper

    @classmethod
    def create(cls, name: str, **kwargs):
        if name not in cls._registry:
            raise ValueError(f"Unknown storage: {name}")
        return cls._registry[name](**kwargs)


def resolve_storage(storage, storage_kwargs=None) -> BaseStorage:
    if storage is None:
        return None

    if isinstance(storage, str):
        return StorageRegistry.create(storage, **(storage_kwargs or {}))

    return storage
