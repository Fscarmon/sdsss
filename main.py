# -*- coding: utf-8 -*-
import os
import string
import random
import re
import time
import ddddocr
from curl_cffi import requests
from urllib.parse import quote
from loguru import logger
import threading
from faker import Faker

ocr = ddddocr.DdddOcr()
fake = Faker()

os.makedirs("static", exist_ok=True)


def get_user_name():
    names = []
    for _ in range(5):
        try:
            name = fake.name()
            first_name = name.split(" ")[0]
            last_name = name.split(" ")[-1]
            names.append({"name": first_name, "surname": last_name})
        except Exception as e:
            logger.error(f"生成随机姓名失败: {e}")
            # 可选: 使用备用方案 (例如, 本地姓名列表)
            first_name = random.choice(["Alice", "Bob"])
            last_name = random.choice(["Smith", "Jones"])
            names.append({"name": first_name, "surname": last_name})
    return names


def generate_random_username():
    length = random.randint(7, 10)
    characters = string.ascii_letters
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string


def generate_random_email_prefix(length=20):
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def background_task():
    email_domains_str = os.environ.get("EMAIL_DOMAIN")
    if not email_domains_str:
        logger.error("EMAIL_DOMAIN 环境变量未设置")
        return

    email_domains = [domain.strip() for domain in email_domains_str.split(';')]
    logger.info(f"使用邮箱后缀: {email_domains}")

    for email_domain in email_domains:
        for _ in range(20):
            email_prefix = generate_random_email_prefix()
            email = f"{email_prefix}@{email_domain}"
            logger.info(f"开始注册邮箱: {email}")
            try:
                register_email(email)  # 移动到 try 块内
            except Exception as e:
                logger.error(f"注册邮箱 {email} 失败: {e}")
                continue


