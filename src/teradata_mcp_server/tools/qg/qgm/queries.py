"""
Manager for QueryGrid queries.
"""

from typing import Any, Dict

from .base import BaseClient


class QueryClient(BaseClient):
    """Manager for QueryGrid queries."""

    BASE_ENDPOINT = "/api/queries"

    def get_query_summary(
        self,
        last_modified_after: str | None = None,
        completed: bool = False,
        query_text_phrase: str | None = None,
        query_ref_ids: str | None = None,
        initiator_query_id: str | None = None,
    ) -> Dict[str, Any]:
        """Get query summary records."""
        params = {}
        if (
            last_modified_after is not None
            and last_modified_after != ""
            and last_modified_after != "null"
        ):
            params["lastModifiedAfter"] = last_modified_after
        if completed:
            params["completed"] = completed
        if (
            query_text_phrase is not None
            and query_text_phrase != ""
            and query_text_phrase != "null"
        ):
            params["queryTextPhrase"] = query_text_phrase
        if (
            query_ref_ids is not None
            and query_ref_ids != ""
            and query_ref_ids != "null"
        ):
            params["queryRefIds"] = query_ref_ids
        if (
            initiator_query_id is not None
            and initiator_query_id != ""
            and initiator_query_id != "null"
        ):
            params["initiatorQueryId"] = initiator_query_id
        return self._request(
            "GET", self.BASE_ENDPOINT, params=params if params else None
        )

    def get_query_by_id(self, id: str) -> Dict[str, Any]:
        """Get query summary by ID."""
        return self._request("GET", f"{self.BASE_ENDPOINT}/{id}")

    def get_query_details(self, id: str) -> Dict[str, Any]:
        """Get query details by ID."""
        return self._request("GET", f"{self.BASE_ENDPOINT}/{id}/details")
