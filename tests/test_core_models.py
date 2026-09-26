import pytest

from app.models.core import ContractDomain, make_case_number


@pytest.mark.parametrize(
    ("domain", "expected"),
    [
        (ContractDomain.WORKS, "SCH001-2027-W-001"),
        (ContractDomain.SERVICE, "SCH001-2027-S-001"),
        (ContractDomain.GOODS, "SCH001-2027-G-001"),
    ],
)
def test_make_case_number_by_domain(domain, expected):
    assert make_case_number(
        organization_code="SCH001",
        fiscal_year=2027,
        sequence=1,
        domain=domain,
    ) == expected


def test_case_number_sanitizes_organization_code():
    assert make_case_number(
        organization_code="sch 001!",
        fiscal_year=2027,
        sequence=12,
        domain=ContractDomain.SERVICE,
    ) == "SCH001-2027-S-012"


def test_case_number_requires_positive_sequence():
    with pytest.raises(ValueError):
        make_case_number(
            organization_code="SCH001",
            fiscal_year=2027,
            sequence=0,
            domain=ContractDomain.GOODS,
        )
