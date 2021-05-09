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
    def store(self, record: T) -> Awaitable[T]:
        ...

    def find(self, query: Dict[str, Any]) -> AsyncIterable[T]:
        ...

    def find_one(self, query: Dict[str, Any]) -> Awaitable[Optional[T]]:
        ...

    def update_one(self, query: Dict[str, Any], updated: T) -> Awaitable[Optional[T]]:
        ...

    def remove_one(self, query: Dict[str, Any]) -> Awaitable[bool]:
        ...

    def remove(self, query: Dict[str, Any]) -> Awaitable[int]:
        ...


class CommonStorage(RecordStorage[Dict[str, Any]]):
    pass


class CommonStorageAdapter(Generic[T]):
    """Adapter for `CommonStorageRecordWrapper`.
    Implement `record2dict` and `dict2record` to transform the data between record and dict.
    """

    def record2dict(self, record: T) -> Dict[str, Any]:
        ...

    def dict2record(self, d: Dict[str, Any]) -> T:
        ...


class CommonStorageRecordWrapper(RecordStorage[T]):
    """
    A wrapper for `CommonStorage`, convert it to a `RecordStorage` which can read and write record directly.
    The correct way to use this class is to extend this class. For example:

    ````
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
    """A `CommonStorageAdapter` for dataclasses.
    Warning: the checking is performed by dataclass itself. Dataclasses does not check the actual data type.
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

from unqlite import UnQLite


class UnQLiteStorage(CommonStorage):
    def __init__(self, instance: UnQLite, collection_name: str) -> None:
        self.executor = ThreadPoolExecutor(
            thread_name_prefix="mailboat.utils.storage.UnQLiteStorage.executor"
        )
        self.instance = instance
        self.collection_name = collection_name
        self.global_collection = self.new_collection
        self.global_collection.create()
        super().__init__()

    @property
    def new_collection(self):
        return self.instance.collection(self.collection_name)

    def store_sync(self, record: Dict[str, Any]) -> Dict[str, Any]:
        self.global_collection.store(record)
        return record

    def store(self, record: Dict[str, Any]) -> Awaitable[Dict[str, Any]]:
        return asyncio.get_running_loop().run_in_executor(
            self.executor, self.store_sync, record
        )

    @classmethod
    def doc_match(cls, doc: Dict[str, Any], match: Dict[str, Any]) -> bool:
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
