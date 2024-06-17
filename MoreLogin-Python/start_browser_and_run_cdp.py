"""
Description: 
Used to start the profile browser, then connected to the browser with cdp and try google search.
Note: To use this interface, you need to start the MoreLogin client and successfully log in.

Documentation:
https://docs.morelogin.com/l/en/interface-documentation/browser-profile#1_start_browser_profile
"""

# pip install requests playwright pycryptodome Crypto
from base_morelogin.base_func import requestHeader, postRequest

import sys
import asyncio
from playwright.async_api import async_playwright, Playwright     # async call 
import traceback

# From profile list page, click on the API button, and copy API ID and API Key to below.
APPID = '123456'
SECRETKEY = 'abcdef'
BASEURL = 'http://127.0.0.1:40000'

async def main():
    async with async_playwright() as playwright:
        await run(playwright)

async def run(playwright: Playwright):
    try:
        # browser's order num, you can get it from profile list page: Numerical order 
        uniqueId = 59
        # browser profile id, please check API-demo: list_browser_profiles.py
        envId = ''
        cdpUrl = await startEnv(envId, uniqueId, APPID, SECRETKEY, BASEURL)

        await operationEnv(cdpUrl, playwright)

        # wait 10 second
        await asyncio.sleep(10)

        # try close env
        await stopEnv(envId, uniqueId, APPID, SECRETKEY, BASEURL)
        print('env closed')

    except:
        errorMessage = traceback.format_exc()
        print('run-error: ' + errorMessage)

# start a browser profile, and return cdp-url
# if browser already opened, the browser will auto bring to front
async def startEnv(envId, uniqueId, appId, secretKey, baseUrl):
    requestPath = baseUrl + '/api/env/start'  
    # Send the envId(profile ID) or the uniqueId(profile order number). 
    # If both are sent, the profile ID takes precedence. 
    data = { 
        'envId': envId,
        'uniqueId': uniqueId
    }
    headers = requestHeader(appId, secretKey)
    response = postRequest(requestPath, data, headers).json()

    if response['code'] != 0:
        print(response['msg'])
        print('please check envId')
        sys.exit()

    port = response['data']['debugPort']
    print('env open result:', response['data'])
    cdpUrl = 'http://127.0.0.1:' + port
    return  cdpUrl

# open page and operation
async def operationEnv(cdpUrl, playwright):
        browser = await playwright.chromium.connect_over_cdp( cdpUrl )
        defaultContext = browser.contexts[0]
        
        # try open page
        page1 = await defaultContext.new_page()
        await page1.goto('https://ipinfo.io')

        page2 = await defaultContext.new_page()
        await page2.goto('https://www.google.com/')
        print(page2.title)
        await page2.fill('[name="q"]', 'MoreLogin')
        await page2.press('[name="q"]', 'Enter')
        #await page2.keyboard.press('Enter')  
        print('search executed')

        # try close and clear resource
        # await page1.close()
        # await page2.close()

# close a browser profile
async def stopEnv(envId, uniqueId, appId, secretKey, baseUrl):
    requestPath = '/api/env/close'   
    # Send the envId(profile ID) or the uniqueId(profile order number). 
    # If both are sent, the profile ID takes precedence. 
    data = { 
        'envId': envId,
        'uniqueId': uniqueId
    }
    headers = requestHeader(appId, secretKey)
    response = postRequest(baseUrl + requestPath, data, headers).json()
    if response['code'] == -1:
        return False
    return True      


if __name__ == '__main__':
    asyncio.run(main())