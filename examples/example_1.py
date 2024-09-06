from pmc_automation_tools import UXDriver
import csv
from selenium.webdriver.common.by import By
username = open('resources/username', 'r').read()
password = open('resources/password', 'r').read()
company_code = open('resources/company', 'r').read()
pcn = '123456'
destination_pcn = '987654'
csv_file = 'container_types.csv'
pa = UXDriver(driver_type='edge') # edge or chrome is supported
driver, url_comb, token = pa.login(username, password, company_code, pcn, test_db=True)
token = pa.pcn_switch(destination_pcn)
pa.driver.get(f'{url_comb}/VisionPlex/Screen?__actionKey=6531&{token}&__features=novirtual') # &__features=novirtual will stop the results grid from lazy loading.
pa.wait_for_gears()
pa.wait_for_element(By.NAME, 'ContainerTypenew')
pa.ux_click_button('Search')
pa.wait_for_gears()

with open(csv_file,'r',encoding='utf-8-sig') as f:
    c = csv.DictReader(f)
    for r in c:
        container_type = r['container_type']
        cube_width = r['cube_width']
        cube_height = r['cube_height']
        cube_length = r['cube_length']
        cube_unit = r['cube_unit']
        pa.wait_for_element(By.LINK_TEXT, container_type).click()
        pa.wait_for_gears()
        pa.wait_for_element(By.NAME, 'CubeLength').sync_textbox(cube_length)
        pa.wait_for_element(By.NAME, 'CubeWidth').sync_textbox(cube_width)
        pa.wait_for_element(By.NAME, 'CubeHeight').sync_textbox(cube_height)
        pa.wait_for_element(By.NAME, 'UnitKey').sync_picker(cube_unit)
        pa.ux_click_button('Ok')
        pa.wait_for_banner()
        pa.wait_for_gears()
        pa.wait_for_element(By.NAME, 'ContainerTypenew')
        pa.wait_for_gears()
        pa.wait_for_banner()