"""Interaction Manager (Tema 1).

En P4 su logica condicional se sustituye por una maquina de estados explicita
derivada del modelo CTT de P3. Aqui solo mantiene contexto y reparte eventos.
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from .bus import EventBus
from .events import Emma, Event, EventType

log = logging.getLogger("IM")

# umbrales provisionales. Se recalibran en  con el WER medido
# sobre el corpus del grupo; elegirlos a ojo es exactamente lo que la
# practica pide no hacer.
C_MIN, C_MAX = 0.40, 0.80


class InteractionManager:
    """Coordinador de la interaccion: abre contextos, arranca los MC y recoge
    sus resultados. Es el unico componente que conoce a los demas.
    """

    def __init__(self, bus: EventBus, name: str = "IM") -> None:
        self.name = name
        self.bus = bus
        self.mailbox = bus.register(name)
        self.components: list[str] = []    # MC que participan en el contexto
        self.context: str | None = None    # identificador del contexto abierto
        self.inputs: list[Emma] = []       # interpretaciones recibidas, en orden

    async def new_context(self, components: list[str]) -> str:
        """Abre un contexto nuevo y lo notifica a cada MC participante.

        Devuelve el identificador del contexto.
        """
        self.context = uuid.uuid4().hex[:8]
        self.components = list(components)
        for mc in self.components:
            await self.bus.publish(Event(
                type=EventType.NEW_CONTEXT_REQUEST, source=self.name,
                target=mc, context=self.context))
        return self.context

    async def start(self, mc: str, data: dict | None = None) -> None:
        """Pide a un MC que empiece a trabajar dentro del contexto actual.

        `data` permite pasarle parametros, por ejemplo una gramatica o un prompt.
        """
        await self.bus.publish(Event(
            type=EventType.START_REQUEST, source=self.name, target=mc,
            context=self.context, data=data))

    def decide(self, emma: Emma) -> str:
        """Politica de confirmacion por umbral de confianza (Tema 2, parte III).

        Por debajo de C_MIN se rechaza la entrada (reject), entre C_MIN y C_MAX
        se pide confirmacion explicita (explicit_confirm) y por encima se
        confirma de forma implicita (implicit_confirm).
        """
        if emma.confidence < C_MIN:
            return "reject"
        if emma.confidence < C_MAX:
            return "explicit_confirm"
        return "implicit_confirm"

    async def run(self) -> None:
        """Bucle principal: recoge los resultados EMMA de los MC y decide.

        De momento solo atiende DoneNotification; el resto de eventos se ignora.
        """
        while True:
            ev = await self.mailbox.get()
            if ev.type is EventType.DONE_NOTIFICATION and isinstance(ev.data, Emma):
                self.inputs.append(ev.data)
                action = self.decide(ev.data)
                log.info("entrada de %s conf=%.2f -> %s",
                         ev.data.modality, ev.data.confidence, action)
            self.mailbox.task_done()
