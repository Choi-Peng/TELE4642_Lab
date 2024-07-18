import requests
import json
import os

def get(api_url):
    try:
        # 发送GET请求获取信息
        response = requests.get(api_url)

        # 检查请求是否成功
        if response.status_code == 200:
            # 解析JSON数据
            data = response.json()

            print(json.dumps(data, indent=2))  # 格式化输出JSON
        else:
            print(f"Failed to get info, status code: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Error during requests to {api_url}: {str(e)}")

def put(api_url):
    print('put something here')

def post(api_url):
    print('post something here')

def delete(api_url):
    print('delete something here')

if __name__ == "__main__":
    while 1:
        os.system('clear')
        # 输入REST API URL
        action = input("Please enter the REST API action: ")
        urlHead = 'http://127.0.0.1:8080/'
        API = action.split()[0]
        url = action.split()[1]
        api_url = f'{urlHead}{url}'
        APIs = {
            'GET': get,
            'PUT': put,
            'POST': post,
            'DELETE': delete
        }
        APIs.get(API)(api_url)
        input()


