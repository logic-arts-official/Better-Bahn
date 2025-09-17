"""
v6.db.transport.rest API Client for Better-Bahn

Resilient Python client for real-time Deutsche Bahn data via v6.db.transport.rest.
Includes error handling, token-bucket rate limiting, in-memory caching with ETag and
stale-while-revalidate, and graceful fallbacks.

API Docs: https://v6.db.transport.rest/api.html
"""

from __future__ import annotations

import json
import time
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import quote

import hashlib
import requests


# ---------- Result types ----------

class APIResultType(Enum):
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    UPSTREAM_ERROR = "upstream_error"
    TRANSIENT_ERROR = "transient_error"
    PERMANENT_ERROR = "permanent_error"


@dataclass
class APIResult:
    result_type: APIResultType
    data: Optional[Any] = None
    error_message: Optional[str] = None
    http_status: Optional[int] = None
    retry_after: Optional[int] = None
    from_cache: bool = False
    cached_at: Optional[float] = None

    @property
    def is_success(self) -> bool:
        return self.result_type == APIResultType.SUCCESS

    @property
    def should_retry(self) -> bool:
        return self.result_type in {
            APIResultType.RATE_LIMITED,
            APIResultType.TRANSIENT_ERROR,
            APIResultType.UPSTREAM_ERROR,
        }

    @property
    def can_fallback_to_cache(self) -> bool:
        return self.result_type in {
            APIResultType.RATE_LIMITED,
            APIResultType.UPSTREAM_ERROR,
            APIResultType.TRANSIENT_ERROR,
        }


# ---------- Cache ----------

@dataclass
class CacheEntry:
    data: Any
    fetched_at: float
    etag: Optional[str] = None
    max_age: int = 300
    stale_while_revalidate: int = 600

    @property
    def is_fresh(self) -> bool:
        return time.time() - self.fetched_at < self.max_age

    @property
    def is_stale_but_usable(self) -> bool:
        return time.time() - self.fetched_at < (self.max_age + self.stale_while_revalidate)


class CacheManager:
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = threading.Lock()

    def _generate_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        if params:
            param_str = json.dumps(params, sort_keys=True, separators=(",", ":"))
            key_data = f"{endpoint}?{param_str}"
        else:
            key_data = endpoint
        return hashlib.md5(key_data.encode("utf-8")).hexdigest()

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Tuple[Optional[CacheEntry], str]:
        key = self._generate_key(endpoint, params)
        with self._lock:
            self._access_times[key] = time.time()
            return self._cache.get(key), key

    def set(self, key: str, entry: CacheEntry) -> None:
        with self._lock:
            if len(self._cache) >= self.max_size and key not in self._cache:
                oldest_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
                self._cache.pop(oldest_key, None)
                self._access_times.pop(oldest_key, None)
            self._cache[key] = entry
            self._access_times[key] = time.time()

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._access_times.clear()


# ---------- Rate limiting ----------

class TokenBucket:
    def __init__(self, capacity: int = 10, refill_rate: float = 1.0):
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.refill_rate = float(refill_rate)
        self.last_update = time.time()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        with self._lock:
            now = time.time()
            self.tokens = min(self.capacity, self.tokens + (now - self.last_update) * self.refill_rate)
            self.last_update = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def time_until_available(self, tokens: int = 1) -> float:
        with self._lock:
            if self.tokens >= tokens:
                return 0.0
            needed = tokens - self.tokens
            return needed / self.refill_rate if self.refill_rate > 0 else float("inf")


def _bool_to_str(v: Optional[bool]) -> Optional[str]:
    if v is None:
        return None
    return "true" if v else "false"


# ---------- Client ----------

