"""Bus de eventos asincrono.

ponytail: una cola asyncio y un diccionario de suscriptores. No hace falta
un broker mientras todo corra en un proceso; si en P12 la vision se mueve a
otro proceso, el reemplazo natural es multiprocessing.Queue o ZeroMQ.
"""
from __future__ import annotations

import asyncio
import logging

from .events import Event

log = logging.getLogger("bus")


class EventBus:
    """Reparte eventos entre componentes identificados por su nombre.

    Cada componente tiene su propio buzon (una cola). Publicar deja el evento
    en una cola central; el bucle `dispatch` lo mueve al buzon del destino.
    Todo lo publicado queda ademas guardado en la traza.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._mailboxes: dict[str, asyncio.Queue[Event]] = {}
        self._trace: list[Event] = []

    def register(self, name: str) -> asyncio.Queue[Event]:
        """Da de alta un componente y devuelve el buzon del que leera sus eventos."""
        if name in self._mailboxes:
            raise ValueError(f"componente ya registrado: {name}")
        self._mailboxes[name] = asyncio.Queue()
        return self._mailboxes[name]

    async def publish(self, ev: Event) -> None:
        """Anota el evento en la traza y lo encola. No espera a que se entregue."""
        self._trace.append(ev)
        await self._queue.put(ev)

    async def dispatch(self) -> None:
        """Bucle de reparto. Un destino desconocido se registra y se descarta."""
        while True:
            ev = await self._queue.get()
            mailbox = self._mailboxes.get(ev.target)
            if mailbox is None:
                log.warning("destino desconocido %r (evento %s)", ev.target, ev.type)
            else:
                log.info("%-22s %s -> %s", ev.type.value, ev.source, ev.target)
                await mailbox.put(ev)
            self._queue.task_done()

    @property
    def trace(self) -> list[Event]:
        """Historial de eventos publicados. Base del informe de latencia de P11."""
        return list(self._trace)
