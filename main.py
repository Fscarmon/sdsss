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

ocr = ddddocr.DdddOcr()

os.makedirs("static", exist_ok=True)


def get_user_name():
    url = "http://www.ivtool.com/random-name-generater/uinames/api/index.php?region=united states&gender=female&amount=5&="
    header = {
        "Host": "www.ivtool.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Priority": "u=1",
    }
    resp = requests.get(url, headers=header, verify=False)
    print(resp.status_code)
    if resp.status_code != 200:
        print(resp.status_code, resp.text)
        raise "获取名字出错"
    data = resp.json()
    return data


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
    usernames = get_user_name()
    url1 = "https://www.serv00.com/offer/create_new_account"
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

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
        "Cookie": "csrftoken={}",
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
        "Cookie": "csrftoken={}",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=1",
    }

    _ = usernames.pop()
    first_name = _["name"]
    last_name = _["surname"]
    username = generate_random_username().lower()
    logger.info(f"{email} {first_name} {last_name} {username}")

    with requests.Session() as session:
        logger.info("获取网页信息")
        resp = session.get(url=url1, headers=header1, impersonate="chrome124")
        print(resp.status_code)
        headers = resp.headers
        content = resp.text

        csrftoken = re.findall(r"csrftoken=(\w+);", headers.get("set-cookie"))[0]
        print("csrftoken", csrftoken)
        header2["Cookie"] = header2["Cookie"].format(csrftoken)
        header3["Cookie"] = header3["Cookie"].format(csrftoken)

        captcha_0 = re.findall(r'id=\"id_captcha_0\" name=\"captcha_0\" value=\"(\w+)\">', content)[0]

        for retry in range(5):
            time.sleep(random.uniform(0.5, 1.2))
            logger.info(f"第 {retry + 1} 次尝试获取验证码")
            try:
                resp = session.get(url=captcha_url.format(captcha_0),
                                 headers=dict(header2, **{"Cookie": header2["Cookie"].format(csrftoken)}), impersonate="chrome124")
                content = resp.content
                with open("static/image.jpg", "wb") as f:
                    f.write(content)

                captcha_1 = ocr.classification(content).lower()

                if not bool(re.match(r'^[a-zA-Z0-9]{4}$', captcha_1)):
                    logger.warning(f"识别的验证码无效: {captcha_1}, 重试")
                    continue

                logger.info(f"识别的验证码: {captcha_1}")

                data = f"csrfmiddlewaretoken={csrftoken}&first_name={first_name}&last_name={last_name}&username={username}&email={quote(email)}&captcha_0={captcha_0}&captcha_1={captcha_1}&question=0&tos=on"
                time.sleep(random.uniform(0.5, 1.2))
                logger.info("请求信息")
                resp = session.post(url=url3, headers=dict(header3, **{"Cookie": header3["Cookie"].format(csrftoken)}),
                                    data=data, impersonate="chrome124")
                print(resp.status_code)
                print(resp.text)
                content = resp.json()

                if content.get("captcha") and content["captcha"][0] == "Invalid CAPTCHA":
                    captcha_0 = content["__captcha_key"]
                    logger.warning("验证码错误，正在重新获取")
                    time.sleep(random.uniform(0.5, 1.2))
                    continue
                else:
                    logger.info(f"邮箱 {email} 注册成功!")
                    return # 注册成功，直接退出该邮箱的循环

            except Exception as e:
                logger.error(f"获取验证码或提交注册信息失败: {e}")

        logger.warning(f"邮箱 {email} 注册失败，尝试下一个邮箱")
        os.remove("static/image.jpg")


if __name__ == '__main__':
    # 直接启动后台任务
    task_thread = threading.Thread(target=background_task)
    task_thread.daemon = True  # 设置为守护线程，主线程退出时自动退出
    task_thread.start()

    while True: # 保持主线程运行
        time.sleep(1) # 防止 CPU 占用过高