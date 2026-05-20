import requests


# send web-request with POST
def postRequest(url, data):
    headers = {'Content-Type': 'application/json'}
    return requests.post(url, json=data, headers=headers) # .json()

# send web-request with GET
def getRequest(url, headers):
    return requests.get(url, headers=headers) # .json()
