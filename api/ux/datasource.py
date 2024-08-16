# UX Datasource
from typing import Literal
import os
import json

from requests.auth import HTTPBasicAuth
from api.common import (
    DataSourceInput,
    DataSourceResponse,
    DataSource,
    CustomSslContextHTTPAdapter,
    RETRY_COUNT,
    BACKOFF,
    RETRY_STATUSES
    )
import requests
from urllib3.util.retry import Retry

class uxDataSourceInput(DataSourceInput):
    def __init__(self, data_source_key: str, *args, template_folder: str=None, **kwargs):
        super().__init__(data_source_key, type='ux', *args, **kwargs)
        self.__input_types__ = {}
        self.__template_folder__ = template_folder
        if self.__template_folder__:
            template_query = self._query_template_import()
            for key, value in template_query.items():
                setattr(self, key, value)
        self._type_create()


    def _query_template_import(self):
        for file in os.listdir(self.__template_folder__):
            if f'{self.__api_id__}.json' == file:
                with open(os.path.join(self.__template_folder__,file), 'r',encoding='utf-8') as j:
                    template = json.loads(j.read())
                if 'inputs' in template.keys():
                    return template['inputs']
                return template


    def _update_input_parameters(self):
        self._query_string = {k:v for k,v in vars(self).items() if not k.startswith('_')}


    def _type_create(self):
        for k,v in vars(self).items():
            if not v or k.startswith('_'):
                continue
            value_type = type(v)
            if value_type is int and len(str(v)) == 1:
                self.__input_types__[k] = bool
            else:
                self.__input_types__[k] = value_type


    def _xstr(self,s):
        return str(s or '')


    def _xbool(self,b):
        return b.strip().upper() != 'FALSE'


    def type_reconcile(self):
        for k,v in vars(self).items():
            if k.startswith('_') or not v or k not in self.__input_types__:
                continue
            target_type = getattr(self,'__input_types__')[k]
            if target_type is int:
                new_val = None if isinstance(v,str) and not v.strip() else target_type(v)
            elif target_type is str:
                new_val = self.xstr(v)
            elif target_type is bool:
                new_val = self.xbool(v)
            else:
                new_val = target_type(v)
            setattr(self,k,new_val)


    def get_to_update(self, get_instance):
        for k,v in vars(get_instance).items():
            setattr(self, k, v)
        for k in self.__input_types__.keys():
            if k not in vars(get_instance):
                self.pop_inputs(k)
        self.type_reconcile()


class uxDataSource(DataSource):
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

    def call_data_source(self, query:uxDataSourceInput):
        if self._test_db:
            db = 'test.'
        else:
            db = ''
        url = f'https://{db}cloud.plex.com/api/datasources/{query.__api_id__}/execute?format=2'
        session = requests.Session()
        retry = Retry(total=RETRY_COUNT, connect=RETRY_COUNT, backoff_factor=BACKOFF, status_forcelist=RETRY_STATUSES, raise_on_status=True)
        adapter = CustomSslContextHTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        response = session.post(url, json=query._query_string, auth=self._auth)
        json_data = response.json()
        return json_data

class uxDataSourceResponse(DataSourceResponse):
    def __init__(self, data_source_key, **kwargs):
        super().__init__(data_source_key, **kwargs)

    def _format_response(self):...
