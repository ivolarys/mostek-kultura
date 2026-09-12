"""Source registry: config `type` -> parser class."""

from __future__ import annotations

from .antee_rss import AnteeRssSource
from .base import Source
from .drupal_events import DrupalEventsSource
from .epo1_calendar import Epo1CalendarSource
from .galileo import GalileoSource
from .goout import GoOutSource
from .josefa_events import JosefaEventsSource
from .klaster_hostinne import KlasterHostinneSource
from .koruna_program import KorunaProgramSource
from .kultura_novapaka import KulturaNovaPakaSource
from .lodzie import LodzieSource
from .manual import ManualSource
from .mojekino import MojekinoSource
from .npu_events import NpuEventsSource
from .public4u import Public4uSource
from .simcal_calendar import SimcalCalendarSource
from .uffo import UffoSource
from .vismo import VismoSource
from .vismo6 import Vismo6Source
from .webnode_program import WebnodeProgramSource

REGISTRY: dict[str, type[Source]] = {
    "galileo": GalileoSource,
    "antee_rss": AnteeRssSource,
    "public4u": Public4uSource,
    "goout": GoOutSource,
    "drupal_events": DrupalEventsSource,
    "lodzie_program": LodzieSource,
    "npu_events": NpuEventsSource,
    "josefa_events": JosefaEventsSource,
    "vismo": VismoSource,
    "vismo6": Vismo6Source,
    "kultura_novapaka": KulturaNovaPakaSource,
    "uffo": UffoSource,
    "manual": ManualSource,
    "mojekino": MojekinoSource,
    "epo1_calendar": Epo1CalendarSource,
    "webnode_program": WebnodeProgramSource,
    "koruna_program": KorunaProgramSource,
    "simcal_calendar": SimcalCalendarSource,
    "klaster_hostinne": KlasterHostinneSource,
}


def make_source(cfg) -> Source:
    try:
        cls = REGISTRY[cfg.type]
    except KeyError as e:
        raise ValueError(f"unknown source type '{cfg.type}' for source '{cfg.name}'") from e
    return cls(cfg)
