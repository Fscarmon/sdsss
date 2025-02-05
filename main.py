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
import traceback
import cv2  # 导入 OpenCV

# 全局配置
MAX_RETRIES = 5  # 最大重试次数
EMAIL_DOMAIN_ENV_VAR = "EMAIL_DOMAIN"  # 邮箱域名环境变量名
CAPTCHA_IMAGE_PATH = "static/image.jpg"  # 验证码图片保存路径
BASE_URL = "https://www.serv00.com"
CREATE_ACCOUNT_URL = f"{BASE_URL}/offer/create_new_account.json"

# 初始化
ocr = ddddocr.DdddOcr()
fake = Faker()

# 确保 static 目录存在
os.makedirs("static", exist_ok=True)


# 辅助函数
def get_user_name():
    """生成包含 name 和 surname 字段的随机姓名列表."""
    names = []
    for _ in range(5):
        try:
            name = fake.name()
            first_name = name.split(" ")[0]
            last_name = name.split(" ")[-1]
            names.append({"name": first_name, "surname": last_name})
        except Exception as e:
            logger.error(f"生成随机姓名失败: {e}\n{traceback.format_exc()}")
            # 备用方案
            first_name = random.choice(["Alice", "Bob"])
            last_name = random.choice(["Smith", "Jones"])
            names.append({"name": first_name, "surname": last_name})
    return names


def generate_random_username(length=8):
    """生成随机用户名."""
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def generate_random_email_prefix(length=20):
    """生成随机邮箱前缀."""
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def get_email_domains():
    """从环境变量获取邮箱域名列表."""
    email_domains_str = os.environ.get(EMAIL_DOMAIN_ENV_VAR)
    if not email_domains_str:
        logger.error(f"{EMAIL_DOMAIN_ENV_VAR} 环境变量未设置")
        return None
    email_domains = [domain.strip() for domain in email_domains_str.split(';')]
    logger.info(f"使用邮箱后缀: {email_domains}")
    return email_domains


def download_captcha_image(session, captcha_url, headers):
    """下载验证码图片."""
    try:
        logger.info(f"请求验证码图片URL: {captcha_url}")
        resp_captcha = session.get(captcha_url, headers=headers, impersonate="chrome124", allow_redirects=False)

        logger.info(f"获取验证码图片状态码: {resp_captcha.status_code}")
        if resp_captcha.status_code != 200:
            logger.error(f"获取验证码图片失败，状态码: {resp_captcha.status_code}, 响应内容: {resp_captcha.text}")
            return None  # 下载失败，返回 None

        content_captcha = resp_captcha.content
        with open(CAPTCHA_IMAGE_PATH, "wb") as f:
            f.write(content_captcha)
        return CAPTCHA_IMAGE_PATH  # 返回图片路径
    except Exception as e:
        logger.error(f"下载验证码图片失败: {e}\n{traceback.format_exc()}")
        return None


def recognize_captcha(image_path):
    """识别验证码图片，并进行降噪处理."""
    try:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 尝试不同的降噪方法 (取消注释以尝试不同的方法)

        # 方法1: 形态学操作 (推荐先尝试这个)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)[1]
        denoised = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

        # 方法2: 中值滤波 (适用于去除椒盐噪声)
        # denoised = cv2.medianBlur(gray, 3)

        # 方法3: 高斯滤波 (适用于平滑图像，减少噪点)
        # denoised = cv2.GaussianBlur(gray, (5, 5), 0)

        # 方法4: 非局部均值滤波 (计算量大，效果好，但速度慢，谨慎使用)
        # denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

        # 使用降噪后的图像进行 OCR
        captcha_text = ocr.classification(denoised).lower()  # OCR需要接收图像数据，而不是文件路径
        logger.info(f"OCR识别结果: {captcha_text}")

        if not bool(re.match(r'^[a-zA-Z0-9]{4}$', captcha_text)):
            logger.warning(f"识别的验证码无效: {captcha_text}")
            return None
        return captcha_text
    except Exception as e:
        logger.error(f"识别验证码失败: {e}\n{traceback.format_exc()}")
        return None


