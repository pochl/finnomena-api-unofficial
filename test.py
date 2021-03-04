from api import finnomenaAPI

api = finnomenaAPI(email='the_phachara@hotmail.com', password='Poch160241')

# "the_phachara@hotmail.com", "Poch160241"
# Test get_fund_info()
#print(api.get_fund_info('tghdigi'))

# Test get_fund_price()
#print(api.get_fund_price('kt-wtai-a'))

# Test login()
# print(api.login())

# Test get_account_status()
# print(api.get_account_status())

# Test get_port_status()
# overall, historical_value, compositions = api.get_port_status("DIY")

# Test get_historical_orders()
orders = api.get_historical_orders("DIY")
print(orders)