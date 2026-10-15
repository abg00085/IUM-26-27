"""Clase base de todo Modality Component (Tema 1)."""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from .bus import EventBus
from .events import Event, EventType


class ModalityComponent(ABC):
    """Un MC solo conoce el bus y su propio nombre.

    No conoce al Interaction Manager ni a los demas componentes: ese
    desacoplamiento es lo que permite anadir una modalidad sin tocar las
    existentes (Tema 1, ejemplo 4).
    """

    def __init__(self, name: str, bus: EventBus) -> None:
        self.name = name
        self.bus = bus
        self.mailbox = bus.register(name)  # aqui llegan los eventos para este MC
        self._active = False               # True mientras atiende un StartRequest

    @abstractmethod
    async def on_start(self, ev: Event) -> None:
        """Reacciona a un StartRequest. Debe emitir DoneNotification al terminar."""

    async def on_cancel(self, ev: Event) -> None:
        """Reaccion a CancelRequest. Base del barge-in de P10."""
        self._active = False

    async def emit(self, type: EventType, context: str, data=None,
                   target: str = "IM") -> None:
        """Publica un evento con este componente como origen.

        El destino por defecto es el IM, que es quien recibe los resultados.
        """
        await self.bus.publish(Event(type=type, source=self.name,
                                     target=target, context=context,
                                     data=data))

    async def run(self) -> None:
        """Bucle principal: lee el buzon y llama al manejador de cada evento.

        Las subclases redefinen los manejadores (`on_start`, `on_cancel`),
        no este bucle. Los tipos de evento sin manejador se ignoran.

        Limitacion actual: el bucle espera a que `on_start` termine antes de
        leer el siguiente evento. Un CancelRequest que llegue durante el
        reconocimiento no se atiende hasta que este acaba, asi que el barge-in
        no es posible con esta estructura. Para incluirlo hay que reestructurarlo,
        por ejemplo lanzando `on_start` como tarea aparte
        (asyncio.create_task) y cancelandola desde `on_cancel`.
        """
        while True:
            ev = await self.mailbox.get()
            if ev.type is EventType.START_REQUEST:
                self._active = True
                await self.on_start(ev)
            elif ev.type is EventType.CANCEL_REQUEST:
                await self.on_cancel(ev)
            self.mailbox.task_done()
