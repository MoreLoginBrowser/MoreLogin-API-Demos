import time
import hashlib
import random
import string
import requests

# count auth info for web-request
def requestHeader(appId, secretKey):
    nonceId = generateNonceId()
    md5Str = md5Encode(nonceId, appId, secretKey)
    return {
        'X-Api-Id': appId,
        'Authorization': md5Str,
        'X-Nonce-Id': nonceId
    }

# generate a random string
def generateRandom(length=6):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string

# count globally unique ID
def generateNonceId():
    return str(int(time.time()* 1000)) + generateRandom()

# count signature parameter
def md5Encode(nonceId, appId, secretKey):
    md5 = hashlib.md5()
    md5.update((appId + nonceId + secretKey).encode('utf-8'))
    return md5.hexdigest() 

# send web-request with POST
def postRequest(url, data, headers):
    headers['Content-Type'] = 'application/json'
    return requests.post(url, json=data, headers=headers) # .json()

# send web-request with GET
def getRequest(url, headers):
    return requests.get(url, headers=headers) # .json()
