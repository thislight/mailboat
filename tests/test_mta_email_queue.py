from email.message import EmailMessage

import pytest
from mailboat.mta import MemoryEmailQueue


class TestMemoryEmailQueue:
    @pytest.mark.asyncio
    @pytest.mark.skip(
        "rubicon: this test's task is always in pending and the eventloop stuck at I/O selector under cpython 3.9.2"
    )
    async def test_method_get_should_return_different_entities_across_calls(self):
        queue = MemoryEmailQueue()
        email0 = EmailMessage()
        email1 = EmailMessage()
        email2 = EmailMessage()
        await queue.put(email0)
        await queue.put(email1)
        await queue.put(email2)

        result0, id0 = await queue.get()
        result1, id1 = await queue.get()
        result2, id2 = await queue.get()
        assert result0 != result1
        assert result1 != result2
        assert result2 != result0
        assert id0 != id1
        assert id1 != id2
        assert id2 != id0
