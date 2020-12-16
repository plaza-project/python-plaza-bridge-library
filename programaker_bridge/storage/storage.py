import copy
import json
import os
import re
from typing import Any, Dict

import sqlalchemy
from sqlalchemy import Column, MetaData, String, Table, Text
from xdg import XDG_DATA_HOME

Json = Any  # TODO: Properly define json-ifiable types

# Models
metadata = MetaData()
MAX_USER_ID_SIZE = 64  # Actually 36 (as an UUID), but let's have some margin

Users = Table(
    "USERS",
    metadata,
    Column("id", String(MAX_USER_ID_SIZE), primary_key=True),
    Column("data", Text()),
)

# Storage management
def serialize_data(data: Dict[str, Json]) -> str:
    return json.dumps(data, sort_keys=True)


def deserialize_data(data: str) -> Dict[str, Json]:
    return json.loads(data)


class EngineContext:
    def __init__(self, engine):
        self.engine = engine
        self.connection = None

    def __enter__(self):
        self.connection = self.engine.connect()
        return self.connection

    def __exit__(self, exc_type, exc_value, tb):
        self.connection.close()


class OnUserContext:
    def __init__(self, engine, conn, user, autosave=True):
        self._engine = engine
        self._connection = conn
        self._transaction = conn.begin()
        self._user = user
        self._orig = user.data
        self._autosave = autosave
        self.data = None

    def __enter__(self):
        self.data = deserialize_data(self._user.data)
        return self.data

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            # Exited on error
            self._transaction.rollback()
        else:
            if self._autosave:
                updated_data = serialize_data(self.data)

                if updated_data != self._orig:
                    update = (
                        Users.update()
                        .where(Users.c.id == self._user.id)
                        .values(data=updated_data)
                    )

                    self._connection.execute(update)

            self._transaction.commit()


class Storage:
    def __init__(self, name: str):
        self.name = name
        DB_PATH_ENV = name.upper() + "_BRIDGE_DB_PATH"

        if os.getenv(DB_PATH_ENV, None) is None:
            data_directory = os.path.join(
                XDG_DATA_HOME, "programaker", "bridges", name.lower()
            )
            CONNECTION_STRING = "sqlite:///{}".format(
                os.path.join(data_directory, "db.sqlite3")
            )
        else:
            CONNECTION_STRING = os.environ[DB_PATH_ENV]

        if CONNECTION_STRING.startswith("sqlite"):
            db_file = re.sub("sqlite.*:///", "", CONNECTION_STRING)
            os.makedirs(os.path.dirname(db_file), exist_ok=True)

        self.engine = sqlalchemy.create_engine(CONNECTION_STRING, echo=False)
        self.metadata = metadata
        self.metadata.create_all(self.engine)

    def _connect_db(self):
        return EngineContext(self.engine)

    def create_user(self, user_id: str, data: Dict[str, Json]) -> bool:
        with self._connect_db() as conn:
            user = conn.execute(
                sqlalchemy.select([Users.c.id, Users.c.data]).where(
                    Users.c.id == user_id
                )
            ).fetchone()

            assert user is None
            insert = Users.insert().values(id=user_id, data=serialize_data(data))
            conn.execute(insert)
            return True

    def on_user(self, user_id: str, autosave=True) -> OnUserContext:
        conn = self.engine.connect()
        user = conn.execute(
            sqlalchemy.select([Users.c.id, Users.c.data]).where(Users.c.id == user_id)
        ).fetchone()

        if user is None:
            raise Exception(f"User {user_id} not found")

        return OnUserContext(self.engine, conn, user, autosave)
