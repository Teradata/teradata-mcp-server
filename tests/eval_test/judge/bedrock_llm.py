"""DeepEval LLM wrapper backed by AWS Bedrock (Converse API)."""

from __future__ import annotations

import json
import os
from typing import Any

import boto3
from deepeval.models.base_model import DeepEvalBaseLLM

from judge.usage import record_bedrock_usage


class BedrockLLM(DeepEvalBaseLLM):
    returns_token_cost = True

    def __init__(self, model_id: str | None = None, bedrock_client=None):
        self.model_id = model_id or os.environ.get(
            "BEDROCK_JUDGE_MODEL_ID",
            os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
        )
        self._client = bedrock_client or self._build_client()
        super().__init__()

    def _build_client(self):
        region = os.environ.get("AWS_REGION", "us-east-1")
        return boto3.client("bedrock-runtime", region_name=region)

    def load_model(self):
        return self._client

    def get_model_name(self) -> str:
        return self.model_id

    def _call(self, prompt: str, schema: Any = None) -> tuple[Any, float | None]:
        response = self._client.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
        )
        cost_usd = record_bedrock_usage(model_id=self.model_id, role="judge", response=response)
        text = response["output"]["message"]["content"][0]["text"]

        if schema is not None:
            # deepeval passes a Pydantic model as schema for structured output;
            # extract the JSON block from the response and parse it.
            try:
                start = text.index("{")
                end = text.rindex("}") + 1
                return schema.model_validate(json.loads(text[start:end])), cost_usd
            except Exception:
                pass

        return text, cost_usd

    def generate(self, prompt: str, schema: Any = None) -> tuple[Any, float | None]:
        return self._call(prompt, schema)

    async def a_generate(self, prompt: str, schema: Any = None) -> tuple[Any, float | None]:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._call, prompt, schema)
