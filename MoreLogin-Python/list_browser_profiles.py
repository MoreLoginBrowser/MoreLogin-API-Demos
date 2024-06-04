# pip install requests pycryptodome Crypto
from base_morelogin.base_func import requestHeader, postRequest

import sys
import asyncio
import traceback

# From profile list page, click on the API button, and copy API ID and API Key to below.
APPID = '123456'
SECRETKEY = 'abcdef'
BASEURL = 'http://127.0.0.1:40000'

async def main():
    try:
        data = await getEnvList(APPID, SECRETKEY, BASEURL)
        if len(data['dataList']) > 0:
            for env in data['dataList']:
                print(env['id'] + ': ' + env['envName'])
        else:
            print('no profile found, please check your condition')

    except:
        error_message = traceback.format_exc()
        print('run-error: ' + error_message)

# get browser profile env list
async def getEnvList(appId, secretKey, baseUrl):
    requestPath = baseUrl + '/api/env/page'  
    data = { 
        'pageNo': 1,                    # env list page no
        'pageSize': 5,                  # number of profiles per page
        'envName': '',   # env name condition for search
        #'groupId': 123,                 # env group condition for search
    }
    headers = requestHeader(appId, secretKey)
    response = postRequest(requestPath, data, headers).json()

    if response['code'] != 0:
        print('error:'+ requestPath + '\r\n' + response['msg'])
        sys.exit()

    #print(response)
    return response['data']

if __name__ == '__main__':
    asyncio.run(main())