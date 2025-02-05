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
from PIL import Image  # Import Pillow (PIL) for image processing
import io
from queue import Queue

ocr = ddddocr.DdddOcr()
fake = Faker()

os.makedirs("static", exist_ok=True)

NUM_THREADS = 50  # 线程数量
EMAIL_QUEUE = Queue() # 邮箱队列

# User-Agent 列表，可以根据需要扩充
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
    # ... 更多 User-Agent
]


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


def register_email(email, ua):
    """注册邮箱，传入邮箱地址和 User-Agent"""
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
            try:
                resp_base = session.get(url_base, headers=header_base, impersonate="chrome124")
                resp_base.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            except requests.RequestException as e:
                logger.error(f"获取基础页面失败: {e}")
                return

            logger.info(f"获取基础页面状态码: {resp_base.status_code}")
            cookie = resp_base.headers.get("set-cookie")
            logger.info(f"获取Cookie: {cookie}")

            if not cookie:
                logger.warning("没有获取到 Cookie，可能需要检查请求或服务器行为。")
                return

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
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",

            }

            try:
                resp_create_account = session.get(url_create_account, headers=header_create_account,
                                                  impersonate="chrome124")
                resp_create_account.raise_for_status()
            except requests.RequestException as e:
                logger.error(f"获取 captcha_0 失败: {e}")
                return

            logger.info(f"获取 captcha_0 状态码: {resp_create_account.status_code}")

            content_create_account = resp_create_account.text

            try:
                content_create_account = eval(content_create_account)
                captcha_0 = content_create_account["__captcha_key"]
                logger.info(f"提取captcha_0成功: {captcha_0}")
            except (KeyError, SyntaxError, TypeError) as e:
                logger.error(f"提取captcha_0失败，content: {content_create_account}, 错误信息：{str(e)}")
                raise Exception(f"提取captcha_0失败：{str(e)}")

            # 3. 构建验证码图片URL
            captcha_url = f"https://www.serv00.com/captcha/image/{captcha_0}/"
            logger.info(f"验证码图片URL: {captcha_url}")

            # **关键更改：使用与 JSON 请求相同的 Headers**
            image_headers = header_create_account  # 使用与获取 JSON 相同的 Headers

            for retry in range(5):
                time.sleep(random.uniform(0.5, 1.2))
                logger.info(f"第 {retry + 1} 次尝试获取验证码")
                try:
                    logger.info(f"请求验证码图片URL: {captcha_url}")
                    resp_captcha = session.get(captcha_url, headers=image_headers, impersonate="chrome124") # 使用相同的Headers

                    resp_captcha.raise_for_status() # 检查状态码

                    content_captcha = resp_captcha.content

                    # 使用 io.BytesIO 从内存中读取图像数据
                    image_stream = io.BytesIO(content_captcha)
                    try:
                        img = Image.open(image_stream)

                        # 使用 Pillow 保存图像
                        img.save("static/image.jpg")
                    except Exception as e:
                        logger.error(f"保存图片失败: {e}")
                        continue

                    captcha_1 = ocr.classification(content_captcha).lower()
                    logger.info(f"OCR识别结果: {captcha_1}")

                    if not bool(re.match(r'^[a-zA-Z0-9]{4}$', captcha_1)):
                        logger.warning(f"识别的验证码无效: {captcha_1}, 重试")
                        continue

                    logger.info(f"识别的验证码: {captcha_1}")

                    # 4. 构建并提交表单数据
                    url_submit = "https://www.serv00.com/offer/create_new_account.json"

                    # **重要：使用与之前相同的 header_create_account 来提交注册**
                    submit_headers = header_create_account # 使用相同的header

                    data = f"first_name={first_name}&last_name={last_name}&username={username}&email={quote(email)}&captcha_0={captcha_0}&captcha_1={captcha_1}&question=0&tos=on"
                    logger.info(f"POST 数据: {data}")

                    logger.info(f"请求URL: {url_submit}")
                    resp_submit = session.post(url_submit, headers=submit_headers, data=data,
                                                impersonate="chrome124")

                    resp_submit.raise_for_status()  # 检查状态码

                    logger.info(f"提交注册信息状态码: {resp_submit.status_code}")

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
                    logger.error(f"获取验证码或提交注册信息失败: {e}")
                finally:
                    # 无论成功与否，删除图片
                    if os.path.exists("static/image.jpg"):
                        os.remove("static/image.jpg")
                    else:
                        logger.warning("图片 static/image.jpg 不存在，无法删除")


            logger.warning(f"邮箱 {email} 注册失败，尝试下一个邮箱")


    except Exception as e:
        logger.error(f"获取 cookie 或 captcha_0 失败: {e}")
        return

def worker():
    """线程 worker 函数，从队列中获取邮箱并进行注册"""
    while True:
        email = EMAIL_QUEUE.get()  # 从队列中获取邮箱
        if email is None:
            break  # 如果队列为空，则退出线程

        ua = random.choice(USER_AGENTS)  # 为当前线程随机选择一个 User-Agent
        logger.info(f"线程 {threading.current_thread().name} 使用 User-Agent: {ua}，开始注册邮箱: {email}")
        try:
            register_email(email, ua)  # 调用注册邮箱函数，传入邮箱和 User-Agent
        except Exception as e:
            logger.error(f"线程 {threading.current_thread().name} 注册邮箱 {email} 失败: {e}")
        finally:
            EMAIL_QUEUE.task_done() # 标记任务完成

def main():
    """主函数，负责初始化邮箱队列和启动线程"""
    email_domains_str = os.environ.get("EMAIL_DOMAIN")
    if not email_domains_str:
        logger.error("EMAIL_DOMAIN 环境变量未设置")
        return

    email_domains = [domain.strip() for domain in email_domains_str.split(';')]
    logger.info(f"使用邮箱后缀: {email_domains}")

    # 填充邮箱队列
    for email_domain in email_domains:
        for _ in range(20): #原来是20
            email_prefix = generate_random_email_prefix()
            email = f"{email_prefix}@{email_domain}"
            EMAIL_QUEUE.put(email)

    # 启动多个线程
    threads = []
    for i in range(NUM_THREADS):
        t = threading.Thread(target=worker, name=f"Thread-{i+1}")
        t.daemon = True  # 设置为守护线程
        threads.append(t)
        t.start()

    # 等待队列中的所有任务完成
    EMAIL_QUEUE.join()

    # 停止 worker 线程
    for _ in range(NUM_THREADS):
        EMAIL_QUEUE.put(None)

    for t in threads:
        t.join()
    logger.info("所有线程完成任务，程序退出")


if __name__ == '__main__':
    main()  # 启动主函数