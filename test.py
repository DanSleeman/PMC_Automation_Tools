from api.ux.datasource import uxDataSource,uxDataSourceInput,uxDataSourceResponse
from api.classic.datasource import ClassicDataSource,ClassicDataSourceInput,ClassicDataSourceResponse
from api.datasource import ApiDataSourceInput
import os
from driver.common import PlexDriver
from driver.ux.driver import uxDriver
from driver.classic.driver import ClassicDriver
from common.utils import create_batch_folder
import logging
db = 'test'
# wsdl = os.path.join(os.getcwd(),'resources','Plex_SOAP_test.wsdl')
# c = ClassicDataSource(wsdl,auth='Grand Haven',db=db)
# ci = ClassicDataSourceInput(2145)
# ci.Part_No = '278780-20'
# ci.Active = '1'
# cr = c.call_data_source(ci)
# pa = ClassicDriver(debug=True,debug_level=logging.DEBUG,driver_type='edge')
pa = uxDriver(debug=True,debug_level=logging.DEBUG,driver_type='edge')
username = open('resources/username','r').read()
password = open('resources/password','r').read()
company = open('resources/company','r').read()
pa.login(username,password,company,'79870',test_db=True)
# pa.driver.get(f'{pa.url_comb}/Rendering_Engine/Default.aspx?Request=Show&RequestData=SourceType(Screen)SourceKey(5726)')
e = pa.wait_for_element(('name','PartNo'))
e.screenshot()
pa.wait_for_gears()
pa.click_button('Search')
pa.wait_for_gears()
create_batch_folder(test=True)

ai = ApiDataSourceInput('https://connect.plex.com/platform/custom-fields/vi/field-types/','get',json={'asdf':'asdf'})
ai.test_input = 'asdf'
ui = uxDataSourceInput('1234')
ui.Test_input = 'asfd'
ui.foo = 'bar'
ui.Foo = 'Baz'





driver,urlcomb,token = pa.login()
pa.driver.get(f'{urlcomb}/Engineering/Part?__features=novirtual&{token}')
pa.wait_for_gears()
part_no = pa.wait_for_element(('name','PartNo'))
part_no.send_keys('278780-20')
part_no.send_keys('\n')
pa.wait_for_gears()
pa.debug_logger.debug('searched')
# pa._debug_print('asdfasdf',level=1)

pa.debug_logger.debug('top level debug')