# 主要注册逻辑
def register_email(email):
    """注册邮箱的主要函数."""
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

    try:
        with requests.Session() as session:

            # 1. 获取 Cookie
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
            logger.info(f"请求URL: {BASE_URL}")
            resp_base = session.get(BASE_URL, headers=header_base, impersonate="chrome124")
            logger.info(f"获取基础页面状态码: {resp_base.status_code}")

            if resp_base.status_code != 200:
                logger.error(f"获取基础页面失败，状态码: {resp_base.status_code}, 响应内容: {resp_base.text}")
                raise Exception(f"获取基础页面失败，状态码: {resp_base.status_code}")

            cookie = resp_base.headers.get("set-cookie")
            logger.info(f"获取Cookie: {cookie}")

            # 2. 获取用户信息
            try:
                usernames = get_user_name()
                _ = usernames.pop()
                first_name = _["name"]
                last_name = _["surname"]
                username = generate_random_username()
                logger.info(f"注册信息 - Email: {email}, First Name: {first_name}, Last Name: {last_name}, Username: {username}")
            except Exception as e:
                logger.error(f"获取用户信息失败: {e}\n{traceback.format_exc()}")
                return  # 停止注册

            # 3. 获取 captcha_0
            header_create_account = {
                "Host": "www.serv00.com",
                "User-Agent": ua,
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": BASE_URL,
                "Connection": "keep-alive",
                "Referer": f"{BASE_URL}/offer/create_new_account",
                "Cookie": cookie,
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
            }

            logger.info(f"请求URL: {CREATE_ACCOUNT_URL}")
            resp_create_account = session.get(CREATE_ACCOUNT_URL, headers=header_create_account,
                                              impersonate="chrome124", allow_redirects=False)

            logger.info(f"获取 captcha_0 状态码: {resp_create_account.status_code}")
            if resp_create_account.status_code == 200 and resp_create_account.content:
                try:
                    content_create_account = resp_create_account.json()  # 直接解析JSON
                    captcha_0 = content_create_account["__captcha_key"]
                    logger.info(f"提取 captcha_0 成功: {captcha_0}")
                except (KeyError, ValueError) as e:  # 修正异常类型
                    logger.error(f"提取 captcha_0 失败，content: {resp_create_account.text}, 错误信息：{e}\n{traceback.format_exc()}")
                    return  # 停止注册
            else:
                logger.error(f"获取 captcha_0 失败，状态码: {resp_create_account.status_code}, 响应内容: {resp_create_account.text}")
                return  # 停止注册

            # 4. 验证码处理和提交
            captcha_url = f"{BASE_URL}/captcha/image/{captcha_0}/"
            header_captcha = {
                "Host": "www.serv00.com",
                "User-Agent": ua,
                "Accept": "image/avif,image/webp,*/*",
                "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
                "Sec-GPC": "1",
                "Connection": "keep-alive",
                "Referer": f"{BASE_URL}/offer/create_new_account",
                "Cookie": cookie,
                "Sec-Fetch-Dest": "image",
                "Sec-Fetch-Mode": "no-cors",
                "Sec-Fetch-Site": "same-origin",
                "Priority": "u=4",
                "TE": "trailers",
            }

            for retry in range(MAX_RETRIES):
                time.sleep(random.uniform(0.5, 1.2))
                logger.info(f"第 {retry + 1} 次尝试注册邮箱 {email}")

                try:
                    # 下载验证码图片
                    image_path = download_captcha_image(session, captcha_url, header_captcha)
                    if not image_path:
                        logger.warning(f"下载验证码失败，重试")
                        continue  # 下载失败，重试

                    # 识别验证码 (包含降噪)
                    captcha_1 = recognize_captcha(image_path)
                    if not captcha_1:
                        logger.warning(f"识别验证码失败，重试")
                        continue  # 识别失败，重试

                    # 5. 提交注册信息
                    header_submit = header_create_account.copy()  # 使用相同的header, 减少出错
                    data = f"first_name={first_name}&last_name={last_name}&username={username}&email={quote(email)}&captcha_0={captcha_0}&captcha_1={captcha_1}&question=0&tos=on"
                    logger.info(f"POST 数据: {data}")

                    logger.info(f"请求URL: {CREATE_ACCOUNT_URL}")
                    resp_submit = session.post(CREATE_ACCOUNT_URL, headers=header_submit, data=data,
                                                impersonate="chrome124", allow_redirects=False)

                    logger.info(f"提交注册信息状态码: {resp_submit.status_code}")
                    if resp_submit.status_code != 200:
                        logger.error(f"提交注册信息失败，状态码: {resp_submit.status_code}, 响应内容: {resp_submit.text}")
                        continue  # 提交失败，重试

                    try:
                        content_submit = resp_submit.json()
                        logger.info(f"提交注册信息响应: {content_submit}")

                        if content_submit.get("captcha") and content_submit["captcha"][0] == "Invalid CAPTCHA":
                            logger.warning("验证码错误，正在重新获取")
                            continue  # 验证码错误，重试
                        elif content_submit.get("username") and content_submit["username"][0] == "This username is already taken.":
                            logger.warning("用户名已被占用，重新生成")
                            username = generate_random_username()
                            continue
                        elif content_submit.get("email") and content_submit["email"][0] == "This email address is already registered.":
                            logger.warning("邮箱已被注册，放弃注册")
                            return
                        else:
                            logger.info(f"邮箱 {email} 注册成功!")
                            return  # 注册成功，退出重试循环

                    except Exception as e:
                        logger.error(f"解析 JSON 失败: {e}, 响应内容: {resp_submit.text}\n{traceback.format_exc()}")
                        continue  # JSON 解析失败，重试

                finally:
                    # 确保删除验证码图片，无论成功与否
                    try:
                        os.remove(CAPTCHA_IMAGE_PATH)
                    except FileNotFoundError:
                        pass  # 图片可能未成功生成

            logger.warning(f"邮箱 {email} 注册失败，达到最大重试次数，尝试下一个邮箱")

    except Exception as e:
        logger.error(f"注册邮箱 {email} 发生异常: {e}\n{traceback.format_exc()}")


# 后台任务
def background_task():
    """后台任务，循环注册邮箱."""
    email_domains = get_email_domains()
    if not email_domains:
        return

    while True:  # 无限循环注册
        for email_domain in email_domains:
            email_prefix = generate_random_email_prefix()
            email = f"{email_prefix}@{email_domain}"
            logger.info(f"开始注册邮箱: {email}")
            try:
                register_email(email)
            except Exception as e:
                logger.error(f"注册邮箱 {email} 失败: {e}\n{traceback.format_exc()}")
                time.sleep(60)  # 发生异常后，等待一段时间再重试


# 主程序
if __name__ == '__main__':
    # 启动后台任务
    task_thread = threading.Thread(target=background_task)
    task_thread.daemon = True  # 设置为守护线程
    task_thread.start()

    # 保持主线程运行
    while True:
        time.sleep(1)  # 防止 CPU 占用过高