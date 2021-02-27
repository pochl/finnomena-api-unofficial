import requests
from bs4 import BeautifulSoup
import lxml.html
#?plan=1&agent_account_id=888211000111&url=/tws/order-history/888211000111?page=1


url = 'https://www.finnomena.com/wp-content/plugins/finno-tws-frontend/services/tws/get-api.php'
#url = 'https://www.finnomena.com/wp-content/plugins/finno-tws-frontend/services/tws/get-api.php?plan=1&agent_account_id=888211000111&url=/tws/order-history/888211000111'


# payload = {'plan':1,
#            'agent_account_id':888211000111,
#            'url': '/tws/order-history/888211000111'}

# temp_data = requests.get(url, params=payload).json()

session = requests.Session()
# print(temp_data)
login_url = 'https://auth.finnomena.com/login' #?challenge=c710a8742a7c48ffa58b79bd0cb7ccc9'

# login = session.get(login_url)
# login_html = lxml.html.fromstring(login.text)
# hidden_inputs = login_html.xpath('//form//input[@type="hidden"]')
# form = {x.attrib["name"]: x.attrib["value"] for x in hidden_inputs}
# print(hidden_inputs)
#print(html)
# Start the session


# Create the payload
payload = {'email':'the_phachara@hotmail.com'}

# Post the payload to the site to log in
# s = session.post(login_url, data=payload)
# s = session.get(login_url)
#print(s.content)
#print(s)

#login_url = 'https://auth.finnomena.com/email-login?email=the_phachara%40hotmail.com'

s = session.get(login_url)
soup = BeautifulSoup(s.text, 'html.parser')
#print(soup)

payload = {'current_password':'Poch160241'}

# Post the payload to the site to log in
s = session.post(login_url, data=payload)

#print(s)

url = 'https://www.finnomena.com/nter-dashboard/?goal_slot=1'
url = 'https://www.finnomena.com/fn3/api/auth/profile'

#url = 'https://www.finnomena.com/wp-content/plugins/finno-tws-frontend/services/tws/get-api.php?plan=1&agent_account_id=888211000111&url=/tws/order-history/888211000111'


# payload = {'page':  2}

# temp_data = session.get(url, params=payload).json()

url = 'https://www.finnomena.com/fund/kt-wtai-a'
# Navigate to the next page and scrape the data
s = session.get(url)#.jason

soup = BeautifulSoup(s.content, 'html.parser')

#search = soup.find(id='sec-id').text
#search = soup.find(class_='feeder-fund').text
#soup.find('img')['src']
search = soup.find(class_='detail-right').find(class_='detail-row').find(class_='right')#.text

print(search)