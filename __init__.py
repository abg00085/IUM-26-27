"""Prototipo multimodal — esqueleto de la practica P1.

Arquitectura W3C MMI (Tema 1): un InteractionManager y varios ModalityComponent
que se comunican por un bus de eventos asincrono con carga util EMMA.
"""
from .events import Event, Emma, EventType
from .bus import EventBus
from .component import ModalityComponent
from .manager import InteractionManager

__all__ = ["Event", "Emma", "EventType", "EventBus",
           "ModalityComponent", "InteractionManager"]
