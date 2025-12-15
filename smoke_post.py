import urllib.request, urllib.parse, time
base='http://127.0.0.1:5000'

def post(path, data):
    url = base + path
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.getcode(), r.read().decode(errors='replace')
    except Exception as e:
        return None, repr(e)

# ensure client and country exist
post('/clients/add', {'client_name':'TraceClient2','phone_number':'000'})
post('/countries/add', {'name':'TraceLand2','price':'60'})
# trigger transaction POST
code, resp = post('/transactions/add', {
    'client_name':'TraceClient2',
    'applicant_name':'Trace Applicant',
    'app_id':'9998',
    'country_name':'TraceLand2',
    'rate':'1.5',
    'addition':'5.0',
    'transaction_date':'2025-12-05'
})
print('POST result:', code)
print(resp)
