import re
import html

CHUNKS_RE = re.compile(r"([^<>]+|<[^>]+>)")
CHUNK_TYPES = ("registration_code",)

def parse_text(text, replacements={}):
    chunks = CHUNKS_RE.findall(text)
    serialized_chunks = []
    for chunk in chunks:
        if chunk.startswith("<"):
            assert chunk.endswith(">")
            chunk = chunk[1:-1].strip()
            if chunk not in CHUNK_TYPES:
                raise Exception("Unknown chunk type “{}”".format(chunk))
            if replacements is not None and chunk in replacements:
                serialized_chunks.append(replacements[chunk])
            else:
                serialized_chunks.append({"type": "placeholder", "value": chunk})
        else:
            serialized_chunks.append({"type": "text", "value": html.escape(chunk)})

    return serialized_chunks


class MessageBasedServiceRegistration:
    def __init__(self, service):
        self.service = service

    def get_call_to_action_text(self):
        raise NotImplementedError("This should be implemented by inheriting classes")

    def serialize(self, extra_data=None):
        replacements = None
        if extra_data is not None:
            replacements = {
                "registration_code": {
                    "type": "console",
                    "value": html.escape("/register " + extra_data.user_id),
                }
            }

        text = self.get_call_to_action_text()
        emerging_text_chunks = parse_text(text, replacements)

        return {"type": "scripted-form", "value": {"form": emerging_text_chunks}}

