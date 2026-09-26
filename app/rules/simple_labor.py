"""청소·경비 등 단순노무용역 공통 규칙."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class SimpleLaborResult:
    two_stage_allowed: bool = False
    negotiation_allowed: bool = False
    legal_bases: list[str] = field(default_factory=lambda: [
        "지방계약법 시행령 제18조(청소·경비 등 단순노무용역 2단계 입찰 제외)",
        "지방계약법 시행령 제43조(청소·경비 등 단순노무용역 협상에 의한 계약 제외)",
    ])
    checks: list[str] = field(default_factory=lambda: [
        "용역이 실제 단순노무용역에 해당하는지 확인",
        "인원·근로시간·업무범위와 원가계산의 노무비가 일치하는지 확인",
        "최저임금·4대보험·퇴직급여 등 관계 노동관계법령 반영 여부 확인",
        "도급근로자 보호지침·산업안전 관련 적용사항 확인",
        "과업에 소독·방역 등 별도 법정자격이 포함되면 해당 자격을 추가 확인",
    ])


def evaluate_simple_labor() -> SimpleLaborResult:
    return SimpleLaborResult()
