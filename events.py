"""Eventos del ciclo de vida MMI y carga util EMMA (Temas 1 y 2)."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum


class EventType(str, Enum):
    """Subconjunto del ciclo de vida MMI que usa el prototipo.

    El estandar define ademas Prepare, Pause y Resume. Se anaden cuando
    alguna practica los necesite.
    """
    NEW_CONTEXT_REQUEST = "NewContextRequest"
    NEW_CONTEXT_RESPONSE = "NewContextResponse"
    START_REQUEST = "StartRequest"
    START_RESPONSE = "StartResponse"
    DONE_NOTIFICATION = "DoneNotification"
    CANCEL_REQUEST = "CancelRequest"
    CLEAR_CONTEXT_REQUEST = "ClearContextRequest"
    EXTENSION_NOTIFICATION = "ExtensionNotification"


@dataclass
class Emma:
    """Interpretacion anotada de una entrada del usuario.

    Refleja los campos de EMMA que el prototipo necesita (Tema 2, parte II).
    `start_ms` y `end_ms` delimitan en el tiempo la senal que se interpreto;
    son los que permiten fusionar entradas de modalidades distintas.
    `alternatives` es la lista N-best: vacia cuando la interpretacion es unica.
    """
    interpretation: dict
    confidence: float
    modality: str
    start_ms: int
    end_ms: int
    alternatives: list[tuple[dict, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Valida la anotacion al crearla: confianza en [0,1] e intervalo coherente."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confianza fuera de [0,1]: {self.confidence}")
        if self.end_ms < self.start_ms:
            raise ValueError("end_ms anterior a start_ms")

    def overlaps(self, other: "Emma", window_ms: int) -> bool:
        """True si ambos eventos caen en la misma ventana temporal de fusion.

        La ventana es simetrica: solo compara los instantes de inicio y no
        tiene en cuenta que modalidad llega antes. En la practica el gesto
        deictico suele preceder a la palabra entre 100 y 500 ms (Tema 6); en el
        Hito 3 hay que sustituirla por una ventana asimetrica que lo recoja. El
        ancho se mide sobre el corpus WoZ de P3.
        """
        return abs(self.start_ms - other.start_ms) <= window_ms

    def dict(self) -> dict:
        """Devuelve la anotacion como diccionario, lista para serializar a JSON."""
        return asdict(self)


@dataclass
class Event:
    """Mensaje del bus. `source` y `target` son nombres de componente.

    `context` agrupa todos los eventos de una misma interaccion; `request_id`
    enlaza cada respuesta con la peticion que la provoco. `data` lleva la
    carga util: una anotacion EMMA en los resultados, un dict en el resto.
    """
    type: EventType
    source: str
    target: str
    context: str
    data: Emma | dict | None = None
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))

    def reply(self, type: EventType, data=None) -> "Event":
        """Construye la respuesta a este evento conservando peticion y contexto."""
        return Event(type=type, source=self.target, target=self.source,
                     context=self.context, data=data, request_id=self.request_id)
