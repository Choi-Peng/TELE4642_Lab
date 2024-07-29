import requests
import json
import os
import sys

urlHead = 'http://127.0.0.1:8080/'

def get(api_url):
    try:
        response = requests.get(urlHead + api_url)

        if response.status_code == 200:
            data = response.json()

            print(json.dumps(data, indent=2))  

            with open('get_data.json','w') as f:
                json.dump(data, f, indent=2)
        else:
            print(f"Failed to get info, status code: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Error during requests to {api_url}: {str(e)}")

def put(data):
    try:
        print(f'data: {data}')
        method, data, url = data.split('\'', 2)
        print(method)
        print(data)
        print(url)
        if method.replace(' ', '') == '-d':
            response = requests.put(urlHead + url.replace(' ', ''), data=data)

            if response.status_code == 200:
                data = response.json()

                print(json.dumps(data, indent=2))  

                with open('get_data.json','w') as f:
                    json.dump(data, f, indent=2)
            else:
                print(f"Failed to get info, status code: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Error during requests {data}: {str(e)}")

def delete(api_url):
    try:
        response = requests.delete(urlHead + api_url)

        if response.status_code == 200:
            data = response.json()

            print(json.dumps(data, indent=2))  

            with open('get_data.json','w') as f:
                json.dump(data, f, indent=2)
        else:
            print(f"Failed to get info, status code: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Error during requests to {api_url}: {str(e)}")

if __name__ == "__main__":
    while 1:
        # 输入REST API URL
        action = input("Please enter the REST API action: ")
        if action == 'clear':
            os.system('clear')
        elif action == 'end':
            sys.exit()
        else:
            method, data = action.split(' ', 1)
            if method == 'GET':
                get(data)
            elif method == 'PUT':
                put(data)
            elif method == 'DELETE':
                delete(data)


