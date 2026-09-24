from app.rules.engine import ContractInput, evaluate_contract


def test_rule_engine_returns_draft_result() -> None:
    result = evaluate_contract(
        ContractInput(
            service_name="테스트 용역",
            estimated_price=10_000_000,
        )
    )
    assert result.contract_method == "판정 규칙 미구현"
    assert result.warnings
