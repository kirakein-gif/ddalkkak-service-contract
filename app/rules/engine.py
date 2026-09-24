"""용역계약 규칙엔진.

법령·예규에서 도출된 규칙 데이터와 입력값을 분리해 관리합니다.
초기 버전에서는 판단 결과뿐 아니라 근거 규정과 확인 필요 항목을 함께 반환합니다.
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class ContractInput:
    service_name: str
    estimated_price: int
    service_type: str = "일반용역"
    region: str | None = None


@dataclass(slots=True)
class RuleResult:
    contract_method: str
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def evaluate_contract(data: ContractInput) -> RuleResult:
    return RuleResult(
        contract_method="판정 규칙 미구현",
        reasons=["실제 용역계약 사례와 현행 규정을 기준으로 규칙을 확정할 예정입니다."],
        warnings=["현재 결과는 업무 판단에 사용할 수 없습니다."],
    )
