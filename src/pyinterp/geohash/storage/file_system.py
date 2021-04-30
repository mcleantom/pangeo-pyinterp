# Copyright (c) 2021 CNES
#
# All rights reserved. Use of this source code is governed by a
# BSD-style license that can be found in the LICENSE file.
from typing import Any, Iterable, List, Optional, Tuple
import pickle
import fsspec
import numcodecs


class FileSystem:
    def __init__(self,
                 fs: fsspec.AbstractFileSystem,
                 root: str,
                 compressor: Optional[numcodecs.Blosc] = None):
        self.fs = fs
        self.compressor = compressor or numcodecs.Blosc()
        self.root = root
        self._transactions = set()
        self._deleted = set()
        self.fs.mkdirs(root, exist_ok=True)

    @staticmethod
    def _pending_key(key: bytes) -> bytes:
        return b'__' + key

    def _entry(self, key: bytes) -> str:
        if key in (self._transactions | self._deleted):
            key = self._pending_key(key)
        return self.fs.sep.join((self.root, key.decode()))

    def __contains__(self, key: bytes):
        return self.fs.exists(self._entry(key))

    def __delitem__(self, key: bytes) -> None:
        self._deleted.add(key)

    def _read(self, entry: str) -> List[Any]:
        with self.fs.open(entry, mode="rb") as stream:
            return pickle.loads(self.compressor.decode(stream.read()))

    def _write(self, entry: str, data: Any) -> None:
        with self.fs.open(entry, mode="wb") as stream:
            stream.write(self.compressor.encode(pickle.dumps(data)))

    def __getitem__(self, key: bytes) -> List[Any]:
        return self._read(self._entry(key))

    def __setitem__(self, key: bytes, value: object) -> None:
        if not isinstance(value, list):
            value = [value]
        self._transactions.add(key)
        self._write(self._entry(key), value)

    def extend(self, other: Iterable[Tuple[bytes, Any]]) -> None:
        for key, value in other:
            if not isinstance(value, list):
                value = [value]
            entry = self._entry(key)
            if self.fs.exists(entry):
                value = self._read(entry) + value
            self._write(entry, value)

    def update(self, other: Iterable[Tuple[bytes, Any]]) -> None:
        for key, value in other:
            self[key] = value

    def _keys(self) -> List[str]:
        return self.fs.listdir(self.root, detail=False)

    def keys(self) -> Iterable[bytes]:
        for item in self.fs.listdir(self.root, detail=False):
            yield item.split(self.fs.sep)[-1].lstrip("_").encode()

    def values(self, keys: Optional[Iterable[bytes]] = None) -> List[Any]:
        keys = keys or self.keys()
        return [self[key] for key in keys]

    def items(
        self,
        keys: Optional[Iterable[bytes]] = None
    ) -> List[Tuple[bytes, List[Any]]]:
        keys = keys or self.keys()
        return [(key, self[key]) for key in keys]

    def rollback(self):
        for item in self._transactions:
            entry = self.fs.sep.join(
                (self.root, self._pending_key(item).decode()))
            self.fs.rm(entry, recursive=True)
        self._transactions.clear()
        self._deleted.clear()

    def commit(self):
        for item in self._deleted:
            self.fs.delete(self.fs.sep.join((self.root, item.decode())),
                           recursive=True)
        self._deleted.clear()

        for item in self._transactions:
            new_entry = self.fs.sep.join(
                (self.root, self._pending_key(item).decode()))
            old_entry = self.fs.sep.join((self.root, item.decode()))
            if self.fs.exists(old_entry):
                self.fs.rm(old_entry, recursive=True)
            self.fs.mv(new_entry, old_entry, recursive=True)
        self._transactions.clear()

    def __enter__(self) -> "FileSystem":
        return self

    def __exit__(self, type, value, tb):
        if type is None and value is None and tb is None:
            self.commit()
        else:
            self.rollback()
