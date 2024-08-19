# UX Datasource
from typing import Literal
import os
import json
from warnings import warn
from requests.auth import HTTPBasicAuth
from pmc_automation_tools.api.common import (
    DataSourceInput,
    DataSourceResponse,
    DataSource,
    CustomSslContextHTTPAdapter,
    RETRY_COUNT,
    BACKOFF,
    RETRY_STATUSES
    )
from pmc_automation_tools.common.exceptions import(
    PlexResponseError,
    UXResponseError,
    UXResponseErrorLog
)
import requests
from urllib3.util.retry import Retry
from itertools import chain
class UXDataSourceInput(DataSourceInput):
    def __init__(self, data_source_key: str, *args, template_folder: str=None, **kwargs):
        super().__init__(data_source_key, type='ux', *args, **kwargs)
        self.__input_types__ = {}
        self.__template_folder__ = template_folder
        if self.__template_folder__:
            template_query = self._query_template_import()
            if template_query:
                for key, value in template_query.items():
                    setattr(self, key, value)
        self._type_create()


    def _query_template_import(self):
        for file in os.listdir(self.__template_folder__):
            if f'{self.__api_id__}.json' == file:
                with open(os.path.join(self.__template_folder__, file), 'r', encoding='utf-8') as j:
                    template = json.loads(j.read())
                if 'inputs' in template.keys():
                    return template['inputs']
                return template


    def _update_input_parameters(self):
        self._query_string = {k:v for k, v in vars(self).items() if not k.startswith('_')}


    def _type_create(self):
        for k, v in vars(self).items():
            if not v or k.startswith('_'):
                continue
            value_type = type(v)
            if value_type is int and len(str(v)) == 1:
                self.__input_types__[k] = bool
            else:
                self.__input_types__[k] = value_type


    def _xstr(self, s):
        return str(s or '')


    def _xbool(self, b):
        return b.strip().upper() != 'FALSE'


    def type_reconcile(self):
        for k, v in vars(self).items():
            if k.startswith('_') or not v or k not in self.__input_types__.keys():
                continue
            target_type = getattr(self, '__input_types__')[k]
            if target_type is int:
                new_val = None if isinstance(v, str) and not v.strip() else target_type(v)
            elif target_type is str:
                new_val = self._xstr(v)
            elif target_type is bool:
                new_val = self._xbool(v)
            else:
                new_val = target_type(v)
            setattr(self, k, new_val)


    def get_to_update(self, get_instance):
        for k, v in vars(get_instance).items():
            setattr(self, k, v)
        for k in self.__input_types__.keys():
            if k not in vars(get_instance):
                self.pop_inputs(k)
        self.type_reconcile()

    def purge_empty(self):
        super().purge_empty()
        purge_attrs = []
        for y in vars(self).keys():
            if y not in self.__input_types__.keys():
                purge_attrs.append(y)
        for y in purge_attrs:
            self.pop_inputs(y)

class UXDataSource(DataSource):
    def __init__(self, *args, 
                 auth: HTTPBasicAuth | str = None, 
                 test_db: bool = True, 
                 pcn_config_file: str = 'resources/pcn_config.json', **kwargs):
        """
        Parameters:

        - auth: HTTPBasicAuth | str, optional
            - HTTPBasicAuth object
            - PCN Reference key for getting the username/password in a json config file.
            
        - test_db: bool, optional
            - Use test or production database
        
        - pcn_config_file: str, optional
            - Path to JSON file containing username/password credentials for HTTPBasicAuth connections.
        """
        super().__init__(*args, auth=auth, test_db=test_db, pcn_config_file=pcn_config_file, type='ux', **kwargs)
        self.url_db = 'test.' if self._test_db else ''
    
    def _create_session(self):
        session = requests.Session()
        retry = Retry(total=RETRY_COUNT, connect=RETRY_COUNT, backoff_factor=BACKOFF, status_forcelist=RETRY_STATUSES, raise_on_status=True)
        adapter = CustomSslContextHTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        return session
    
    def call_data_source(self, query:UXDataSourceInput):
        url = f'https://{self.url_db}cloud.plex.com/api/datasources/{query.__api_id__}/execute?format=2'
        session = self._create_session()
        response = session.post(url, json=query._query_string, auth=self._auth)
        json_data = response.json()
        return UXDataSourceResponse(query.__api_id__, **json_data)
    
    def list_data_source_access(self, pcn:str =None, all_accounts=False):
        url = f'https://{self.url_db}cloud.plex.com/api/datasources/search?name='
        session = self._create_session()
        access_list = []
        if all_accounts:
            pcn_list = [pcn for pcn in self.launch_pcn_dict.keys()]
        else:
            pcn_list = [pcn]
        for pcn in pcn_list:
            self._auth = self.set_auth(pcn)
            response = session.get(url, auth=self._auth)
            j = json.loads(response.text)
            for ds in j:
                ds['pcn'] = pcn
            access_list.append(j)
        all_datasources = list(chain.from_iterable(access_list))
        return UXDataSourceResponse('all_access',rows=all_datasources)

class UXDataSourceResponse(DataSourceResponse):
    def __init__(self, data_source_key, **kwargs):
        super().__init__(data_source_key, **kwargs)
        if isinstance(getattr(self, 'outputs', None), dict):
            for k, v in self.outputs.items():
                setattr(self, k, v)
        if getattr(self, 'rowLimitExceeded', False):
            warn('Row limit was exceeded in response. Review input filters and adjust to limit returned data.', category=UserWarning, stacklevel=3)
        if getattr(self, 'errors', []):
            raise UXResponseErrorLog(self.errors)
        self._format_response()

    def _format_response(self):
        self._transformed_data = getattr(self, 'rows', [])
        return self._transformed_data