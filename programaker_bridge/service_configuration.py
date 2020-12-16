from .utils import get_file_hash


class ServiceConfiguration:
    def __init__(
        self,
        service_name,
        blocks,
        registration=None,
        is_public=False,
        icon=None,
        allow_multiple_connections=False,
        collection_manager=None,
    ):
        self.service_name = service_name
        self.blocks = blocks
        self.is_public = is_public
        self.registration = registration
        self.icon = icon
        self.allow_multiple_connections = allow_multiple_connections
        self.collection_manager = collection_manager

    def serialize_collections(self, collection_manager):
        if collection_manager is None:
            return None

        collections = []
        for (_id, collection) in collection_manager._collections.items():
            collections.append({"name": collection.name})

        return collections

    def serialize(self):
        serialized_registration = None
        if self.registration is not None:
            serialized_registration = self.registration.serialize()

        if isinstance(self.icon, str):
            icon_data = {"url": self.icon}
        elif self.icon is not None:
            hash_function, hash_result = get_file_hash(self.icon)
            icon_data = {hash_function: hash_result}
        else:
            icon_data = None

        return {
            "service_name": self.service_name,
            "blocks": list(map(lambda b: b.serialize(), self.blocks)),
            "is_public": self.is_public,
            "registration": serialized_registration,
            "icon": icon_data,
            "allow_multiple_connections": self.allow_multiple_connections,
            "resources": self.serialize_collections(self.collection_manager),
        }
