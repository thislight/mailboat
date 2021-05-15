"""The abstract storage layer of Mailboat.

The abstract storage layer of Mailboat is centred on the concept of Record, which is the smallest storable unit in the abstract storage layer and can be either an atomic type or a composite type (see `RecordStorage`).

But in practice we cannot safely store an arbitrary composite type (say any Dataclass), so a special case of `RecordStorage` has been added to the abstract storage layer: `CommonStorage`. A `CommonStorage` is actually a `RecordStorage` with a dictionary of Record type with a string type as a key. We can also see this in its type definition.

However, we often want to read and write directly to a specific type rather than a dictionary. Reading and writing directly to a specific type allows for easier syntax and code completion, but we also don't want to write a new Storage class for each new type.
At this point we can note that `CommonStorage` stores values in a dictionary, and in most cases our data can be converted directly to a dictionary. This module provides a tool class for this usage: `CommonStorageRecordWrapper`. All you need to do is provide a `CommonStorage` and a `CommonStorageAdapter` that takes care of the type conversion to create a `RecordStorage` that reads and writes with a specific type of `RecordStorage` that reads and writes Record with a specific type.

Most of the data structures in Mailboat are declared with `dataclasses.dataclass`. For ease of use, this module provides a direct implementation of `CommonStorageAdapter` for it: `DataclassCommonStorageAdapter`.
"""
from typing import (
    Any,
    AsyncIterable,
    Awaitable,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
)

T = TypeVar("T")


class RecordStorage(Generic[T]):
    """A protocol type which describes basic database operations on a type.

    .. TODO:: Transation should be implemented to provide a way for atomic data operations.

    This class describes all queries in `dict` with `str` as key.
    """

    def store(self, record: T) -> Awaitable[T]:
        """Save a record as new."""
        ...

    def find(self, query: Dict[str, Any]) -> AsyncIterable[T]:
        """Find records which completely matchs `query`."""
        ...

    def find_one(self, query: Dict[str, Any]) -> Awaitable[Optional[T]]:
        """Find one record which completely matchs `query`."""
        ...

    def update_one(self, query: Dict[str, Any], updated: T) -> Awaitable[Optional[T]]:
        """Replace one record, which matchs `query`, with `updated`."""
        ...

    def remove_one(self, query: Dict[str, Any]) -> Awaitable[bool]:
        """Remove one record which matches `query`."""
        ...

    def remove(self, query: Dict[str, Any]) -> Awaitable[int]:
        """Remove all records match `query`."""
        ...


class CommonStorage(RecordStorage[Dict[str, Any]]):
    """A protocol type which is `RecordStorage` with `Dict[str, Any]` (read/write `dict`) for general purpose."""

    pass


class CommonStorageAdapter(Generic[T]):
    """Adapter for `CommonStorageRecordWrapper`.
    Implement `record2dict` and `dict2record` to transform the data between record and dict.

    Typically used in `CommonStorageRecordWrapper`.
    """

    def record2dict(self, record: T) -> Dict[str, Any]:
        """Build a `dict` from `record`."""
        ...

    def dict2record(self, d: Dict[str, Any]) -> T:
        """Build a record from a `d`."""
        ...


class CommonStorageRecordWrapper(RecordStorage[T]):
    """
    A wrapper for `CommonStorage`, convert the common storage to a `RecordStorage` which can read and write a record type directly.

    The typical way to use this class is to extend this class, pass though the common storage and add an implementation of `CommonStorageAdapter`. For example:

    ````python
    class UserRecordStorage(CommonStorageRecordWrapper[UserRecord]):
        def __init__(self, common_storage: CommonStorage) -> None:
            super().__init__(common_storage, DataclassCommonStorageAdapter(UserRecord))
    ````
    """

    def __init__(
        self, common_storage: CommonStorage, adapter: CommonStorageAdapter[T]
    ) -> None:
        self.common_storage = common_storage
        self.adapter = adapter
        super().__init__()

    async def store(self, record: T) -> T:
        d = self.adapter.record2dict(record)
        result = await self.common_storage.store(d)
        return self.adapter.dict2record(result)

    async def find(self, query: Dict[str, Any]) -> AsyncIterable[T]:
        async for doc in self.common_storage.find(query):
            yield self.adapter.dict2record(doc)

    async def find_one(self, query: Dict[str, Any]) -> Optional[T]:
        result = await self.common_storage.find_one(query)
        if result:
            return self.adapter.dict2record(result)
        else:
            return None

    async def update_one(self, query: Dict[str, Any], updated: T) -> Optional[T]:
        result = await self.common_storage.update_one(
            query, self.adapter.record2dict(updated)
        )
        if result:
            return self.adapter.dict2record(result)
        return None

    async def remove(self, query: Dict[str, Any]) -> int:
        return await self.common_storage.remove(query)

    async def remove_one(self, query: Dict[str, Any]) -> bool:
        return await self.common_storage.remove_one(query)


