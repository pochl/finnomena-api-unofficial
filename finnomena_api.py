import requests
from bs4 import BeautifulSoup
import os
import numpy as np
import pandas as pd

from utils import *

class finnomenaAPI:
    def __init__(self, config_path = 'config'):
        self.config = {}
        for f in os.listdir(config_path):
            self.config[os.path.splitext(f)[0]] = load_yaml(config_path + '/' + f)

        self.keys = self.config['keys']
        self.urls = self.keys['url']
        self.root = self.urls['root']
        self.funds_root = self.root + self.urls['fund']
        self.fees_dict = self.keys['fees_dict']

    def get_fund_info(self, name):
        info = {}
        fund_url = self.funds_root + '/' + name
        page = requests.get(fund_url)

        soup = BeautifulSoup(page.content, 'html.parser')

        feeder_fund = soup.find(class_='feeder-fund').text
        sec_name = soup.find(id='sec-name').text
        mstar_id = soup.find(id='sec-id').text

        info['security_name'] = sec_name
        info['morningstar_id'] = mstar_id
        info['feeder_fund'] = feeder_fund

        fee_url = 'https://www.finnomena.com/fn3/api/fund/public/' + mstar_id + '/fee'
        fees_list = requests.get(fee_url).json()['fees']

        fees = {}
        for i in fees_list:
            if i['feetypedesc'] in self.fees_dict:

                try:
                    amount = float(i['actualvalue'])
                except:
                    amount = np.nan

                fees[self.fees_dict[i['feetypedesc']]] = amount

        info = {**info, **fees}

        return info

    def get_fund_price(self, sec_name: str, time_range = 'MAX'):
        info = self.get_fund_info(sec_name)
        mstar_id = info['morningstar_id']

        # Validate time_range (available options are 1D, 7D, 1M, 3M, 6M, 1Y, 3Y, 5Y, 10Y and MAX)
        time_range_option = ['1D', '7D', '1M', '3M', '6M', '1Y', '3Y', '5Y', '10Y', 'MAX']
        assert time_range in time_range_option

        payload = {'range':  time_range,
                   'fund': mstar_id}
        url = self.urls['fund_timeseries_price']
        temp_data = requests.get(url, params=payload).json()

        data = {'date':[], 'price':[]}
        for i in temp_data:
            data['date'].append(i['nav_date'])
            data['price'].append(i['value'])
        
        df = pd.DataFrame(data)

        return df

api = finnomenaAPI()
print(api.get_fund_info('kt-wtai-a'))
#print(api.get_fund_price('kt-wtai-a'))
