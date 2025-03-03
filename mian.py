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
import brotli
import gzip

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

    try:
        with requests.Session() as session:

            header_base = {  # 获取cookie
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
            url_base = "https://www.serv00.com"
            logger.info(f"请求URL: {url_base}")
            resp_base = session.get(url_base, headers=header_base, impersonate="chrome124")
            logger.info(f"获取基础页面状态码: {resp_base.status_code}")

            if resp_base.status_code != 200:
                logger.error(f"获取基础页面失败，状态码: {resp_base.status_code}, 响应内容: {resp_base.text}")
                raise Exception(f"获取基础页面失败，状态码: {resp_base.status_code}")
            cookie = resp_base.headers.get("set-cookie")
            logger.info(f"获取Cookie: {cookie}")

            try:
                usernames = get_user_name()
            except Exception as e:
                logger.error(f"获取用户名失败: {e}")
                return

            _ = usernames.pop()
            first_name = _["name"]
            last_name = _["surname"]
            username = generate_random_username().lower()
            logger.info(f"{email} {first_name} {last_name} {username}")

            url_create_account = "https://www.serv00.com/offer/create_new_account.json"
            header_create_account = {  # 替换成你浏览器复制的header
                "Host": "www.serv00.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "https://www.serv00.com",
                "Connection": "keep-alive",
                "Referer": "https://www.serv00.com/offer/create_new_account",
                "Cookie": cookie,
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",

            }
            #header_create_account.pop("Accept-Encoding", None)  # 确保移除 Accept-Encoding

            logger.info(f"请求URL: {url_create_account}")
            resp_create_account = session.get(url_create_account, headers=header_create_account,
                                              impersonate="chrome124", allow_redirects=False) # disable redirects
            logger.info(f"获取 captcha_0 状态码: {resp_create_account.status_code}")

            content_create_account = None # 初始化变量
            try:
                if resp_create_account.status_code == 200 and resp_create_account.content:
                    content_encoding = resp_create_account.headers.get('Content-Encoding', '')

                    if content_encoding:
                        logger.warning(f"响应使用了 Content-Encoding: {content_encoding}, 但不应该有. ")

                    if 'gzip' in content_encoding:
                        try:
                            content_create_account = gzip.decompress(resp_create_account.content).decode('utf-8')
                            logger.info("使用 gzip 解压缩成功")
                        except Exception as e:
                            logger.error(f"gzip 解压缩失败: {e}, 响应内容 (前 100 个字符): {resp_create_account.text[:100]}")

                    elif 'br' in content_encoding:
                        try:
                            content_create_account = brotli.decompress(resp_create_account.content).decode('utf-8')  # 需要 pip install brotli
                            logger.info("使用 brotli 解压缩成功")
                        except Exception as e:
                            logger.error(f"brotli 解压缩失败: {e}, 响应内容 (前 100 个字符): {resp_create_account.text[:100]}")
                    else:
                        content_create_account = resp_create_account.text
                        logger.info("未使用 gzip 或 brotli 压缩")


                    if content_create_account:
                        try:
                            content_create_account = eval(content_create_account)
                            captcha_0 = content_create_account["__captcha_key"]
                            logger.info(f"提取captcha_0成功: {captcha_0}")
                        except (KeyError, SyntaxError, TypeError) as e:
                             logger.error(f"eval解析content失败，content: {content_create_account}, 错误信息：{str(e)}")
                             #如果eval失败，走正则提取
                             captcha_0_match = re.search(r'"__captcha_key":\s*"([^"]+)"', resp_create_account.text[:100])
                             if captcha_0_match:
                                 captcha_0 = captcha_0_match.group(1)
                                 logger.info(f"正则提取captcha_0成功: {captcha_0}")
                             else:
                                 logger.error(f"正则提取captcha_0失败")
                                 raise Exception(f"提取captcha_0失败：{str(e)}")
                    else:
                        raise Exception(f"解压后内容为空")

                else:
                    logger.error(f"获取 captcha_0 失败，状态码: {resp_create_account.status_code}, 响应内容为空或错误")
                    raise Exception(f"获取 captcha_0 失败，状态码: {resp_create_account.status_code}， 响应内容为空或错误")


            except Exception as e: # 确保这个 except 块正确地缩进
                logger.error(f"获取 cookie 或 captcha_0 失败: {e}")
                return


            # 3. 构建验证码图片URL
            captcha_url = f"https://www.serv00.com/captcha/image/{captcha_0}/"
            logger.info(f"验证码图片URL: {captcha_url}")

            header_captcha = {
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

            for retry in range(5):
                time.sleep(random.uniform(0.5, 1.2))
                logger.info(f"第 {retry + 1} 次尝试获取验证码")
                try:
                    logger.info(f"请求验证码图片URL: {captcha_url}")
                    resp_captcha = session.get(captcha_url, headers=header_captcha, impersonate="chrome124", allow_redirects=False)

                    logger.info(f"获取验证码图片状态码: {resp_captcha.status_code}")
                    if resp_captcha.status_code != 200:
                        logger.error(f"获取验证码图片失败，状态码: {resp_captcha.status_code}, 响应内容: {resp_captcha.text}")
                        raise Exception(f"获取验证码图片失败，状态码: {resp_captcha.status_code}")

                    content_captcha = resp_captcha.content
                    with open("static/image.jpg", "wb") as f:
                        f.write(content_captcha)

                    captcha_1 = ocr.classification(content_captcha).lower()
                    logger.info(f"OCR识别结果: {captcha_1}")

                    if not bool(re.match(r'^[a-zA-Z0-9]{4}$', captcha_1)):
                        logger.warning(f"识别的验证码无效: {captcha_1}, 重试")
                        continue

                    logger.info(f"识别的验证码: {captcha_1}")

                    # 4. 构建并提交表单数据
                    url_submit = "https://www.serv00.com/offer/create_new_account.json"
                    header_submit = {
                        "Host": "www.serv00.com",
                        "User-Agent": ua,
                        "Accept": "*/*",
                        "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
                        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                        "X-Requested-With": "XMLHttpRequest",
                        "Origin": "https://www.serv00.com",
                        "Connection": "keep-alive",
                        "Referer": "https://www.serv00.com/offer/create_new_account",
                        "Cookie": cookie,
                        "Sec-Fetch-Dest": "empty",
                        "Sec-Fetch-Mode": "cors",
                        "Sec-Fetch-Site": "same-origin",
                        "Priority": "u=1",
                    }
                    data = f"first_name={first_name}&last_name={last_name}&username={username}&email={quote(email)}&captcha_0={captcha_0}&captcha_1={captcha_1}&question=0&tos=on"
                    logger.info(f"POST 数据: {data}")

                    logger.info(f"请求URL: {url_submit}")
                    resp_submit = session.post(url_submit, headers=header_submit, data=data,
                                                    impersonate="chrome124", allow_redirects=False)

                    logger.info(f"提交注册信息状态码: {resp_submit.status_code}")
                    if resp_submit.status_code != 200:
                        logger.error(f"提交注册信息失败，状态码: {resp_submit.status_code}, 响应内容: {resp_submit.text}")
                        raise Exception(f"提交注册信息失败，状态码: {resp_submit.status_code}")

                    try:
                        content_submit = resp_submit.json()
                        logger.info(f"提交注册信息响应: {content_submit}")

                        if content_submit.get("captcha") and content_submit["captcha"][0] == "Invalid CAPTCHA":
                            logger.warning("验证码错误，正在重新获取")
                            time.sleep(random.uniform(0.5, 1.2))
                            continue
                        else:
                            logger.info(f"邮箱 {email} 注册成功!")
                            return
                except Exception as e:
                    logger.error(f"解析 JSON 失败: {e}, 响应内容: {resp_submit.text}")
                    raise

                except Exception as e:
                    logger.error(f"获取验证码或提交注册信息失败: {e}")

            logger.warning(f"邮箱 {email} 注册失败，尝试下一个邮箱")
            try:
                os.remove("static/image.jpg")
            except FileNotFoundError:
                logger.warning("验证码图片不存在，可能未成功生成")

    except Exception as e:
        logger.error(f"获取 cookie 或 captcha_0 失败: {e}")
        return


if __name__ == '__main__':
    # 直接启动后台任务
    task_thread = threading.Thread(target=background_task)
    task_thread.daemon = True  # 设置为守护线程，主线程退出时自动退出
    task_thread.start()

    while True:  # 保持主线程运行
        time.sleep(1)  # 防止 CPU 占用过高