class DBTransportAPIClient:
    BASE_URL = "https://v6.db.transport.rest"

    def __init__(
        self,
        rate_limit_capacity: int = 10,
        rate_limit_window: float = 10.0,
        cache_max_size: int = 1000,
        default_timeout: int = 30,
        enable_caching: bool = True,
        user_agent: str = "Better-Bahn/2.0 (+https://github.com/logic-arts-official/Better-Bahn)",
    ):
        refill_rate = rate_limit_capacity / rate_limit_window if rate_limit_window > 0 else rate_limit_capacity
        self.rate_limiter = TokenBucket(capacity=rate_limit_capacity, refill_rate=refill_rate)
        self.cache_manager = CacheManager(max_size=cache_max_size) if enable_caching else None

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent, "Accept": "application/json"})
        self.default_timeout = default_timeout

        self.stats = {
            "requests_made": 0,
            "cache_hits": 0,
            "rate_limit_hits": 0,
            "errors": 0,
        }

    # ---- internals ----

    def _map_http_status_to_result_type(self, status_code: int) -> APIResultType:
        if 200 <= status_code < 300:
            return APIResultType.SUCCESS
        if status_code == 404:
            return APIResultType.NOT_FOUND
        if status_code == 429:
            return APIResultType.RATE_LIMITED
        if 400 <= status_code < 500:
            return APIResultType.PERMANENT_ERROR
        if 500 <= status_code < 600:
            return APIResultType.UPSTREAM_ERROR
        return APIResultType.TRANSIENT_ERROR

    def _extract_rate_limit_info(self, response: requests.Response) -> Optional[int]:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                pass
        x_reset = response.headers.get("X-RateLimit-Reset")
        if x_reset:
            try:
                reset_time = int(x_reset)
                return max(0, reset_time - int(time.time()))
            except ValueError:
                pass
        return None

    def _make_request_with_cache(self, endpoint: str, params: Optional[Dict] = None) -> APIResult:
        self.stats["requests_made"] += 1

        cache_entry: Optional[CacheEntry] = None
        cache_key: Optional[str] = None
        if self.cache_manager:
            cache_entry, cache_key = self.cache_manager.get(endpoint, params)
            if cache_entry and cache_entry.is_fresh:
                self.stats["cache_hits"] += 1
                return APIResult(
                    result_type=APIResultType.SUCCESS,
                    data=cache_entry.data,
                    from_cache=True,
                    cached_at=cache_entry.fetched_at,
                    http_status=200,
                )

        if not self.rate_limiter.consume():
            self.stats["rate_limit_hits"] += 1
            wait_time = self.rate_limiter.time_until_available()
            if cache_entry and cache_entry.is_stale_but_usable:
                self.stats["cache_hits"] += 1
                return APIResult(
                    result_type=APIResultType.SUCCESS,
                    data=cache_entry.data,
                    from_cache=True,
                    cached_at=cache_entry.fetched_at,
                    http_status=200,
                )
            return APIResult(
                result_type=APIResultType.RATE_LIMITED,
                error_message=f"Rate limit exceeded, retry in {wait_time:.1f}s",
                retry_after=int(wait_time) + 1,
            )

        headers: Dict[str, str] = {}
        if cache_entry and cache_entry.etag:
            headers["If-None-Match"] = cache_entry.etag

        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params, headers=headers, timeout=self.default_timeout)

            if response.status_code == 304 and cache_entry:
                fresh_entry = CacheEntry(data=cache_entry.data, fetched_at=time.time(), etag=cache_entry.etag)
                if self.cache_manager and cache_key:
                    self.cache_manager.set(cache_key, fresh_entry)
                return APIResult(
                    result_type=APIResultType.SUCCESS,
                    data=cache_entry.data,
                    from_cache=True,
                    cached_at=fresh_entry.fetched_at,
                    http_status=200,
                )

            result_type = self._map_http_status_to_result_type(response.status_code)

            if result_type == APIResultType.SUCCESS:
                try:
                    data = response.json()
                except ValueError as e:
                    self.stats["errors"] += 1
                    return APIResult(
                        result_type=APIResultType.TRANSIENT_ERROR,
                        error_message=f"Invalid JSON response: {e}",
                        http_status=response.status_code,
                    )

                if self.cache_manager and cache_key:
                    etag = response.headers.get("ETag")
                    self.cache_manager.set(cache_key, CacheEntry(data=data, fetched_at=time.time(), etag=etag))

                return APIResult(
                    result_type=APIResultType.SUCCESS,
                    data=data,
                    http_status=response.status_code,
                    from_cache=False,
                )

            # errors
            self.stats["errors"] += 1
            retry_after = self._extract_rate_limit_info(response) if result_type == APIResultType.RATE_LIMITED else None

            if cache_entry and cache_entry.is_stale_but_usable and result_type in {
                APIResultType.RATE_LIMITED,
                APIResultType.UPSTREAM_ERROR,
                APIResultType.TRANSIENT_ERROR,
            }:
                return APIResult(
                    result_type=APIResultType.SUCCESS,
                    data=cache_entry.data,
                    from_cache=True,
                    cached_at=cache_entry.fetched_at,
                    http_status=200,
                )

            try:
                error_details = response.text[:500]
            except Exception:
                error_details = f"HTTP {response.status_code}"

            return APIResult(
                result_type=result_type,
                error_message=f"API error: {error_details}",
                http_status=response.status_code,
                retry_after=retry_after,
            )

        except requests.Timeout:
            self.stats["errors"] += 1
            if cache_entry and cache_entry.is_stale_but_usable:
                return APIResult(
                    result_type=APIResultType.SUCCESS,
                    data=cache_entry.data,
                    from_cache=True,
                    cached_at=cache_entry.fetched_at,
                    http_status=200,
                )
            return APIResult(result_type=APIResultType.TRANSIENT_ERROR, error_message="Request timeout")

        except requests.ConnectionError:
            self.stats["errors"] += 1
            if cache_entry and cache_entry.is_stale_but_usable:
                return APIResult(
                    result_type=APIResultType.SUCCESS,
                    data=cache_entry.data,
                    from_cache=True,
                    cached_at=cache_entry.fetched_at,
                    http_status=200,
                )
            return APIResult(result_type=APIResultType.TRANSIENT_ERROR, error_message="Connection error")

        except requests.RequestException as e:
            self.stats["errors"] += 1
            return APIResult(result_type=APIResultType.TRANSIENT_ERROR, error_message=f"Request failed: {e}")

    # ---- legacy compatibility thin wrapper (Optional[Any]) ----

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Any]:
        result = self._make_request_with_cache(endpoint, params)
        return result.data if result.is_success else None

    # ---- public resilient methods ----

    def find_locations_resilient(self, query: str, results: int = 5) -> APIResult:
        params = {"query": query, "results": results}
        return self._make_request_with_cache("/locations", params)

    def get_journeys_resilient(
        self,
        from_station: str,
        to_station: str,
        departure: Optional[str] = None,
        arrival: Optional[str] = None,
        results: int = 3,
        stopovers: bool = True,
        transfers: int = -1,
        accessibility: Optional[str] = None,
    ) -> APIResult:
        params: Dict[str, Union[str, int]] = {
            "from": from_station,
            "to": to_station,
            "results": results,
            "stopovers": _bool_to_str(stopovers) or "true",
        }
        if departure:
            params["departure"] = departure
        if arrival:
            params["arrival"] = arrival
        if transfers >= 0:
            params["transfers"] = transfers
        if accessibility:
            params["accessibility"] = accessibility
        return self._make_request_with_cache("/journeys", params)

    def get_departures_resilient(
        self, station_id: str, when: Optional[str] = None, duration: int = 120, results: int = 10
    ) -> APIResult:
        endpoint = f"/stops/{quote(station_id)}/departures"
        params: Dict[str, Union[str, int]] = {"duration": duration, "results": results}
        if when:
            params["when"] = when
        return self._make_request_with_cache(endpoint, params)

    def get_trip_details_resilient(self, trip_id: str, line_name: Optional[str] = None) -> APIResult:
        endpoint = f"/trips/{quote(trip_id)}"
        params: Dict[str, str] = {}
        if line_name:
            params["lineName"] = line_name
        return self._make_request_with_cache(endpoint, params if params else None)

    # ---- simple Optional-returning helpers ----

    def find_locations(self, query: str, results: int = 5) -> Optional[List[Dict]]:
        result = self.find_locations_resilient(query, results)
        return result.data if result.is_success else None

    def get_journeys(
        self,
        from_station: str,
        to_station: str,
        departure: Optional[str] = None,
        arrival: Optional[str] = None,
        results: int = 3,
        stopovers: bool = True,
        transfers: int = -1,
        accessibility: Optional[str] = None,
    ) -> Optional[Dict]:
        result = self.get_journeys_resilient(
            from_station, to_station, departure, arrival, results, stopovers, transfers, accessibility
        )
        return result.data if result.is_success else None

    def get_departures(
        self, station_id: str, when: Optional[str] = None, duration: int = 120, results: int = 10
    ) -> Optional[Dict]:
        result = self.get_departures_resilient(station_id, when, duration, results)
        return result.data if result.is_success else None

    def get_arrivals(
        self, station_id: str, when: Optional[str] = None, duration: int = 120, results: int = 10
    ) -> Optional[Dict]:
        endpoint = f"/stops/{quote(station_id)}/arrivals"
        params: Dict[str, Union[str, int]] = {"duration": duration, "results": results}
        if when:
            params["when"] = when
        return self._make_request(endpoint, params)

    def get_trip_details(self, trip_id: str, line_name: Optional[str] = None) -> Optional[Dict]:
        result = self.get_trip_details_resilient(trip_id, line_name)
        return result.data if result.is_success else None

    def get_station_info(self, station_id: str) -> Optional[Dict]:
        endpoint = f"/stops/{quote(station_id)}"
        return self._make_request(endpoint)

    def find_nearby_stations(
        self, latitude: float, longitude: float, distance: int = 1000, results: int = 8
    ) -> Optional[List[Dict]]:
        params = {"latitude": latitude, "longitude": longitude, "distance": distance, "results": results}
        return self._make_request("/stops/nearby", params)

    # ---- utilities ----

    def get_stats(self) -> Dict[str, Any]:
        cache_stats = {}
        if self.cache_manager:
            cache_stats = {"cache_size": len(self.cache_manager._cache), "cache_max_size": self.cache_manager.max_size}
        return {
            **self.stats,
            **cache_stats,
            "rate_limit_tokens": self.rate_limiter.tokens,
            "rate_limit_capacity": self.rate_limiter.capacity,
        }

    def clear_cache(self) -> None:
        if self.cache_manager:
            self.cache_manager.clear()

    def reset_stats(self) -> None:
        self.stats = {"requests_made": 0, "cache_hits": 0, "rate_limit_hits": 0, "errors": 0}

    def get_real_time_status(self, journey_data: Dict) -> Dict:
        status = {"has_delays": False, "total_delay_minutes": 0, "cancelled_legs": 0, "delays_by_leg": []}
        if not journey_data or "legs" not in journey_data:
            return status
        for leg in journey_data["legs"]:
            leg_status = {"leg_id": leg.get("id", "unknown"), "departure_delay": 0, "arrival_delay": 0, "cancelled": False}
            dep = leg.get("departure") or {}
            arr = leg.get("arrival") or {}
            if dep.get("delay") is not None:
                dep_min = dep["delay"] // 60
                leg_status["departure_delay"] = dep_min
                status["total_delay_minutes"] += max(dep_min, 0)
                if dep_min > 0:
                    status["has_delays"] = True
            if arr.get("delay") is not None:
                arr_min = arr["delay"] // 60
                leg_status["arrival_delay"] = arr_min
                additional = max(arr_min - leg_status["departure_delay"], 0)
                status["total_delay_minutes"] += additional
                if additional > 0:
                    status["has_delays"] = True
            if leg.get("cancelled"):
                leg_status["cancelled"] = True
                status["cancelled_legs"] += 1
            status["delays_by_leg"].append(leg_status)
        return status


