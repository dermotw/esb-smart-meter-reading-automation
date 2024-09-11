#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup   # pip install beautifulsoup4
import re as re
import json
import csv
import yaml
import sys

try:
  if sys.argv[1] == 'debug':
    debug = True
except:
   debug = False

with open("config.yml") as config_file:
  config = yaml.load(config_file, Loader=yaml.FullLoader)

meter_mprn = config["esb"]["mprn"]
esb_user_name = config["esb"]["user_name"]
esb_password = config["esb"]["password"]

main_url = "https://myaccount.esbnetworks.ie"
historic_consumption_url = "https://myaccount.esbnetworks.ie/Api/HistoricConsumption"
file_url = 'https://myaccount.esbnetworks.ie/DataHub/DownloadHdfPeriodic'

if debug == True:
  print("[+] open session ...")
s = requests.Session()

s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
  })
login_page = s.get(main_url, allow_redirects=True)
if debug == True:
  print("[!] Landing page Status Code: ", login_page.status_code)
result = re.findall(r"(?<=var SETTINGS = )\S*;", str(login_page.content))
settings = json.loads(result[0][:-1])
if debug == True:
  print("-"*10)
  print("csrf token: ", settings['csrf'])
  print("transid token: ", settings['transId'])
  print("-"*10)

s.post(
    'https://login.esbnetworks.ie/esbntwkscustportalprdb2c01.onmicrosoft.com/B2C_1A_signup_signin/SelfAsserted?tx=' + settings['transId'] + '&p=B2C_1A_signup_signin',
    data={
      'signInName': esb_user_name, 
      'password': esb_password, 
      'request_type': 'RESPONSE'
    },
    headers={
      'x-csrf-token': settings['csrf'],
    },
    allow_redirects=True)
confirm_login = s.get(
    'https://login.esbnetworks.ie/esbntwkscustportalprdb2c01.onmicrosoft.com/B2C_1A_signup_signin/api/CombinedSigninAndSignup/confirmed',
    params={
      'rememberMe': False,
      'csrf_token': settings['csrf'],
      'tx': settings['transId'],
      'p': 'B2C_1A_signup_signin',
    }
  )
soup = BeautifulSoup(confirm_login.content, 'html.parser')
form = soup.find('form', {'id': 'auto'})
if debug == True:
  print("[!] Submitting login form ...")
fff=s.post(
        form['action'],
        allow_redirects=True,
        data={
          'state': form.find('input', {'name': 'state'})['value'],
          'client_info': form.find('input', {'name': 'client_info'})['value'],
          'code': form.find('input', {'name': 'code'})['value'],
        }, 
    )
if debug == True:
  print("[!] Status Code: ", fff.status_code)
user_welcome_soup = BeautifulSoup(fff.text,'html.parser')
user_elements = user_welcome_soup.find('h1', class_='esb-title-h1')
if user_elements.text[:2] != "We":
    print("[!!!] No Welcome message, User is not logged in.")
    s.close()
h1_elem = s.get(historic_consumption_url, allow_redirects=True)
h1_elem_content = h1_elem.text
h1_elem_soup = BeautifulSoup(h1_elem_content, 'html.parser')
h1_elem_element = h1_elem_soup.find('h1', class_='esb-title-h1')
if h1_elem_element.text[:2] != "My":
    print("[!] ups - something went wrong.")
    s.close()
x_headers={
  'Host': 'myaccount.esbnetworks.ie',
  'x-ReturnUrl': historic_consumption_url,
  'Referer': historic_consumption_url,
}
x_down = s.get(main_url+"/af/t",headers=x_headers)
set_cookie_header = x_down.headers.get('Set-Cookie', '')
def extract_xsrf_token(cookie_header):
    cookies = cookie_header.split(',')
    for cookie in cookies:
        if 'XSRF-TOKEN' in cookie:
            token = cookie.split('XSRF-TOKEN=')[1].split(';')[0]
            return token
    return None
xsrf_token = extract_xsrf_token(set_cookie_header)
file_headers = {
    'Referer': historic_consumption_url,
    'content-type': 'application/json',
    'x-returnurl': historic_consumption_url,
    'x-xsrf-token': xsrf_token,
    'Origin': main_url,
}
payload_data = {
    "mprn": meter_mprn,
    "searchType": "intervalkw"
}
response_data_file = s.post(file_url, headers=file_headers, json=payload_data)

s.close()
magic_data = response_data_file.content.decode("utf-8")

my_json = []
csv_reader = csv.DictReader(magic_data.split('\n'))

for row in csv_reader:
    my_json.append(row)

json_out = json.dumps(my_json, indent=2)

print(json_out)