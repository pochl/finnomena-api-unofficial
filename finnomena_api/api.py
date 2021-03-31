import os
import json

import requests
import pandas as pd
import getpass
import numpy as np
from bs4 import BeautifulSoup
from finnomena_api.utils import load_yaml, remove_nonEng

from finnomena_api.keys import keys

class finnomenaAPI:
    def __init__(self, email=None, password=None):
        self.keys = keys

        self.email = email
        if self.email is None:
            self.password = None
        else:
            self.password = password

        # Initialize 
        self.session = requests.Session()
        self.is_login = self.check_login_status()

    def login(self):
        """
        A function to login to finnomena account by the given email and password

        Returns:
            self.is_login (bool): the login status (True = logged in, False = not logged in)
        """
        # check if not already logged in
        if self.is_login:
            return self.is_login

        # check if email is provided
        if self.email is None:
            print("The action requires permission to access your Finnomena account. Please provide login information.")
            self.email = input('Email: ')
            self.password = str(getpass.getpass('Password: '))

        # check if password is provided:
        if self.password is None:
            print("The action requires permission to access your Finnomena account. Please provide password for account with email: " + self.email)
            self.password = str(getpass.getpass('Password: '))
        
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
    
    def check_login_status(self):
        """
        A function to check the login status

        Returns:
            login (bool): the login status (True = logged in, False = not logged in)
        """
        response = self.session.get('https://www.finnomena.com/fn3/api/auth/profile')
        if self.email is None:
            login = False
        else:
            if self.email in response.text:
                login = True
            else:
                login = False
    
        return login

    def get_fund_list(self):
        """
        A function to get a list of all funds available for searching in finnomena.com

        Returns:
            funds (pandas.DataFrame): A dataframe of all funds
        """
        funds = requests.get('https://www.finnomena.com/fn3/api/fund/public/list').json()
        funds = pd.DataFrame(funds)
        return funds



    def get_fund_info(self, sec_name):
        """
        A function to get basic information of a given fund. The informations are:
        1. the code name of the fund
        2. fund's ID in morningstar.com
        3. it's feeder fund (if any)
        4. the fees (e.g. purchase fee, redemption fee, management fee, etc)

        **This function does NOT require logging in.**

        Args:
            sec_name (str): the fund's code name (e.g. KT-WTAI-A, TMBCOF)
        
        Returns:
            info (dict): dictionary containing the fund's information

        """
        sec_name = str(sec_name)

        info = {}
        fund_url = self.keys['url']['fund'] + '/' + sec_name
        page = requests.get(fund_url)

        soup = BeautifulSoup(page.content, 'html.parser')

        sec_name_found = soup.find(id='sec-name')
        if sec_name_found is None:
            raise ValueError("Cannot find fund with name '" + sec_name + "'. Check the list of available funds by method get_fund_list() or make sure fund's code name is spelled correctly")
        sec_name_found = sec_name_found.text

        feeder_fund = soup.find(class_='feeder-fund')
        if feeder_fund is not None:
            feeder_fund = feeder_fund.text
            feeder_fund = remove_nonEng(feeder_fund)

        mstar_id = soup.find(id='sec-id').text

        info['security_name'] = sec_name_found
        info['morningstar_id'] = mstar_id
        info['feeder_fund'] = feeder_fund
        # ----------------------------------------------------------------
        payload = {'fund':mstar_id}
        other_info = requests.get('https://www.finnomena.com/fn3/api/fund/nav/latest', params=payload).json()
        info['nav_date'] = other_info['nav_date']
        info['current_price'] = other_info['value']
        info['total_amount'] = other_info['amount']
        info['d_change'] = other_info['d_change']
        # ----------------------------------------------------------------

        fee_url = 'https://www.finnomena.com/fn3/api/fund/public/' + mstar_id + '/fee'
        fees_list = requests.get(fee_url).json()['fees']

        fees = {v:None for v in self.keys['fees_dict'].values()}
        for i in fees_list:
            if i['feetypedesc'] in self.keys['fees_dict']:

                try:
                    amount = float(i['actualvalue'])
                except:
                    amount = np.nan

                fees[self.keys['fees_dict'][i['feetypedesc']]] = amount
        # ----------------------------------------------------------------

        info = {**info, **fees}

        return info

    def get_fund_price(self, sec_name: str, time_range = 'MAX'):
        """
        A function to get historical price of a given fund.

        **This function does NOT require logging in.**

        Args:
            sec_name (str): the fund's code name (e.g. KT-WTAI-A, TMBCOF)
            time_range (str, optional): time frame to get the fund's price. 
                                        E.g. setting time_range = '1Y' will return the price of the fund since a year ago until today. 
                                        If not given, it will return all of the available data (price since inception)
        
        Returns:
            price (pandas.Dataframe): a dataframe of fund's price in timeseries 

        """
        sec_name = str(sec_name)
        time_range = str(time_range)

        info = self.get_fund_info(sec_name)
        mstar_id = info['morningstar_id']

        # Validate time_range (available options are 1D, 7D, 1M, 3M, 6M, 1Y, 3Y, 5Y, 10Y and MAX)
        time_range_option = ['1D', '7D', '1M', '3M', '6M', '1Y', '3Y', '5Y', '10Y', 'MAX']
        if time_range not in time_range_option:
            raise ValueError('time_range is not valid. The options are ' + ', '.join(time_range_option))

        payload = {'range':  time_range,
                   'fund': mstar_id}
        url = self.keys['url']['fund_timeseries_price']
        temp_data = requests.get(url, params=payload).json()

        data = {'date':[], 'price':[]}
        for i in temp_data:
            data['date'].append(i['nav_date'])
            data['price'].append(i['value'])
        
        price = pd.DataFrame(data)

        return price

    def get_account_status(self):
        """
        A function to get a current status of the given finnomena account. The 'status' are:
        1. overall value and gain/loss
        2. portfolios under this account and their overall value, gain/loss

        **This function REQUIRES logging in.**

        Returns:
            result_dict (dict): a dictionary containing the current status of the account

        """

        self.login()

        response = self.session.get(self.keys['url']['all_ports']).json()
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
        """
        A function to get a current status of a portfolio under the given finnomena account. The 'status' are:
        1. overall value and gain/loss of the port
        2. historical data (value/cost) of the port
        3. the assets within the port and their prices

        **This function REQUIRES logging in.**

        Args:
            port_name (str): the name of the portfolio to get the status

        Returns:
            overall (dict): a dictionary containing the currentoverall value and gain/loss of the port
            historical_value (pandas.DataFrame): a dataframe of historical data of the port
            compositions (pandas.DataFrame): a dataframe of the assets within the port
        """
        port_name = str(port_name)

        # Check if port_name valid
        account_status = self.get_account_status()
        ports_info = account_status['ports_info']
        if port_name not in ports_info.keys():
            ports_name_str = ', '.join(list(ports_info.keys()))
            raise ValueError("Invalid port_name. Available ports for this account are: " + ports_name_str)
        
        port_info = ports_info[port_name]

        payload = {
                    'goal_user_id': port_info['goal_id'],
                    'operation': 'get'
        }

        response = self.session.get(self.keys['url']['port'], params=payload)
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

    def get_order_history(self, port_name):  
        """
        A function to get the order history of a portfolio in the given account 

        **This function REQUIRES logging in.**

        Args:
            port_name (str): the name of the portfolio to get the order history

        Returns:
            orders (pandas.DataFrame): dataframe of the order history
        """  
        port_name = str(port_name)

        # Check if port_name valid
        account_status = self.get_account_status()
        ports_info = account_status['ports_info']
        if port_name not in ports_info.keys():
            ports_name_str = ', '.join(list(ports_info.keys()))
            raise ValueError("Invalid port_name. Available ports for this account are: " + ports_name_str)
        
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

            response = self.session.get(self.keys['url']['historical_orders'], params=payload)
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



            
