"""딸깍 계약업무 플랫폼 공통 도메인 모델.

공사·용역·물품이 동일한 계약 사건카드 구조를 사용하고,
학교/기관별 tenant 경계를 명시적으로 둔다.

Firestore 연결 전 단계의 순수 모델이며 저장소 구현과 분리한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


class OrganizationType(StrEnum):
    SCHOOL = "SCHOOL"
    SUPPORT_OFFICE = "SUPPORT_OFFICE"
    EDUCATION_OFFICE = "EDUCATION_OFFICE"
    OTHER_PUBLIC = "OTHER_PUBLIC"


class OrganizationStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class MembershipRole(StrEnum):
    ORG_ADMIN = "ORG_ADMIN"
    CONTRACT_MANAGER = "CONTRACT_MANAGER"
    VIEWER = "VIEWER"


class MembershipStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class ContractDomain(StrEnum):
    WORKS = "WORKS"
    SERVICE = "SERVICE"
    GOODS = "GOODS"


class CaseStatus(StrEnum):
    DRAFT = "DRAFT"
    INTERNAL_REVIEW = "INTERNAL_REVIEW"
    NOTICE_PREPARATION = "NOTICE_PREPARATION"
    NOTICE_OPEN = "NOTICE_OPEN"
    BID_OPENING = "BID_OPENING"
    QUALIFICATION_REVIEW = "QUALIFICATION_REVIEW"
    AWARD_DECISION = "AWARD_DECISION"
    CONTRACT_PREPARATION = "CONTRACT_PREPARATION"
    CONTRACTED = "CONTRACTED"
    PERFORMANCE = "PERFORMANCE"
    INSPECTION = "INSPECTION"
    PAYMENT = "PAYMENT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass(slots=True)
class Organization:
    org_id: str
    name: str
    organization_type: OrganizationType = OrganizationType.SCHOOL
    external_code: str | None = None
    parent_org_id: str | None = None
    region: str | None = None
    status: OrganizationStatus = OrganizationStatus.PENDING
    created_at: datetime | None = None


@dataclass(slots=True)
class Membership:
    membership_id: str
    user_id: str
    org_id: str
    role: MembershipRole = MembershipRole.CONTRACT_MANAGER
    status: MembershipStatus = MembershipStatus.PENDING
    joined_at: datetime | None = None


@dataclass(slots=True)
class ContractCase:
    case_id: str
    org_id: str
    fiscal_year: int
    sequence: int
    domain: ContractDomain
    title: str
    status: CaseStatus = CaseStatus.DRAFT

    subtype: str | None = None
    owner_user_id: str | None = None
    g2b_notice_no: str | None = None
    planned_notice_date: date | None = None
    bid_open_date: date | None = None
    contract_date: date | None = None

    budget_amount: int | None = None
    estimated_price: int | None = None
    base_amount: int | None = None
    contract_amount: int | None = None

    rule_version: str | None = None
    current_action: str | None = None
    due_date: date | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None
    tags: list[str] = field(default_factory=list)


def make_case_number(
    *,
    organization_code: str,
    fiscal_year: int,
    sequence: int,
    domain: ContractDomain,
) -> str:
    """사람이 보기 쉬운 기관별 계약 사건번호를 만든다.

    예: CHN123-2027-S-001
    """
    if sequence <= 0:
        raise ValueError("sequence는 1 이상이어야 합니다.")
    domain_code = {
        ContractDomain.WORKS: "W",
        ContractDomain.SERVICE: "S",
        ContractDomain.GOODS: "G",
    }[domain]
    safe_org = "".join(ch for ch in organization_code.upper() if ch.isalnum() or ch in "-_")
    if not safe_org:
        raise ValueError("organization_code가 비어 있습니다.")
    return f"{safe_org}-{fiscal_year}-{domain_code}-{sequence:03d}"
