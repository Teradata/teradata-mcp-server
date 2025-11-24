"""
Manager for QueryGrid datasource registration operations.
"""

from .base import BaseClient


class DatasourceRegistrationClient(BaseClient):
    """Manager for QueryGrid datasource registration operations."""

    BASE_ENDPOINT = "/api/operations"

    def get_datasource_registration(
        self, datasource_type: str, system_id: str
    ) -> bytes:
        """
        Generate node registration zip file for a given data source.

        Args:
            datasource_type (str): Name of the data source type. E.g. emr, dataproc, hdinsight, genericjdbc, cdp, bigquery, onpremtd
            system_id (str): ID of the system.

        Returns:
            bytes: The zip file content.
        """
        params = {}
        params["datasourceType"] = datasource_type
        params["systemId"] = system_id
        api_endpoint = f"{self.BASE_ENDPOINT}/datasource-registration"
        response = self.session.get(f"{self.base_url}{api_endpoint}", params=params)
        response.raise_for_status()
        return response.content
