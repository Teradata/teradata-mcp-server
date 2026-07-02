import pytest
from tests.conftest import assert_eval_case, load_cases


@pytest.mark.parametrize("case", load_cases("qlty"), ids=lambda c: c["id"])
def test_qlty(case, bedrock_client, agent_model_id, judge_llm):
    assert_eval_case(case, bedrock_client, agent_model_id, judge_llm)
