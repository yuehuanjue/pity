import json
import time

import aiohttp
from aiohttp import FormData

from app.middleware.oss import OssClient
from config import Config


class AsyncRequest(object):

    def __init__(self, url: str, timeout=15, **kwargs):
        self.url = url
        self.kwargs = kwargs
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    def get_cookie(self, session):
        cookies = session.cookie_jar.filter_cookies(self.url)
        return {k: v.value for k, v in cookies.items()}

    async def invoke(self, method: str):
        start = time.time()
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as session:
            async with session.request(method, self.url, timeout=self.timeout, **self.kwargs) as resp:
                if resp.status != 200:
                    return await self.collect(False, self.kwargs.get("data"), resp.status)
                cost = "%.0fms" % ((time.time() - start) * 1000)
                response = await AsyncRequest.get_resp(resp)
                cookie = self.get_cookie(session)
                return await self.collect(True, self.kwargs.get("data"), resp.status, response,
                                          resp.headers, resp.request_info.headers, elapsed=cost,
                                          cookies=cookie)

    @staticmethod
    async def client(url: str, body_type: int, timeout=15, **kwargs):
        if not url.startswith(("http://", "https://")):
            raise Exception("请输入正确的url, 记得带上http哦")
        headers = kwargs.get("headers", {})
        if body_type == Config.BodyType.json:
            if "Content-Type" not in headers:
                headers['Content-Type'] = "application/json; charset=UTF-8"
            r = AsyncRequest(url, headers=headers, timeout=timeout,
                             json=kwargs.get("body"))
        elif body_type == Config.BodyType.form:
            try:
                body = kwargs.get("body")
                if body:
                    form_data = FormData()
                    # 因为存储的是字符串，所以需要反序列化
                    items = json.loads(body)
                    for item in items:
                        # 如果是文本类型，直接添加key-value
                        if item.get("type") == 'TEXT':
                            form_data.add_field(item.get("key"), item.get("value"))
                        else:
                            client = OssClient.get_oss_client()
                            file_object = await client.get_file_object(item.get("value"))
                            form_data.add_field(item.get("key"), file_object)
                else:
                    form_data = None
                r = AsyncRequest(url, headers=headers, data=form_data, timeout=timeout)
            except Exception as e:
                raise Exception(f"解析form-data失败: {str(e)}")
        elif body_type == Config.BodyType.x_form:
            body = kwargs.get("body", "{}")
            body = json.loads(body)
            r = AsyncRequest(url, headers=headers, data=body, timeout=timeout)
        else:
            # 暂时未支持其他类型
            r = AsyncRequest(url, headers=headers, timeout=timeout, data=kwargs.get("body"))
        return r

    @staticmethod
    async def get_resp(resp):
        try:
            data = await resp.json(encoding='utf-8')
            return json.dumps(data, ensure_ascii=False, indent=4)
        except:
            data = await resp.text()
            return data

    @staticmethod
    def get_request_data(body):
        request_body = body
        if isinstance(body, bytes):
            request_body = request_body.decode()
        if isinstance(body, FormData):
            request_body = str(body)
        if isinstance(request_body, str) or request_body is None:
            return request_body
        return json.dumps(request_body, ensure_ascii=False)

    @staticmethod
    async def collect(status, request_data, status_code=200, response=None, response_headers=None,
                      request_headers=None, cookies=None, elapsed=None, msg="success"):
        """
        收集http返回数据
        :param status: 请求状态
        :param request_data: 请求入参
        :param status_code: 状态码
        :param response: 相应
        :param response_headers: 返回header
        :param request_headers:  请求header
        :param cookies:  cookie
        :param elapsed: 耗时
        :param msg: 报错信息
        :return:
        """
        request_headers = json.dumps({k: v for k, v in request_headers.items()} if request_headers is not None else {},
                                     ensure_ascii=False)
        response_headers = json.dumps(
            {k: v for k, v in response_headers.items()} if response_headers is not None else {},
            ensure_ascii=False)
        cookies = {k: v for k, v in cookies.items()} if cookies is not None else {}
        cookies = json.dumps(cookies, ensure_ascii=False)
        return {
            "status": status, "response": response, "status_code": status_code,
            "request_data": AsyncRequest.get_request_data(request_data),
            "response_headers": response_headers, "request_headers": request_headers,
            "msg": msg, "cost": elapsed, "cookies": cookies,
        }
