"""CineStar Hradec Králové public Craft GraphQL GET programme."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

from ..dates import local, today
from ..model import Event
from .base import Source, clean

log = logging.getLogger(__name__)

_API = "https://craft.cinestar.cz/api"
_EVENTS_QUERY = """query Q($site:[String!],$Start:[QueryArgument!],$Finish:[QueryArgument!]){scheduledEventsEntries(site:$site,Start:$Start,Finish:$Finish,orderBy:\"Start ASC\",limit:200){... on scheduledEvents_default_Entry{EventId:title Start Finish TitleId ObjectId Properties{Code Name} movieInCinemasAvailability{... on moviesInCinemasAvailability_default_Entry{TitleArray PictureUrl movie{... on movies_default_Entry{slug MovieId moviePoster{url}}}}}}}}"""
_EVENTS_PAGE_QUERY = """query Q($site:[String!],$Start:[QueryArgument!],$Finish:[QueryArgument!],$offset:Int){scheduledEventsEntries(site:$site,Start:$Start,Finish:$Finish,orderBy:\"Start ASC\",limit:200,offset:$offset){... on scheduledEvents_default_Entry{EventId:title Start Finish TitleId ObjectId Properties{Code Name} movieInCinemasAvailability{... on moviesInCinemasAvailability_default_Entry{TitleArray PictureUrl movie{... on movies_default_Entry{slug MovieId moviePoster{url}}}}}}}}"""
_HALLS_QUERY = """query Q($site:[String!]){cinemaHallsEntries(site:$site,limit:200){... on cinemaHalls_default_Entry{ObjectId Properties{Name Code}}}}"""


class CineStarSource(Source):
    def fetch(self, http) -> list[Event]:
        start, finish = today(), today() + timedelta(days=60)
        variables = {
            "site": ["hradec"], "Start": [f">= {start.isoformat()}"], "Finish": [f"< {finish.isoformat()}"],
        }
        events = self._entries(self._get_json(http, _EVENTS_QUERY, variables))
        offset = len(events)
        seen_ids = {str(item.get("EventId")) for item in events}
        while offset and offset % 200 == 0:
            page = self._entries(self._get_json(http, _EVENTS_PAGE_QUERY, {**variables, "offset": offset}))
            if not page:
                break
            page_ids = {str(item.get("EventId")) for item in page}
            if not page_ids - seen_ids:
                raise ValueError("CineStar GraphQL pagination repeated a page")
            events.extend(page)
            seen_ids.update(page_ids)
            offset += len(page)
        halls = self._get_json(http, _HALLS_QUERY, {"site": ["hradec"]})
        hall_names = self._hall_names(halls)
        out: list[Event] = []
        for item in events:
            try:
                event = self._parse(item, hall_names)
            except (KeyError, TypeError, ValueError) as exc:
                log.warning("%s: skipping malformed screening: %s", self.name, exc)
                continue
            if event:
                out.append(event)
        return out

    @staticmethod
    def _url(query: str, variables: dict) -> str:
        return f"{_API}?{urlencode({'query': query, 'variables': json.dumps(variables, separators=(',', ':'))})}"

    def _get_json(self, http, query: str, variables: dict) -> dict:
        data = http.get_json(self._url(query, variables))
        if not isinstance(data, dict) or data.get("errors") or not isinstance(data.get("data"), dict):
            raise ValueError("CineStar GraphQL returned errors or an invalid schema")
        return data

    @staticmethod
    def _entries(data: dict) -> list[dict]:
        entries = data["data"].get("scheduledEventsEntries")
        if not isinstance(entries, list):
            raise TypeError("CineStar GraphQL response lacks scheduledEventsEntries")
        return entries

    @staticmethod
    def _hall_names(data: dict) -> dict[str, str]:
        names: dict[str, str] = {}
        halls = data["data"].get("cinemaHallsEntries")
        if not isinstance(halls, list):
            raise TypeError("CineStar GraphQL response lacks cinemaHallsEntries")
        for hall in halls:
            if not isinstance(hall, dict):
                raise TypeError("CineStar GraphQL returned an invalid cinema hall")
            name = next((clean(p.get("Name")) for p in hall.get("Properties", []) if clean(p.get("Name"))), "")
            if name and hall.get("ObjectId"):
                names[str(hall["ObjectId"])] = name.title()
        return names

    def _parse(self, item: dict, hall_names: dict[str, str]) -> Event | None:
        availability = item.get("movieInCinemasAvailability") or []
        movie = availability[0] if availability else {}
        title = clean(movie.get("TitleArray"))
        start_s = item.get("Start")
        if not title or not start_s or not item.get("EventId"):
            return None
        start = local(datetime.fromisoformat(start_s))
        end = local(datetime.fromisoformat(item["Finish"])) if item.get("Finish") else None
        movie_detail = (movie.get("movie") or [{}])[0]
        slug = movie_detail.get("slug")
        url = f"https://cinestar.cz/cz/hradec/filmy/movie/{item['TitleId']}-{slug}" if slug else self.cfg.page_url
        poster = (movie_detail.get("moviePoster") or [{}])[0].get("url")
        hall = hall_names.get(str(item.get("ObjectId")))
        venue = f"CineStar Hradec Králové — {hall}" if hall else "CineStar Hradec Králové"
        return self.event(
            title=title, start=start, end=end, all_day=False, url=url, venue=venue,
            native_category="Film", image=poster, native_id=str(item["EventId"]), place_raw=self.cfg.place,
        )
