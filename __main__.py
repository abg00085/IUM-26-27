"""Autocomprobacion de P1: un ciclo MMI completo sobre un MC simulado.

    python -m prototype

Falla ruidosamente si el ciclo NewContextRequest -> StartRequest ->
DoneNotification no se completa o si la politica de confianza se rompe.
"""
from __future__ import annotations

import asyncio
import logging

from . import EventBus, Emma, Event, InteractionManager, ModalityComponent, EventType


class SimulatedComponent(ModalityComponent):
    """MC de prueba: al recibir StartRequest devuelve una interpretacion fija."""

    def __init__(self, name, bus, confidence: float):
        super().__init__(name, bus)
        self.confidence = confidence

    async def on_start(self, ev: Event) -> None:
        """Simula un reconocimiento y devuelve al IM una anotacion EMMA fija."""
        await asyncio.sleep(0.01)  # simula el coste del reconocedor
        emma = Emma(interpretation={"intent": "query_part", "ref": "A-14"},
                    confidence=self.confidence, modality=self.name,
                    start_ms=ev.timestamp_ms, end_ms=ev.timestamp_ms + 850)
        await self.emit(EventType.DONE_NOTIFICATION, ev.context, emma)


async def main() -> None:
    """Monta bus, IM y dos MC simulados, ejecuta un ciclo y lo comprueba."""
    logging.basicConfig(level=logging.INFO, format="%(name)-4s | %(message)s")
    bus = EventBus()
    im = InteractionManager(bus)
    voice = SimulatedComponent("voice", bus, confidence=0.91)
    gesture = SimulatedComponent("gesture", bus, confidence=0.55)

    # Cada componente es una tarea concurrente con su propio bucle de eventos
    tasks = [asyncio.create_task(t) for t in
             (bus.dispatch(), im.run(), voice.run(), gesture.run())]

    ctx = await im.new_context(["voice", "gesture"])
    await im.start("voice")
    await im.start("gesture")
    await asyncio.sleep(0.3)  # margen para que se procesen todos los eventos
    for t in tasks:
        t.cancel()

    # --- comprobaciones ---
    assert len(im.inputs) == 2, f"esperadas 2 entradas, hubo {len(im.inputs)}"
    assert im.decide(im.inputs[0]) == "implicit_confirm"
    assert im.decide(im.inputs[1]) == "explicit_confirm"
    types = [e.type for e in bus.trace]
    assert types.count(EventType.NEW_CONTEXT_REQUEST) == 2
    assert types.count(EventType.START_REQUEST) == 2
    assert types.count(EventType.DONE_NOTIFICATION) == 2

    # La ventana de fusion se estima en P3 sobre el corpus WoZ; 500 ms es
    # solo el valor de arranque.
    assert im.inputs[0].overlaps(im.inputs[1], window_ms=500)

    print(f"\nOK — contexto {ctx}: ciclo MMI completo, politica de confianza "
          f"y ventana de fusion verificadas sobre {len(bus.trace)} eventos.")


if __name__ == "__main__":
    asyncio.run(main())
