"""나라장터(OpenAPI) 연동 모듈.

실제 엔드포인트와 응답 스키마는 활용신청 완료 후 확정합니다.
API 키는 환경변수 DATA_GO_KR_SERVICE_KEY에서 읽습니다.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class G2BClientConfig:
    service_key: str


class G2BClient:
    def __init__(self, config: G2BClientConfig) -> None:
        self.config = config

    async def get_bid_notice(self, bid_notice_no: str) -> dict:
        raise NotImplementedError("나라장터 입찰공고 API 스키마 확정 후 구현")