def register_email(email):
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

    # 1. 从 https://www.serv00.com 获取 cookie
    url_base = "https://www.serv00.com"
    header_base = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Priority": "u=1",
    }

    logger.info(f"请求URL: {url_base}")  # 记录请求URL
    try:
        with requests.Session() as session:  # 使用Session 管理cookie
            resp_base = session.get(url_base, headers=header_base, impersonate="chrome124")
            logger.info(f"获取基础页面状态码: {resp_base.status_code}")  # 记录状态码
            if resp_base.status_code != 200:
                logger.error(f"获取基础页面失败，状态码: {resp_base.status_code}, 响应内容: {resp_base.text}")
                raise Exception(f"获取基础页面失败，状态码: {resp_base.status_code}")

            headers_base = resp_base.headers
            content_base = resp_base.text

            # 获取完整的 Cookie 字符串
            cookie = headers_base.get("set-cookie")
            logger.info(f"获取Cookie: {cookie}")

            try:
                usernames = get_user_name()
            except Exception as e:
                logger.error(f"获取用户名失败: {e}")
                return  # 如果获取用户名失败，直接返回

            _ = usernames.pop()
            first_name = _["name"]
            last_name = _["surname"]
            username = generate_random_username().lower()
            logger.info(f"{email} {first_name} {last_name} {username}")

            # 2. 使用获取的 cookie 访问 url1 和 url3
            url1 = "https://www.serv00.com/offer/create_new_account"

            header1 = {
                "Host": "www.serv00.com",
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
                "Connection": "keep-alive",
                "Referer": "https://www.serv00.com/offer",
                "Sec-GPC": "1",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Priority": "u=1",
                "Cookie": cookie  # 使用获取的 cookie
            }
            captcha_url = "https://www.serv00.com/captcha/image/{}/"
            header2 = {
                "Host": "www.serv00.com",
                "User-Agent": ua,
                "Accept": "image/avif,image/webp,*/*",
                "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
                "Sec-GPC": "1",
                "Connection": "keep-alive",
                "Referer": "https://www.serv00.com/offer/create_new_account",
                "Cookie": cookie,  # 使用获取的 cookie
                "Sec-Fetch-Dest": "image",
                "Sec-Fetch-Mode": "no-cors",
                "Sec-Fetch-Site": "same-origin",
                "Priority": "u=4",
                "TE": "trailers",
            }

            url3 = "https://www.serv00.com/offer/create_new_account.json"
            header3 = {
                "Host": "www.serv00.com",
                "User-Agent": ua,
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "https://www.serv00.com",
                "Connection": "keep-alive",
                "Referer": "https://www.serv00.com/offer/create_new_account",
                "Cookie": cookie,  # 使用获取的 cookie
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Priority": "u=1",
            }

            logger.info(f"请求URL: {url1}")  # 记录请求URL
            resp = session.get(url=url1, headers=header1, impersonate="chrome124")
            logger.info(f"获取网页信息状态码: {resp.status_code}")  # 记录状态码
            if resp.status_code != 200:
                logger.error(f"获取网页信息失败，状态码: {resp.status_code}, 响应内容: {resp.text}")
                raise Exception(f"获取网页信息失败，状态码: {resp.status_code}")

            # headers = resp.headers  #  不再需要从这里获取， 已经从 url_base 获取
            content = resp.text

            try:
                captcha_0 = re.findall(r'id=\"id_captcha_0\" name=\"captcha_0\" value=\"(\w+)\">', content)[0]
                logger.info(f"提取captcha_0成功: {captcha_0}")  # 记录提取的captcha_0
            except IndexError:
                logger.error(f"提取captcha_0失败，content: {content}")
                raise Exception("提取captcha_0失败")

            for retry in range(5):
                time.sleep(random.uniform(0.5, 1.2))
                logger.info(f"第 {retry + 1} 次尝试获取验证码")
                try:
                    captcha_url_formatted = captcha_url.format(captcha_0)
                    logger.info(f"请求验证码图片URL: {captcha_url_formatted}")  # 记录验证码图片URL
                    resp = session.get(url=captcha_url_formatted,
                                         headers=header2, impersonate="chrome124")  # header2 直接使用 cookie

                    logger.info(f"获取验证码图片状态码: {resp.status_code}")  # 记录状态码
                    if resp.status_code != 200:
                        logger.error(f"获取验证码图片失败，状态码: {resp.status_code}, 响应内容: {resp.text}")
                        raise Exception(f"获取验证码图片失败，状态码: {resp.status_code}")

                    content = resp.content
                    with open("static/image.jpg", "wb") as f:
                        f.write(content)

                    captcha_1 = ocr.classification(content).lower()
                    logger.info(f"OCR识别结果: {captcha_1}")

                    if not bool(re.match(r'^[a-zA-Z0-9]{4}$', captcha_1)):
                        logger.warning(f"识别的验证码无效: {captcha_1}, 重试")
                        continue

                    logger.info(f"识别的验证码: {captcha_1}")

                    data = f"csrfmiddlewaretoken=&first_name={first_name}&last_name={last_name}&username={username}&email={quote(email)}&captcha_0={captcha_0}&captcha_1={captcha_1}&question=0&tos=on"
                    logger.info(f"POST 数据: {data}")  # 记录POST数据
                    time.sleep(random.uniform(0.5, 1.2))
                    logger.info("请求信息")
                    logger.info(f"请求URL: {url3}")  # 记录请求URL
                    resp = session.post(url=url3, headers=header3,  # header3 直接使用 cookie
                                        data=data, impersonate="chrome124")

                    logger.info(f"提交注册信息状态码: {resp.status_code}")  # 记录状态码
                    if resp.status_code != 200:
                        logger.error(f"提交注册信息失败，状态码: {resp.status_code}, 响应内容: {resp.text}")
                        raise Exception(f"提交注册信息失败，状态码: {resp.status_code}")

                    print(resp.text)
                    content = resp.json()
                    logger.info(f"提交注册信息响应: {content}")

                    if content.get("captcha") and content["captcha"][0] == "Invalid CAPTCHA":
                        captcha_0 = content["__captcha_key"]
                        logger.warning("验证码错误，正在重新获取")
                        time.sleep(random.uniform(0.5, 1.2))
                        continue
                    else:
                        logger.info(f"邮箱 {email} 注册成功!")
                        return  # 注册成功，直接退出该邮箱的循环

                except Exception as e:
                    logger.error(f"获取验证码或提交注册信息失败: {e}")

            logger.warning(f"邮箱 {email} 注册失败，尝试下一个邮箱")
            os.remove("static/image.jpg")

    except Exception as e:
        logger.error(f"获取 cookie 失败: {e}")
        return


if __name__ == '__main__':
    # 直接启动后台任务
    task_thread = threading.Thread(target=background_task)
    task_thread.daemon = True  # 设置为守护线程，主线程退出时自动退出
    task_thread.start()

    while True:  # 保持主线程运行
        time.sleep(1)  # 防止 CPU 占用过高