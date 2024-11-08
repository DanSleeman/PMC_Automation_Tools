from pmc_automation_tools.api.common import (
    DataSourceInput,
    DataSourceResponse,
    DataSource,
    CustomSslContextHTTPAdapter,
    RETRY_COUNT,
    BACKOFF,
    RETRY_STATUSES
    )
from pmc_automation_tools.common.exceptions import ApiError
import requests
from requests.exceptions import HTTPError

from urllib3.util.retry import Retry

from itertools import chain
from concurrent.futures import ThreadPoolExecutor

from typing import List

TEST = 'https://test.connect.plex.com'
PROD = 'https://connect.plex.com'

class ApiDataSourceInput(DataSourceInput):
    def __init__(self, url: str, method: str, *args, **kwargs):
        super().__init__(url, type='api', *args, **kwargs)
        self._method = method
    
    
    def __repr__(self):
        _attrs = [f"{k}='{v}'" for k, v in vars(self).items() if not k.startswith('_')]
        return f"ApiDataSourceInput(url={self.__api_id__}, method={self._method}, {', '.join(_attrs)})"


    def _update_input_parameters(self):
        self._query_string = {k:v for k, v in vars(self).items() if not k.startswith('_')}
        if 'json' in self._query_string.keys():
            self._query_string = self._query_string['json']


class ApiDataSource(DataSource):
    def __init__(self, auth: str, *args, test_db: bool = True, **kwargs):
        """
        Parameters:

        - auth: str
            - API Key as a string

        - test_db: bool, optional
            - Use test or production database
        """
        super().__init__(*args, auth=auth, test_db=test_db, type='api', **kwargs)
    

    def __repr__(self):
        return f"ApiDataSource(auth={self.__auth_key__}, test_db={self._test_db})"
    

    def call_data_source(self, pcn:str|list, query:ApiDataSourceInput):
        """
        Returns a list of the json objects as dictionaries from the API response.

        Parameters:

        - pcn: str | list
            - Single PCN number or list of PCNs to run the query against

        - query: ApiDataSourceInput
            - DataSourceInput containing the connection parameters
        """
        if self._test_db:
            query.__api_id__ = query.__api_id__.replace(PROD, TEST)
        response_list = []
        if isinstance(pcn, str):
            pcn_list = [pcn]
        for p in pcn_list:
            headers = {'Content-Type': 'application/json',
                'X-Plex-Connect-Api-Key': self._auth,
                'X-Plex-Connect-Customer-Id': p
            }
            session = requests.Session()
            retry = Retry(total=RETRY_COUNT, connect=RETRY_COUNT, backoff_factor=BACKOFF, status_forcelist=RETRY_STATUSES, raise_on_status=True)
            adapter = CustomSslContextHTTPAdapter(max_retries=retry)
            session.mount('https://', adapter)
            request_params = {'json': query._query_string} if query._method.upper() in ['POST', 'PUT'] else {'params': query._query_string}
            response = session.request(query._method, query.__api_id__, headers=headers, **request_params)
            try:
                response.raise_for_status()
            except HTTPError as e:
                raise ApiError('Error calling API.', **response.json(), status=response.status_code)
            # List of dictionaries or single dictionary object
            if response.text != [] and response.text != '':
                    if type(response.json()) is list:
                        response_list.append(response.json())
                    else:
                        response_list.append([response.json()])
            else:
                return response
        return ApiDataSourceResponse(query.__api_id__, response_list = list(chain.from_iterable(response_list)))


    def call_data_source_threaded(self, query_list:List['ApiDataSourceInput']) -> List['ApiDataSourceResponse']:
        with ThreadPoolExecutor(max_workers=8) as pool:
            response_list = list(pool.map(self.call_data_source, query_list))
        return response_list


class ApiDataSourceResponse(DataSourceResponse):
    def __init__(self, url, **kwargs):
        super().__init__(url, **kwargs)
        self._format_response()

    def _format_response(self):
        self._transformed_data = getattr(self, 'response_list', [])
