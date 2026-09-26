import asyncio

import httpx

from app.services.g2b import G2BClient, G2BClientConfig


def payload(items):
    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
            "body": {"items": items, "totalCount": len(items)},
        }
    }


def test_g2b_service_case_merges_notice_basis_eligibility_and_items():
    def handler(request: httpx.Request) -> httpx.Response:
        op = request.url.path.rsplit("/", 1)[-1]
        if op == "getBidPblancListInfoServc":
            return httpx.Response(200, json=payload([{
                "bidNtceNo": "R26BK01234567",
                "bidNtceOrd": "000",
                "bidNtceNm": "2027학년도 ○○초등학교 통학차량 임차용역",
                "ntceInsttNm": "○○초등학교",
                "dminsttNm": "○○초등학교",
                "bidNtceDt": "2026-09-26 10:00:00",
                "bidBeginDt": "2026-10-01 10:00:00",
                "bidClseDt": "2026-10-07 10:00:00",
                "opengDt": "2026-10-07 11:00:00",
                "presmptPrce": "45000000",
                "bidMethdNm": "전자입찰",
                "cntrctCnclsMthdNm": "총액계약",
                "bidNtceDtlUrl": "https://example.test/notice",
            }]))
        if op == "getBidPblancListInfoServcBsisAmount":
            return httpx.Response(200, json=payload([{
                "bssamt": "49500000",
                "evlBssAmt": "45000000",
                "rsrvtnPrceRngBgnRate": "-3",
                "rsrvtnPrceRngEndRate": "3",
            }]))
        if op == "getBidPblancListInfoLicenseLimit":
            return httpx.Response(200, json=payload([{
                "lcnsLmtNm": "여객자동차운송사업(전세버스)",
                "permsnIndstrytyList": "5805",
            }]))
        if op == "getBidPblancListInfoPrtcptPsblRgn":
            return httpx.Response(200, json=payload([{
                "prtcptPsblRgnNm": "충청남도",
            }]))
        if op == "getBidPblancListInfoServcPurchsObjPrdct":
            return httpx.Response(200, json=payload([{
                "prdctClsfcNoNm": "도로여객운송서비스",
                "dtilPrdctClsfcNoNm": "통학운송서비스",
                "qty": "1",
                "unit": "식",
                "uprc": "49500000",
                "dlvrPlce": "○○초등학교",
            }]))
        return httpx.Response(404)

    client = G2BClient(
        G2BClientConfig(
            service_key="test-key",
            base_url="https://example.test/1230000/ad/BidPublicInfoService",
        ),
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(client.get_service_case("R26BK01234567"))

    assert result["found"] is True
    assert result["bid_notice_name"].startswith("2027학년도")
    assert result["estimated_price"] == 45_000_000
    assert result["base_amount"] == 49_500_000
    assert result["region_limit"] == "충청남도"
    assert result["license_limits"][0]["name"] == "여객자동차운송사업(전세버스)"
    assert result["items"][0]["detail_product_name"] == "통학운송서비스"
    assert result["autofill"]["base_amount"] == 49_500_000


def test_g2b_service_case_returns_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload([]))

    client = G2BClient(
        G2BClientConfig(
            service_key="test-key",
            base_url="https://example.test/1230000/ad/BidPublicInfoService",
        ),
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(client.get_service_case("R26BK00000000"))
    assert result["found"] is False
