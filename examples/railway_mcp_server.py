"""철도 정보 MCP 서버 (가이드 08장 예시).

네 개의 Tool을 제공합니다.
    - list_stations          : 관리 중인 모든 역 반환
    - get_station_info       : 역 이름으로 역 상세 정보 조회
    - distance_between       : 두 역 사이의 직선 거리(km) 계산
    - find_trains            : 출발/도착역에 대한 가상의 열차 시간표 조회

이 파일은 교육용이며, 실제 API 연결 없이 하드코딩된 샘플 데이터로 동작합니다.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Literal

from pydantic import BaseModel, Field

from fastmcp import FastMCP


# ---------------------------------------------------------------------------
# 1) 모델 정의 (Pydantic BaseModel)
# ---------------------------------------------------------------------------
class Station(BaseModel):
    """역 정보."""

    name: str = Field(description="역 이름")
    line: int = Field(description="호선 번호")
    is_transfer: bool = Field(description="환승역 여부")
    lat: float = Field(description="위도")
    lng: float = Field(description="경도")


class Train(BaseModel):
    """열차 운행 정보."""

    train_no: str = Field(description="열차 번호")
    departure: str = Field(description="출발역 이름")
    arrival: str = Field(description="도착역 이름")
    depart_time: str = Field(description="출발 시각(HH:MM)")
    arrive_time: str = Field(description="도착 시각(HH:MM)")
    duration_min: int = Field(description="총 소요 시간(분)")


class DistanceResult(BaseModel):
    """두 역 사이 거리 계산 결과."""

    departure: str
    arrival: str
    distance_km: float = Field(description="직선 거리(킬로미터)")


# ---------------------------------------------------------------------------
# 2) 샘플 데이터 (서울 지하철 1·2호선 일부를 단순화)
# ---------------------------------------------------------------------------
STATIONS: dict[str, Station] = {
    "서울역":   Station(name="서울역",   line=1, is_transfer=True,  lat=37.5547, lng=126.9707),
    "시청":     Station(name="시청",     line=1, is_transfer=True,  lat=37.5640, lng=126.9770),
    "종각":     Station(name="종각",     line=1, is_transfer=False, lat=37.5703, lng=126.9829),
    "종로3가":  Station(name="종로3가",  line=1, is_transfer=True,  lat=37.5714, lng=126.9919),
    "동대문":   Station(name="동대문",   line=1, is_transfer=True,  lat=37.5713, lng=127.0094),
    "강남":     Station(name="강남",     line=2, is_transfer=False, lat=37.4980, lng=127.0276),
    "역삼":     Station(name="역삼",     line=2, is_transfer=False, lat=37.5006, lng=127.0366),
    "잠실":     Station(name="잠실",     line=2, is_transfer=True,  lat=37.5133, lng=127.1000),
    "홍대입구": Station(name="홍대입구", line=2, is_transfer=True,  lat=37.5572, lng=126.9240),
    "신촌":     Station(name="신촌",     line=2, is_transfer=False, lat=37.5550, lng=126.9368),
}

TRAINS: list[Train] = [
    Train(train_no="KTX-001", departure="서울역", arrival="강남",   depart_time="08:00", arrive_time="08:35", duration_min=35),
    Train(train_no="KTX-003", departure="서울역", arrival="강남",   depart_time="09:00", arrive_time="09:36", duration_min=36),
    Train(train_no="ITX-110", departure="서울역", arrival="잠실",   depart_time="08:15", arrive_time="09:10", duration_min=55),
    Train(train_no="SRT-205", departure="시청",   arrival="잠실",   depart_time="08:30", arrive_time="09:20", duration_min=50),
    Train(train_no="LOC-301", departure="종각",   arrival="동대문", depart_time="08:10", arrive_time="08:18", duration_min=8),
    Train(train_no="LOC-302", departure="동대문", arrival="종각",   depart_time="09:00", arrive_time="09:08", duration_min=8),
    Train(train_no="EXP-401", departure="홍대입구", arrival="강남", depart_time="08:05", arrive_time="08:38", duration_min=33),
    Train(train_no="EXP-402", departure="강남",   arrival="홍대입구", depart_time="18:05", arrive_time="18:40", duration_min=35),
]


# ---------------------------------------------------------------------------
# 3) 순수 함수(코어 로직) — Tool 바깥에서도 재사용 가능
# ---------------------------------------------------------------------------
def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """위·경도를 받아 지표 위 직선 거리(km)를 돌려주는 순수 함수."""
    earth_radius_km = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * earth_radius_km * asin(sqrt(a))


def _normalize_station(name: str) -> str:
    """사용자가 부르는 다양한 표기를 STATIONS의 키로 정규화.

    예) '강남역' → '강남', '서울' → '서울역'.
    LLM이 자연스럽게 보내는 두 가지 변형('역' 접미사 유무)을 모두 받아
    데이터의 키와 매칭시킨다.

    Raises:
        ValueError: 어느 형태로도 매칭되지 않을 때. 메시지에는 유효한 역
            목록을 함께 노출해 LLM이 다음 시도에서 자가복구할 수 있게 한다.
    """
    if name in STATIONS:
        return name
    if name.endswith("역") and name[:-1] in STATIONS:
        return name[:-1]
    if (name + "역") in STATIONS:
        return name + "역"
    available = ", ".join(STATIONS.keys())
    raise ValueError(
        f"'{name}' 역은 이 서비스가 관리하는 역 목록에 없습니다. "
        f"가능한 역: {available}"
    )


# ---------------------------------------------------------------------------
# 4) MCP 서버 인스턴스 + Tool 정의
# ---------------------------------------------------------------------------
mcp = FastMCP("railway-info")


@mcp.tool
def list_stations(line: int | None = None) -> list[Station]:
    """등록된 역 목록을 반환합니다.

    Args:
        line: 지정하면 해당 호선의 역만 필터링. 생략하면 전체 반환.

    Returns:
        Station 객체의 리스트.
    """
    stations = list(STATIONS.values())
    if line is not None:
        stations = [s for s in stations if s.line == line]
    return stations


@mcp.tool
def get_station_info(name: str) -> Station:
    """역 이름으로 역 상세 정보를 조회합니다.

    역 이름은 '강남' / '강남역' 둘 다 받습니다('역' 접미사 유무 무관).
    어떤 역이 등록되어 있는지 확신이 없다면 먼저 list_stations()를 호출하세요.

    Args:
        name: 조회할 역의 한글 이름(예: "강남" 또는 "강남역").

    Returns:
        일치하는 Station 객체.

    Raises:
        ValueError: 등록되지 않은 역 이름을 전달한 경우. 오류 메시지에
            가능한 역 목록이 함께 포함됩니다.
    """
    key = _normalize_station(name)
    return STATIONS[key]


@mcp.tool
def distance_between(station_a: str, station_b: str) -> DistanceResult:
    """두 역 사이의 직선 거리(km)를 계산합니다.

    역 이름은 '강남' / '강남역' 둘 다 받습니다('역' 접미사 유무 무관).

    Args:
        station_a: 첫 번째 역 이름.
        station_b: 두 번째 역 이름.

    Returns:
        거리 정보(DistanceResult). departure/arrival 필드에는 정규화된
        역 이름이 들어갑니다.

    Raises:
        ValueError: 둘 중 하나라도 등록되지 않은 역인 경우.
    """
    key_a = _normalize_station(station_a)
    key_b = _normalize_station(station_b)
    a = STATIONS[key_a]
    b = STATIONS[key_b]
    km = _haversine_km(a.lat, a.lng, b.lat, b.lng)
    return DistanceResult(
        departure=key_a,
        arrival=key_b,
        distance_km=round(km, 3),
    )


@mcp.tool
def find_trains(
    departure: str,
    arrival: str,
    sort_by: Literal["depart_time", "duration_min"] = "depart_time",
) -> list[Train]:
    """출발역과 도착역이 일치하는 열차 시간표를 조회합니다.

    역 이름은 '강남' / '강남역' 둘 다 받습니다('역' 접미사 유무 무관).
    "가장 빠른 열차"를 묻는 질문이라면 sort_by="duration_min"으로 호출하세요
    (기본값 'depart_time'은 가장 일찍 출발하는 순입니다).

    Args:
        departure: 출발역 이름.
        arrival: 도착역 이름.
        sort_by: 결과 정렬 기준. 'depart_time'(가장 일찍 출발 순) 또는
            'duration_min'(가장 빠르게 도착 순).

    Returns:
        조건에 맞는 Train 객체 리스트. 일치 항목이 없으면 빈 리스트.

    Raises:
        ValueError: 출발/도착역 중 하나라도 등록되지 않은 역인 경우.
    """
    dep = _normalize_station(departure)
    arr = _normalize_station(arrival)
    results = [t for t in TRAINS if t.departure == dep and t.arrival == arr]
    results.sort(key=lambda t: getattr(t, sort_by))
    return results


# ---------------------------------------------------------------------------
# 5) 엔트리 포인트
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
