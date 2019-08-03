class ServiceConfiguration:
    def __init__(self, service_name, blocks, registration=None, is_public=False):
        self.service_name = service_name
        self.blocks = blocks
        self.is_public = is_public
        self.registration = registration

    def serialize(self):
        serialized_registration = None
        if self.registration is not None:
            serialized_registration = self.registration.serialize()

        return {
            "service_name": self.service_name,
            "blocks": list(map(lambda b: b.serialize(), self.blocks)),
            "is_public": self.is_public,
            "registration": serialized_registration,
        }
