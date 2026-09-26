"""조달청 나라장터 입찰공고정보서비스 연동.

공공데이터포털 조달청_나라장터 입찰공고정보서비스의 최신 /ad/ 경로를 사용한다.
현재 딸깍 용역계약에서는 '용역(servc)' 공고만 우선 지원한다.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx


DEFAULT_BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"

OP_SERVICE_NOTICE = "getBidPblancListInfoServc"
OP_SERVICE_BASIS = "getBidPblancListInfoServcBsisAmount"
OP_LICENSE_LIMIT = "getBidPblancListInfoLicenseLimit"
OP_REGION = "getBidPblancListInfoPrtcptPsblRgn"
OP_SERVICE_ITEMS = "getBidPblancListInfoServcPurchsObjPrdct"


class G2BAPIError(RuntimeError):
    pass


@dataclass(slots=True)
class G2BClientConfig:
    service_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 20.0


def _normalize_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    response = payload.get("response", payload)
    header = response.get("header") or {}
    result_code = str(header.get("resultCode", "00"))
    if result_code not in {"00", "0"}:
        raise G2BAPIError(
            f"나라장터 API 오류 {result_code}: {header.get('resultMsg', '알 수 없는 오류')}"
        )

    body = response.get("body") or {}
    items = body.get("items", [])
    if items is None:
        return []
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    if isinstance(items, dict):
        nested = items.get("item")
        if nested is None:
            return [items] if items else []
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
        if isinstance(nested, dict):
            return [nested]
    return []


def _number(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _first_text(items: list[dict[str, Any]], *keys: str) -> str:
    values: list[str] = []
    for item in items:
        for key in keys:
            value = item.get(key)
            if value not in (None, ""):
                text = str(value).strip()
                if text and text not in values:
                    values.append(text)
    return ", ".join(values)


class G2BClient:
    def __init__(
        self,
        config: G2BClientConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not config.service_key:
            raise ValueError("공공데이터포털 서비스키가 필요합니다.")
        self.config = config
        self.transport = transport

    async def _get_items(
        self,
        operation: str,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        query = {
            "serviceKey": self.config.service_key,
            "type": "json",
            "pageNo": 1,
            "numOfRows": 100,
            **params,
        }
        async with httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            transport=self.transport,
        ) as client:
            response = await client.get(
                f"{self.config.base_url.rstrip('/')}/{operation}",
                params=query,
            )
            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError as exc:
                raise G2BAPIError("나라장터 API가 JSON이 아닌 응답을 반환했습니다.") from exc
        return _normalize_items(payload)

    async def get_service_notice(self, bid_notice_no: str) -> dict[str, Any] | None:
        items = await self._get_items(
            OP_SERVICE_NOTICE,
            {"inqryDiv": "2", "bidNtceNo": bid_notice_no},
        )
        return items[0] if items else None

    async def get_service_basis_amount(self, bid_notice_no: str) -> list[dict[str, Any]]:
        return await self._get_items(
            OP_SERVICE_BASIS,
            {"inqryDiv": "2", "bidNtceNo": bid_notice_no},
        )

    async def get_eligibility(
        self,
        bid_notice_no: str,
        bid_notice_order: str = "000",
    ) -> dict[str, list[dict[str, Any]]]:
        common = {
            "inqryDiv": "2",
            "bidNtceNo": bid_notice_no,
            "bidNtceOrd": bid_notice_order or "000",
        }
        license_items, region_items = await asyncio.gather(
            self._get_items(OP_LICENSE_LIMIT, common),
            self._get_items(OP_REGION, common),
        )
        return {"license_limits": license_items, "regions": region_items}

    async def get_service_items(
        self,
        bid_notice_no: str,
        bid_notice_order: str = "000",
    ) -> list[dict[str, Any]]:
        return await self._get_items(
            OP_SERVICE_ITEMS,
            {
                "inqryDiv": "2",
                "bidNtceNo": bid_notice_no,
                "bidNtceOrd": bid_notice_order or "000",
            },
        )

    async def get_service_case(self, bid_notice_no: str) -> dict[str, Any]:
        notice = await self.get_service_notice(bid_notice_no)
        if not notice:
            return {
                "found": False,
                "bid_notice_no": bid_notice_no,
                "message": "용역 입찰공고를 찾지 못했습니다.",
            }

        order = str(notice.get("bidNtceOrd") or "000")
        basis, eligibility, items = await asyncio.gather(
            self.get_service_basis_amount(bid_notice_no),
            self.get_eligibility(bid_notice_no, order),
            self.get_service_items(bid_notice_no, order),
        )

        basis_first = basis[0] if basis else {}
        license_items = eligibility["license_limits"]
        region_items = eligibility["regions"]

        estimated_price = _number(notice.get("presmptPrce"))
        base_amount = _number(basis_first.get("bssamt"))
        evaluation_base_amount = _number(basis_first.get("evlBssAmt"))

        detail_items = []
        for item in items:
            detail_items.append(
                {
                    "product_name": item.get("prdctClsfcNoNm"),
                    "detail_product_name": item.get("dtilPrdctClsfcNoNm"),
                    "quantity": item.get("qty"),
                    "unit": item.get("unit"),
                    "unit_price": _number(item.get("uprc")),
                    "delivery_place": item.get("dlvrPlce"),
                }
            )

        region_text = _first_text(
            region_items,
            "prtcptPsblRgnNm",
            "prtcptLmtRgnNm",
        ) or str(notice.get("prtcptLmtRgnNm") or "").strip()

        result = {
            "found": True,
            "bid_notice_no": str(notice.get("bidNtceNo") or bid_notice_no),
            "bid_notice_order": order,
            "bid_notice_name": notice.get("bidNtceNm"),
            "notice_institution": notice.get("ntceInsttNm"),
            "demand_institution": notice.get("dminsttNm"),
            "notice_datetime": notice.get("bidNtceDt"),
            "bid_begin_datetime": notice.get("bidBeginDt"),
            "bid_close_datetime": notice.get("bidClseDt"),
            "open_datetime": notice.get("opengDt"),
            "estimated_price": estimated_price,
            "base_amount": base_amount,
            "evaluation_base_amount": evaluation_base_amount,
            "reserve_rate_min": basis_first.get("rsrvtnPrceRngBgnRate"),
            "reserve_rate_max": basis_first.get("rsrvtnPrceRngEndRate"),
            "bid_method": notice.get("bidMethdNm"),
            "contract_method": notice.get("cntrctCnclsMthdNm"),
            "joint_supply_method": notice.get("cmmnSpldmdMethdNm"),
            "region_limit": region_text,
            "license_limits": [
                {
                    "name": item.get("lcnsLmtNm"),
                    "allowed_industries": item.get("permsnIndstrytyList"),
                }
                for item in license_items
            ],
            "items": detail_items,
            "detail_url": notice.get("bidNtceDtlUrl") or notice.get("bidNtceUrl"),
            "raw": {
                "notice": notice,
                "basis": basis,
                "eligibility": eligibility,
                "items": items,
            },
        }
        result["autofill"] = {
            "service_name": result["bid_notice_name"] or "",
            "estimated_price": estimated_price,
            "base_amount": base_amount,
            "region_restriction_text": region_text,
            "bid_start": result["bid_begin_datetime"] or "",
            "bid_end": result["bid_close_datetime"] or "",
            "bid_open": result["open_datetime"] or "",
        }
        return result