import dataclasses


class DataclassCommonStorageAdapter(Generic[T], CommonStorageAdapter[T]):
    """A `CommonStorageAdapter` for `dataclasses`.

    ..warning:: the checking is performed by dataclass itself. `dataclasses` does not check the actual data type, but checking the fields given.
    """

    def __init__(self, datacls: Type[T]) -> None:
        assert dataclasses.is_dataclass(datacls), "datacls should be a dataclass"
        self.datacls = datacls
        super().__init__()

    def dict2record(self, d: Dict[str, Any]) -> T:
        d = d.copy()
        if "__id" in d:
            d.pop("__id")
        return self.datacls(**d)  # type: ignore # it should work

    def record2dict(self, record: T) -> Dict[str, Any]:
        return dataclasses.asdict(record)


import asyncio
from concurrent.futures import ThreadPoolExecutor

from unqlite import UnQLite, Collection


class UnQLiteStorage(CommonStorage):
    """An implementation of `CommonStorage` for `unqlite.UnQLite`.

    .. note:: This implementation using thead pool to avoid main thread blocking
        The API of `unqlite-python` is synchrounous. To prevent main thread blocking It is wrapped with thread pool executor.
        But the effects should be researched in future.

    .. caution:: I/O operation may unexceptedly block the main thread in constructing.
        The collection is created in constructor， and it may contains I/O operations.

    Related:

    - [unqlite-python API documentation](https://unqlite-python.readthedocs.io/en/latest/api.html)
    """

    def __init__(self, instance: UnQLite, collection_name: str) -> None:
        self.executor = ThreadPoolExecutor(
            thread_name_prefix="mailboat.utils.storage.UnQLiteStorage.executor"
        )
        self.instance = instance
        self.collection_name = collection_name
        self.global_collection = self.new_collection
        """The collection used for storing records.

        ..danger:: Don't use it to U(pdate)R(emove)D(elete).
            The query process in URD will change the internal state of this instance of `unqlite.Collection`.
            It leads to unexecpted behaviours.
        """
        self.global_collection.create()
        super().__init__()

    @property
    def new_collection(self) -> Collection:
        """Return a new collection.

        ..note:: (Rubicon) As the unqlite-python documentation, `unqlite.Collection` actually mantains states (seems like `unqlite.Cursor`) in it.
            We should create a new collection to prevent accidents in concurrent environment.
        """
        return self.instance.collection(self.collection_name)

    def store_sync(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Store the `record` without thread pool."""
        self.global_collection.store(record)
        return record

    def store(self, record: Dict[str, Any]) -> Awaitable[Dict[str, Any]]:
        return asyncio.get_running_loop().run_in_executor(
            self.executor, self.store_sync, record
        )

    @classmethod
    def doc_match(cls, doc: Dict[str, Any], match: Dict[str, Any]) -> bool:
        """Check if `doc` completely matchs `match`."""
        for k in match:
            if k in doc:
                if match[k] == doc[k]:
                    return True
        return False

    def _find(
        self, query: Dict[str, Any], queue: asyncio.Queue[Optional[Dict[str, Any]]]
    ) -> None:
        for doc in self.new_collection.filter(lambda d: self.doc_match(d, query)):
            queue.put_nowait(doc)
        queue.put_nowait(None)

    async def find(self, query: Dict[str, Any]) -> AsyncIterable[Dict[str, Any]]:
        queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        fut = asyncio.ensure_future(
            asyncio.get_running_loop().run_in_executor(
                self.executor, self._find, query, queue
            )
        )
        try:
            while el := (await queue.get()):
                yield el
        finally:
            if not fut.done():
                fut.cancel()

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        async for doc in self.find(query):
            return doc
        return None

    async def update_one(
        self, query: Dict[str, Any], updated: Dict[str, Any], upsert: bool = False
    ) -> Optional[Dict[str, Any]]:
        doc = await self.find_one(query)
        if doc:
            doc_id = doc["__id"]
            self.global_collection.update(doc_id, updated)
        elif upsert:
            await self.store(updated)
            return updated
        return None

    async def remove(self, query: Dict[str, Any]) -> int:
        doc_ids: List[int] = []
        async for doc in self.find(query):
            doc_ids.append(doc["__id"])
        for i in doc_ids:
            self.global_collection.delete(i)
        return len(doc_ids)

    async def remove_one(self, query: Dict[str, Any]) -> bool:
        doc = await self.find_one(query)
        if doc:
            self.global_collection.delete(doc["__id"])
            return True
        else:
            return False
