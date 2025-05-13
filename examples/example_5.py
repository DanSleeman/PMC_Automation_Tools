import pmc_automation_tools as pa
import os
from selenium.webdriver.common.by import By

username = open(os.path.join('resources','username')).read()
password = open(os.path.join('resources','password')).read()
company_code = open(os.path.join('resources','company')).read()
pcn = '123456'
dest_pcn = '987654'
test = True
input_file = 'Operations.csv'
input_records = pa.read_updated(input_file)

batch_code_folder = pa.create_batch_folder(test=test)
update_file = os.path.join(batch_code_folder, 'Updates.csv')
error_file = os.path.join(batch_code_folder, 'Errors.csv')
updated = pa.read_updated(update_file)

ux = pa.UXDriver('chrome')
logger = pa.setup_logger('Operations', root_dir=batch_code_folder)
driver, url_comb, token = ux.login(username, password, company_code, pcn, test_db=test)
token = ux.pcn_switch(dest_pcn)
# Operations screen URL
MAIN_URL = f'{url_comb}/VisionPlex/Screen?__actionKey=7148&{token}&__features=novirtual'
driver.get(MAIN_URL)
ux.wait_for_element(By.NAME, 'OperationCode')

for row in input_records:
    if row in updated:
        continue
    try:
        ux.click_action_bar_item('Add')
        ux.wait_for_gears()
        # Each column name should match the screen element's label text.
        # Underscores in the column name are replaced with spaces.
        # Case sensitivity does not matter.
        for k, v in row.items():
            screen_elem = ux.find_element_by_label(k)
            screen_elem.sync(v)
        ux.click_button('Ok')
        ux.wait_for_banner()
        ux.wait_for_gears()
        pa.save_updated(update_file, row)
    except Exception as e:
        logger.error(row)
        logger.exception(e)
        pa.save_updated(error_file, row)
        driver.get(MAIN_URL)
        ux.wait_for_element(By.NAME, 'OperationCode')

