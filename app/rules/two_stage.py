"""학교 용역 2단계(규격·가격) 입찰 공통 판정.

지방계약법 시행령 제18조를 기반으로 하되,
제안서 적격점수는 법에서 일률적으로 정한 값이 아니라 학교가 공고·평가기준으로 정한다.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class TwoStageMethod(StrEnum):
    SIMULTANEOUS = "SIMULTANEOUS"
    SEQUENTIAL = "SEQUENTIAL"


@dataclass(slots=True)
class TwoStageInput:
    service_name: str
    method: TwoStageMethod = TwoStageMethod.SIMULTANEOUS
    proposal_pass_score: float = 80.0
    total_proposal_score: float = 100.0
    price_open_only_for_qualified: bool = True


@dataclass(slots=True)
class TwoStageResult:
    contract_method: str
    legal_basis: str
    proposal_pass_score: float
    total_proposal_score: float
    price_open_only_for_qualified: bool
    flow: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def evaluate_two_stage(data: TwoStageInput) -> TwoStageResult:
    if not data.service_name.strip():
        raise ValueError("용역명이 필요합니다.")
    if data.total_proposal_score <= 0:
        raise ValueError("제안서 총점은 0점보다 커야 합니다.")
    if not 0 < data.proposal_pass_score <= data.total_proposal_score:
        raise ValueError("제안서 적격점수는 0점 초과 총점 이하여야 합니다.")

    if data.method == TwoStageMethod.SIMULTANEOUS:
        method = "2단계 규격·가격 동시입찰"
        flow = [
            "입찰공고",
            "제안서(규격입찰서)와 가격입찰서 동시 접수",
            "제안서 평가",
            f"{data.proposal_pass_score:g}점 이상 등 공고에서 정한 기준으로 규격적격자 확정",
            "규격적격자에 한해 가격입찰 개찰",
            "예정가격 이하 최저가격 등 공고에서 정한 기준으로 낙찰자 결정",
            "계약체결",
        ]
    else:
        method = "2단계 규격입찰 후 가격입찰"
        flow = [
            "입찰공고",
            "규격입찰서 접수 및 평가",
            "규격적격자 확정",
            "규격적격자에게 가격입찰 참가자격 부여",
            "가격입찰",
            "낙찰자 결정",
            "계약체결",
        ]

    return TwoStageResult(
        contract_method=method,
        legal_basis="지방계약법 시행령 제18조",
        proposal_pass_score=data.proposal_pass_score,
        total_proposal_score=data.total_proposal_score,
        price_open_only_for_qualified=True,
        flow=flow,
        checks=[
            "제안서 평가항목·배점·적격점수를 공고 전에 확정",
            "가격입찰은 규격·기술 적격자로 확정된 업체에 한해 개찰",
            "평가위원 구성·제안서 제출방법·평가일정을 학교 기준에 맞게 확정",
            "동일가격 최저가 처리방식(전자자동추첨·제안서 평가점수 우선 등)을 적용근거와 함께 공고 전에 확정",
            "유찰·재입찰 처리방법을 공고문에 명확히 기재",
        ],
        warnings=[
            "80점은 학교 공고에서 자주 쓰이는 기준이지만 지방계약법 시행령이 일률적으로 강제하는 점수는 아닙니다.",
            "청소·경비 등 행정안전부령이 정하는 단순노무용역에는 시행령 제18조 2단계 입찰을 적용하지 않습니다.",
        ],
    )