# ---------- High-level helper ----------

def get_real_time_journey_info(from_station: str, to_station: str) -> Dict[str, Any]:
    client = DBTransportAPIClient()
    journey_result = client.get_journeys_resilient(from_station, to_station, results=5)
    if not journey_result.is_success:
        return {
            "available": False,
            "error": journey_result.error_message or f"HTTP {journey_result.http_status}",
            "journeys": [],
            "journeys_count": 0,
            "from_station": from_station,
            "to_station": to_station,
        }

    data = journey_result.data or {}
    journeys = data.get("journeys", []) if isinstance(data, dict) else []
    processed: List[Dict[str, Any]] = []
    for j in journeys:
        rt = client.get_real_time_status(j)
        processed.append(
            {
                "duration_minutes": (j.get("duration", 0) // 60) if isinstance(j.get("duration"), int) else 0,
                "transfers": max(len(j.get("legs", [])) - 1, 0),
                "real_time_status": {
                    "has_delays": rt["has_delays"],
                    "total_delay_minutes": rt["total_delay_minutes"],
                    "has_cancellations": rt["cancelled_legs"] > 0,
                    "status": "disrupted" if (rt["has_delays"] or rt["cancelled_legs"] > 0) else "on_time",
                },
            }
        )

    return {
        "available": True,
        "journeys": processed,
        "journeys_count": len(processed),
        "from_station": from_station,
        "to_station": to_station,
    }


# ---------- Self-test ----------

def _self_test() -> None:
    print("DB Transport API Client smoke test")
    client = DBTransportAPIClient()

    print("\nStats initial:", client.get_stats())

    print("\n1) Locations 'Berlin Hbf'...")
    r = client.find_locations_resilient("Berlin Hbf", results=1)
    print("  type=", r.result_type.value, " cache=", r.from_cache)
    if r.is_success and isinstance(r.data, list) and r.data:
        berlin_id = r.data[0].get("id") or r.data[0].get("station", {}).get("id")
        name = r.data[0].get("name")
        print(f"  Found: {name} (ID: {berlin_id})")

        print("\n2) Journeys Berlin -> München...")
        j = client.get_journeys_resilient(str(berlin_id), "8000261", results=1)
        print("  type=", j.result_type.value, " cache=", j.from_cache)
        journeys = (j.data or {}).get("journeys", []) if j.is_success else []
        if journeys:
            status = client.get_real_time_status(journeys[0])
            print("  Delays:", status["has_delays"], " total_min=", status["total_delay_minutes"])

    print("\n3) Rate limit probe...")
    for i in range(15):
        r = client.find_locations_resilient("Hamburg", results=1)
        if r.result_type == APIResultType.RATE_LIMITED:
            print(f"  Rate limit hit after {i+1} calls; retry_after={r.retry_after}s")
            break

    print("\n4) Cache behavior...")
    r1 = client.find_locations_resilient("Frankfurt", results=1)
    r2 = client.find_locations_resilient("Frankfurt", results=1)
    print("  req1 from_cache=", r1.from_cache, " | req2 from_cache=", r2.from_cache)

    print("\nStats final:", client.get_stats())


if __name__ == "__main__":
    _self_test()
