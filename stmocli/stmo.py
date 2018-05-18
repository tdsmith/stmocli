from redash_client.client import RedashClient
import requests
from requests.compat import urljoin

from .conf import Conf


class STMO(object):
    """The STMO half of stmocli.

    This class is responsible for all of stmocli's functionality that does not involve
    accepting input from the user or displaying the results.
    """
    RedashClientException = RedashClient.RedashClientException

    def __init__(self, redash_api_key, conf=None):
        self.conf = conf or Conf()
        self._redash = RedashClient(redash_api_key)
        self.redash_api_key = redash_api_key

    def get_query(self, query_id):
        """Fetches information about a query from Redash.

        Args:
            query_id (int, str): Redash query ID

        Returns:
            query (dict): The response from redash, representing a Query model.
        """
        # Get query:
        # https://github.com/getredash/redash/blob/1573e06e710733714d47940cc1cb196b8116f670/redash/handlers/api.py#L74
        url_path = "queries/{}?api_key={}".format(query_id, self.redash_api_key)
        results, response = self._redash._make_request(
            requests.get,
            urljoin(self._redash.API_BASE_URL, url_path)
        )
        return results

    def track_query(self, query_id, file_name):
        """Saves a query to disk and adds it to the conf file.

        Args:
            query_id (int, str): Redash query ID
            file_name (str, callable): Name of the file_name to write the query out to.
                If callable, receives the Redash query object as a parameter.

        Returns:
            query (dict): The response from redash, representing a Query model.
        """
        query = self.get_query(query_id)
        query_file_name = file_name(query) if callable(file_name) else file_name
        with open(query_file_name, "w") as outfile:
            outfile.write(query["query"])
        query_meta = {
            "id": query_id,
            "data_source_id": query["data_source_id"],
            "name": query["name"],
            "description": query["description"],
            "schedule": query["schedule"],
            "options": query["options"]
        }
        self.conf.add_query(query_file_name, query_meta)
        return query

    def push_query(self, file_name):
        """Replaces the SQL on Redash with the local version of a tracked query.

        Args:
            file_name (str): file_name of a tracked query

        Returns:
            meta (dict): The query metadata

        Throws:
            KeyError: if query is not tracked
            RedashClientException
        """
        meta = self.conf.get_query(file_name)
        with open(file_name, 'r') as fin:
            sql = fin.read()
        self._redash.update_query(
            meta['id'], meta['name'],
            sql, meta['data_source_id'],
            meta['description'], meta['options'])
        return meta

    def url_for_query(self, file_name):
        meta = self.conf.get_query(file_name)
        return urljoin(RedashClient.BASE_URL, "queries/{id}".format(**meta))
