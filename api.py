import requests
from bs4 import BeautifulSoup
import os
import numpy as np
import pandas as pd
import json
import stdiomask
from utils import *

class finnomenaAPI:
    def __init__(self, config_path = 'config', email=None, password=None):
        self.config = {}
        for f in os.listdir(config_path):
            self.config[os.path.splitext(f)[0]] = load_yaml(config_path + '/' + f)

        self.keys = self.config['keys']
        self.urls = self.keys['url']
        self.root = self.urls['root']
        self.funds_root = self.root + self.urls['fund']
        self.fees_dict = self.keys['fees_dict']

        self.email = email
        if self.email is None:
            self.password = None
        else:
            self.password = password

        # Initialize 
        self.session = requests.Session()
        self.is_login = self.check_login_status()

    def login(self):
        # check if not already logged in
        if self.is_login:
            return self.is_login

        # check if email is provided
        if self.email is None:
            print("The action requires permission to access your Finnomena account. Please provide login information.")
            self.email = input('Email: ')
            self.password = stdiomask.getpass()

        # check if password is provided:
        if self.password is None:
            print("The action requires permission to access your Finnomena account. Please provide password for account with email: " + self.email)
            self.password = stdiomask.getpass()
        
        print("Logging in to account: " + self.email + ' . . . . .')

        params = (
            ('return_url', 'https://www.finnomena.com/'),
            ('action', 'login'),
            ('device', 'web'),
        )
        response = self.session.get('https://www.finnomena.com/fn3/api/auth/loginaction', params=params)
        challenge = response.url.split('=')[-1]
        # -----------------------------------
        data = {"email":self.email,"password":str(self.password),"challenge":challenge}
        response = self.session.post('https://auth.finnomena.com/api/web/login', data=json.dumps(data))
        if not response.ok:
            raise Exception("email or password is incorrect")
            self.is_login = False
            return self.is_login
        
        response= response.json()
        response = self.session.get(response['data']['redirect_to'])
        cookies = self.session.cookies.get_dict()
        access_token = cookies['access_token']
        # -----------------------------------------
        jar = requests.cookies.RequestsCookieJar()
        jar.set('access_token',access_token)
        self.session.cookies = jar

        # Test if login successful ----------------
        self.is_login = self.check_login_status()
        if not self.is_login:
            raise Exception('Login unsuccessful')

        print("successfully logged in")
        return self.is_login

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
    
    def check_login_status(self):
        response = self.session.get('https://www.finnomena.com/fn3/api/auth/profile')
        if self.email in response.text:
            login = True
        else:
            login = False
        return login

    def get_account_status(self):
        self.login()

        response = self.session.get(self.urls['all_ports']).json()
        data = response['data']

        overall_account_gain = {
                                'market_value': data['crm']['market_value'],
                                'total_gain':  data['crm']['total_pl']['total'],
                                'realized_gain': data['crm']['total_pl']['realized'],
                                'unrealized_gain': data['crm']['total_pl']['unrealized'],
                                'dividend': data['crm']['total_pl']['dividend'],
                                'trading_gain': data['crm']['total_pl']['trading']
        }

        ports = data['crm']['accounts']
        ports_info = {}
        for port in ports:
            port_name = port['plan']['plan_name']
            ports_info[port_name] = {
                                    'plan_slot': port['plan_slot'],
                                    'nomura_id': port['agent_account_id'],
                                    'goal_id': port['goal_user_id'],
                                    'port_type': port['plan']['plan_type_display'],
                                    'market_value': port['market_value'],
                                    'total_gain': port['total_pl']['total']
            }

        result_dict = {'overall_account_gain': overall_account_gain, 'ports_info': ports_info}
        
        return result_dict
    
    def get_port_status(self, port_name):
        # Check if port_name valid
        account_status = self.get_account_status()
        ports_info = account_status['ports_info']
        if port_name not in ports_info.keys():
            ports_name_str = ', '.join(list(ports_info.keys()))
            raise Exception("Invalid port_name. Available ports for this account are: " + ports_name_str)
        
        port_info = ports_info[port_name]

        payload = {
                    'goal_user_id': port_info['goal_id'],
                    'operation': 'get'
        }

        response = self.session.get(self.urls['port'], params=payload)
        response = response.json()

        # Overal port's status
        overall = {
                    'market_value': response['PLInfo']['unrealized_pl']['sum_of_market_value'],
                    'total_gain':  float(response['PLInfo']['total_realized_amount']) + float(response['PLInfo']['unrealized_pl']['sum_of_unrealized_pl']),
                    'realized_gain': response['PLInfo']['total_realized_amount'],
                    'unrealized_gain': response['PLInfo']['unrealized_pl']['sum_of_unrealized_pl'],
                    'dividend': response['PLInfo']['dividend_amount'],
                    'trading_gain': float(response['PLInfo']['realized_amount']) + float(response['PLInfo']['unrealized_pl']['sum_of_unrealized_pl'])
        }

        # Port's historical data
        historical_value = pd.DataFrame(response['outstandingHisData'])
        historical_value = historical_value.drop(columns=['da'])
        historical_value = historical_value.rename(columns={'va':'value'})

        # Port's composition
        compositions = pd.DataFrame(response['outstandingData'])
        compositions = compositions.drop(columns=['agent','full_name_th','uid'])
        compositions = compositions.rename(columns={'asset_code':'sec_name','avg_proce':'avg_cost',
                                                    'market_price':'current_nav','profit':'return',
           
                                                    'unit_cost':'total_unit'})
        return overall, historical_value, compositions

    def get_historical_orders(self, port_name):    
        # Check if port_name valid
        account_status = self.get_account_status()
        ports_info = account_status['ports_info']
        if port_name not in ports_info.keys():
            ports_name_str = ', '.join(list(ports_info.keys()))
            raise Exception("Invalid port_name. Available ports for this account are: " + ports_name_str)
        
        port_info = ports_info[port_name]

        page_number = 1
        orders = []
        terminate = False
        while not terminate:

            payload = {
                    'plan': port_info['plan_slot'],
                    'agent_account_id': str(port_info['nomura_id']),
                    'url': '/tws/order-history/' + str(port_info['nomura_id']) + '?page=' + str(page_number)
            }

            response = self.session.get(self.urls['historical_orders'], params=payload)
            response = response.json()
            total_orders = response['message']['total']
            orders = orders + response['message']['data']

            terminate = (len(orders) >= int(total_orders))

            page_number += 1
        
        orders = pd.DataFrame(orders)
        
        return orders


    def ruin_token(self):
        """
        Only for testing. 
        """
        jar = requests.cookies.RequestsCookieJar()
        jar.set('access_token',"0000000000000")
        self.session.cookies = jar



            
