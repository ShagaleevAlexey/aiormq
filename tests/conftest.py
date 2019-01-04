import asyncio
import os

import pytest
from async_generator import yield_, async_generator
from yarl import URL

from aiormq.connection import Connection


@pytest.fixture
def event_loop():
    asyncio.get_event_loop().close()
    loop = asyncio.new_event_loop()     # type: asyncio.AbstractEventLoop
    loop.set_debug(True)
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        loop.close()


def cert_path(*args):
    return os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'certs', *args
    )


amqp_urls = [
    URL(os.getenv('AMQP_URL', 'amqp://guest:guest@localhost/')),
    URL(os.getenv(
        'AMQP_URL', 'amqp://guest:guest@localhost/'
    )).with_scheme('amqps').with_query({
        "cafile": cert_path('ca.pem'),
        "no_verify_ssl": 1,
    }),
    URL(os.getenv(
        'AMQP_URL', 'amqp://guest:guest@localhost/'
    )).with_scheme('amqps').with_query({
        "cafile": cert_path('ca.pem'),
        "keyfile": cert_path('client.key'),
        "certfile": cert_path('client.pem'),
        "no_verify_ssl": 1,
    })
]


@pytest.fixture(params=amqp_urls)
@async_generator
async def amqp_connection(request, event_loop):
    connection = Connection(request.param, loop=event_loop)

    await connection.connect()

    try:
        await yield_(connection)
    finally:
        await connection.close()


channel_params = [
    dict(channel_number=None, frame_buffer=10, publisher_confirms=True),
    dict(channel_number=None, frame_buffer=1, publisher_confirms=True),
    dict(channel_number=None, frame_buffer=10, publisher_confirms=False),
    dict(channel_number=None, frame_buffer=1, publisher_confirms=False),
]


@pytest.fixture(params=channel_params)
@async_generator
async def amqp_channel(request, amqp_connection):
    try:
        await yield_(await amqp_connection.channel(**request.param))
    finally:
        await amqp_connection.close()