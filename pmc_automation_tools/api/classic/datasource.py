from api.common import DataSourceInput, DataSourceResponse, DataSource
from common.exceptions import ClassicConnectionError

import requests
from typing import Literal
from requests.auth import HTTPBasicAuth

from zeep import Client
from zeep.transports import Transport
from zeep.helpers import serialize_object

SOAP_TEST = 'https://testapi.plexonline.com/Datasource/service.asmx'
SOAP_PROD = 'https://api.plexonline.com/Datasource/service.asmx'
class ClassicDataSourceInput(DataSourceInput):
    def __init__(self, data_source_key: int, *args, delimeter='|', **kwargs):
        self._delimeter = delimeter
        super().__init__(data_source_key, *args, type='classic', **kwargs)
        self.__api_id__ = int(self.__api_id__)

    def _update_input_parameters(self):
        self._parameter_names = self._delimeter.join([k for k, v in vars(self).items() if not k.startswith('_')])
        self._parameter_values = self._delimeter.join([v for k, v in vars(self).items() if not k.startswith('_')])


class ClassicDataSource(DataSource):
    def __init__(self, wsdl, *args, 
                 auth: HTTPBasicAuth|str=None, 
                 test_db: bool = True, 
                 pcn_config_file: str='resources/pcn_config.json', **kwargs):
        """
        Parameters:
        - wsdl: path
            - Path to the wsdl file. Plex restricts access to their wsdl URL and these files can be found on the community.

        - auth: HTTPBasicAuth | str, optional
            - HTTPBasicAuth object
            - API Key as a string
            - PCN Reference key for getting the username/password in a json config file.
            
        - test_db: bool, optional
            - Use test or production database
        
        - pcn_config_file: str, optional
            - Path to JSON file containing username/password credentials for HTTPBasicAuth connections.
        """
        super().__init__(*args, auth=auth, test_db=test_db, pcn_config_file=pcn_config_file, type='classic', **kwargs)
        self._wsdl = wsdl


    def call_data_source(self, query:ClassicDataSourceInput):
        session = requests.Session()
        session.auth = self._auth
        client = Client(wsdl=self._wsdl, transport=Transport(session=session))
        self._connection_address = client.wsdl.services['Service'].ports['ServiceSoap'].binding_options['address']
        if self._test_db and self._connection_address != SOAP_TEST:
            raise
        response = client.service.ExecuteDataSourcePost(dataSourceKey=query.__api_id__, parameterNames=query._parameter_names, parameterValues=query._parameter_values, delimeter=query._delimeter)
        _response = serialize_object(response, dict)
        return ClassicDataSourceResponse(query.__api_id__, **_response)


class ClassicDataSourceResponse(DataSourceResponse):
    def __init__(self, data_source_key, **kwargs):
        super().__init__(data_source_key, **kwargs)
        if self.Error:
            raise ClassicConnectionError(self.Message,
                                         data_source_key=self.DataSourceKey,
                                         instance=self.InstanceNo,
                                         status=self.StatusNo,
                                         error_no=self.ErrorNo)
        self._result_set = kwargs.get('ResultSets')
        if self._result_set:
            self._row_count = self._result_set['ResultSet'][0]['RowCount']
            self._result_set = self._result_set['ResultSet'][0]['Rows']['Row']
            self._format_response()
    
    
    def _format_response(self):
        self._transformed_data = []
        if hasattr(self, '_result_set'):
            for row in self._result_set:
                row_data = {}
                columns = row['Columns']['Column']
                for column in columns:
                    name = column['Name']
                    value = column['Value']
                    row_data[name] = value
                self._transformed_data.append(row_data)
        return self._transformed_data