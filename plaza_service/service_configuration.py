class ServiceConfiguration:
    def __init__(self, service_name, blocks, is_public=False):
        self.service_name = service_name
        self.blocks = blocks
        self.is_public = is_public

    def serialize(self):
        return {
            "service_name": self.service_name,
            "blocks": list(map(lambda b: b.serialize(), self.blocks)),
            "is_public": self.is_public,
        }
