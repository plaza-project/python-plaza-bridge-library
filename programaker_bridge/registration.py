import logging
import re
import shlex

CHUNKS_RE = re.compile(r"([^<>]+|<[^>]+>)")
CHUNK_TYPES = ("u", "a", "input", "value", "autolink", "console", "img")
CONTAINER_CHUNKS = {
    "u": {"fields": {}},
    "autolink": {"fields": {}},
    "a": {"fields": {"href"}},
    "console": {"fields": {}},
}
# Don't have an </img> tag, for example
ITEM_CHUNKS = {"img": {"fields": {"src", "alt"}}}


def parse_text(text, replacements={}):
    chunks = CHUNKS_RE.findall(text)

    parent_chunks = []
    current_chunk = serialized_chunks = {"content": []}

    for chunk in chunks:
        if chunk.startswith("<"):
            assert chunk.endswith(">")
            chunk = chunk[1:-1].strip()
            tagName = re.split("\s", chunk, 1)[0].lower()
            properties = {}
            if chunk.count(" ") > 0:
                property_chunks = shlex.split(chunk.split(" ", 1)[1])
                for pchunk in property_chunks:
                    if "=" not in pchunk:
                        properties[pchunk] = True
                    else:
                        key, value = pchunk.split("=", 1)
                        properties[key] = value

            endTag = tagName.startswith("/")
            if endTag:
                tagName = tagName[1:]

            if tagName.rstrip("/") == "br":
                current_chunk["content"].append({"type": "text", "value": "\n"})
            elif replacements is not None and chunk in replacements:
                current_chunk["content"].append(replacements[chunk])
            elif tagName not in CHUNK_TYPES:
                raise Exception("Unknown chunk type “{}”".format(chunk))
            else:
                if endTag:
                    assert len(parent_chunks) > 0
                    assert len(properties) == 0
                    assert current_chunk["tag"] == tagName
                    parent_chunk = parent_chunks.pop()
                    parent_chunk["content"].append(current_chunk)
                    current_chunk = parent_chunk

                elif tagName in CONTAINER_CHUNKS:
                    parent_chunks.append(current_chunk)
                    current_chunk = {
                        "type": "tag",
                        "tag": tagName,
                        "properties": properties,
                        "content": [],
                    }

                elif tagName in ITEM_CHUNKS:
                    if "/" in properties:
                        del properties["/"]

                    to_del = []
                    for prop in properties:
                        if prop not in ITEM_CHUNKS[tagName].get("fields", {}):
                            logging.warning(
                                "Property '{}' not supported in <{}>".format(
                                    prop, tagName
                                )
                            )
                            to_del.append(prop)

                    for prop in to_del:
                        del properties[prop]

                    current_chunk["content"].append(
                        {
                            "type": "tag",
                            "tag": tagName,
                            "properties": properties,
                            "content": [],
                        }
                    )

                else:
                    current_chunk["content"].append(
                        {
                            "type": "tag",
                            "tag": tagName,
                            "properties": properties,
                            "content": [],
                        }
                    )
        else:
            current_chunk["content"].append({"type": "text", "value": chunk})

    assert len(parent_chunks) == 0
    return serialized_chunks["content"]


class MessageBasedServiceRegistration:
    def __init__(self, **kwargs):
        if "service" in kwargs:
            logging.warn(
                "Service argument is deprecated on MessageBasedServiceRegistration"
            )

    def get_call_to_action_text(self):
        raise NotImplementedError("This should be implemented by inheriting classes")

    def serialize(self, extra_data=None):
        replacements = None
        if extra_data is not None:
            replacements = {
                "registration_code": {
                    "type": "console",
                    "value": "/register " + extra_data.user_id,
                }
            }

        text = self.get_call_to_action_text(extra_data)
        emerging_text_chunks = parse_text(text, replacements)

        return {"type": "message", "value": {"form": emerging_text_chunks}}


class FormBasedServiceRegistration:
    def __init__(self, **kwargs):
        if "service" in kwargs:
            logging.warn(
                "Service argument is deprecated on FormBasedServiceRegistration"
            )

    def get_call_to_action_text(self):
        raise NotImplementedError("This should be implemented by inheriting classes")

    def serialize(self, extra_data=None):
        replacements = None
        if extra_data is not None:
            replacements = {"input": lambda x: x}

        text = self.get_call_to_action_text(extra_data)
        emerging_text_chunks = parse_text(text, replacements)

        return {"type": "form", "value": {"form": emerging_text_chunks}}
