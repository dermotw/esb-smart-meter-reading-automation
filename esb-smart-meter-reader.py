#!/usr/bin/env python3

# https://www.boards.ie/discussion/2058292506/esb-smart-meter-data-script
# https://gist.github.com/schlan/f72d823dd5c1c1d19dfd784eb392dded

# Modified by badger707
# it works as of 21-JUL-2023
#
# Further modified by dermo
# still works as of 30/01/2024 but give me time...

import urllib3
urllib3.disable_warnings()

import requests
from bs4 import BeautifulSoup
import re
import json
import csv
from datetime import datetime, timedelta, timezone

import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

import yaml
from yaml import load

def load_esb_data(user, password, mpnr, start_date):
  print("[+] open session ...")
  s = requests.Session()
  s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
  })    
  print("[+] calling login page. ..")
  login_page = s.get('https://myaccount.esbnetworks.ie/', allow_redirects=True)
  result = re.findall(r"(?<=var SETTINGS = )\S*;", str(login_page.content))
  settings = json.loads(result[0][:-1])
  print("[+] sending credentials ...")
  s.post(
    'https://login.esbnetworks.ie/esbntwkscustportalprdb2c01.onmicrosoft.com/B2C_1A_signup_signin/SelfAsserted?tx=' + settings['transId'] + '&p=B2C_1A_signup_signin', 
    data={
      'signInName': user, 
      'password': password, 
      'request_type': 'RESPONSE'
    },
    headers={
      'x-csrf-token': settings['csrf'],
    },
    allow_redirects=False)
  print("[+] passing AUTH ...")
  confirm_login = s.get(
    'https://login.esbnetworks.ie/esbntwkscustportalprdb2c01.onmicrosoft.com/B2C_1A_signup_signin/api/CombinedSigninAndSignup/confirmed',
    params={
      'rememberMe': False,
      'csrf_token': settings['csrf'],
      'tx': settings['transId'],
      'p': 'B2C_1A_signup_signin',
    }
  )
  print("[+] confirm_login: ",confirm_login)
  print("[+] doing some BeautifulSoup ...")
  soup = BeautifulSoup(confirm_login.content, 'html.parser')
  form = soup.find('form', {'id': 'auto'})
  s.post(
    form['action'],
    allow_redirects=False,
    data={
      'state': form.find('input', {'name': 'state'})['value'],
      'client_info': form.find('input', {'name': 'client_info'})['value'],
      'code': form.find('input', {'name': 'code'})['value'],
    }, 
  )
  
  #data = s.get('https://myaccount.esbnetworks.ie/datadub/GetHdfContent?mprn=' + mpnr + '&startDate=' + start_date.strftime('%Y-%m-%d'))
  print("[+] getting CSV file for MPRN ...")
  data = s.get('https://myaccount.esbnetworks.ie/DataHub/DownloadHdf?mprn=' + mpnr + '&startDate=' + start_date.strftime('%d-%m-%Y'))

  print("[+] CSV file received !!!")
  data_decoded = data.content.decode('utf-8').splitlines()
  print("[+] data decoded from Binary format")
  print("[+] Adding to InfluxDB (this will take a while)...")
  json_data = parse_csv(data_decoded)
  return json_data

def parse_date(date_str):
  if len(date_str) == 19:
      return datetime.strptime(date_str, '%Y-%m-%d %H:%M')
  else:
      dt = datetime.strptime(date_str[:19], '%d-%m-%Y %H:%M')
      return dt

def load_smart_meter_stats_v2(user, password, mpnr):
  #last_month = datetime.today() - timedelta(days=30)
  today_ = datetime.today()
  #smart_meter_data = load_esb_data(user, password, mpnr, last_month)
  smart_meter_data = load_esb_data(user, password, mpnr, today_)
  print("[+] smart_meter_data: ",smart_meter_data)
  print("[++] end of smart_meter_data")
  return smart_meter_data

def parse_csv(csv_file):
  my_json = []
  csv_reader = csv.DictReader(csv_file)
  for row in csv_reader:
    mprn = row['MPRN']
    value = row['Read Value']
    the_date = parse_date(row['Read Date and End Time'])
    update_influx(mprn, the_date, value)


def update_influx(mpnr, the_date, value):
  global influx_token, influx_url, influx_org, influx_bucket

  # connect to the influx server...
  write_client = influxdb_client.InfluxDBClient(url=influx_url, token=influx_token, org=influx_org, verify_ssl=0)
  write_api = write_client.write_api(write_options=SYNCHRONOUS)
  point = (
    Point("power")
    .tag("MPRN", mpnr)
    .field("usage", float(value))
    .time(the_date, write_precision="ms")
  )
  write_api.write(bucket=influx_bucket, org=influx_org, record=point)

with open("config.yml") as config_file:
  config = yaml.load(config_file, Loader=yaml.FullLoader)

meter_mprn = config["esb"]["mprn"]
esb_user_name = config["esb"]["user_name"]
esb_password = config["esb"]["password"]

influx_token = config["influx"]["token"]
influx_url = config["influx"]["url"]
influx_org = config["influx"]["org"]
influx_bucket = config["influx"]["bucket"]

xoxo = load_smart_meter_stats_v2(esb_user_name, esb_password, meter_mprn)