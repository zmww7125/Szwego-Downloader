import os
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

# --- 配置 ---
# 要爬取的网站链接
URL = "https://www.szwego.com/static/index.html?link_type=pc_home&shop_id=_dndndGw_1GrMWmb6QufbGq3hxszaalDuViWAm7w&shop_name=4444#/album_home"

# 登录等待时间（秒），请在此时间内完成扫码登录
LOGIN_WAIT_TIME = 30

# --- Helper function for downloading ---
def download_media(url, folder_path, file_name_base):
    time.sleep(1) # 添加1秒下载延迟
    if not url or not isinstance(url, str):
        return
    try:
        response = requests.get(url, stream=True, timeout=15)
        response.raise_for_status()

        content_type = response.headers.get('content-type', '').lower()
        
        extension = ''
        if 'image/jpeg' in content_type:
            extension = '.jpg'
        elif 'image/png' in content_type:
            extension = '.png'
        elif 'image/gif' in content_type:
            extension = '.gif'
        elif 'image/webp' in content_type:
            extension = '.webp'
        elif 'video/mp4' in content_type:
            extension = '.mp4'
        else:
            url_path = url.split("?")[0]
            _, ext_from_url = os.path.splitext(url_path)
            if ext_from_url.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webp']:
                extension = ext_from_url.lower()

        if not extension:
            print(f"无法确定文件类型，跳过下载: {url}")
            return

        file_name = f"{file_name_base}_{int(time.time() * 1000)}{extension}"
        file_path = os.path.join(folder_path, file_name)
        
        print(f"正在下载: {url} -> {file_path}")
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)

    except requests.exceptions.RequestException as e:
        print(f"下载时出错: {url}, 错误: {e}")
    except Exception as e:
        print(f"处理下载时发生未知错误: {e}")

# --- 主程序 ---

# 设置滚动时间为 5 秒
scroll_duration = 5

print(f"好的，将向下滚动 {scroll_duration} 秒来加载项目。")


driver = webdriver.Chrome()
try:
    print("\n正在启动浏览器...")
    driver.get(URL)

    print(f"请在 {LOGIN_WAIT_TIME} 秒内完成登录...")
    time.sleep(LOGIN_WAIT_TIME)

    print(f"登录时间结束，开始向下滚动 {scroll_duration} 秒...")

    # 模拟向下滚动（有时间限制）
    start_time = time.time()
    end_time = start_time + scroll_duration
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while time.time() < end_time:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2) # 等待新内容加载
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("已滚动到底部，提前结束滚动。")
            break
        last_height = new_height

    print("滚动结束，开始提取项目...")
    album_items = driver.find_elements(By.CSS_SELECTOR, "div.home-goods-cells > .weui_padding")

    if not album_items:
        print("错误：未找到任何商品项目。请确认已登录且页面已加载。")
    else:
        total_items = len(album_items)
        print(f"找到了 {total_items} 个商品项目。")
        
        try:
            for i, item in enumerate(album_items):
                print(f"\n--- 正在处理项目 {i+1}/{total_items} ---")
                
                try:
                    # 商品名称和文件夹创建
                    name = "" # Default name is empty
                    # The description text is more reliable as a title, but might not exist
                    name_elements = item.find_elements(By.CSS_SELECTOR, ".word-break.can-select")
                    if name_elements:
                        name = name_elements[0].text
                    
                    # Sanitize the folder name
                    # Remove characters that are invalid in Windows/Linux/macOS filenames
                    # Also remove other special characters and emojis that can cause issues.
                    safe_name = re.sub(r'[\\/:*?"<>|《》．✈️]', '_', name)
                    # Collapse multiple spaces or underscores into a single underscore
                    safe_name = re.sub(r'[\s_]+', '_', safe_name)
                    # Remove leading/trailing underscores and truncate
                    folder_name = safe_name.strip('_')[:50] # Increased length
                    if not folder_name:
                        folder_name = f"未命名_{int(time.time())}_{i}"
                    
                    # Ensure the folder exists before trying to save to it
                    try:
                        if not os.path.exists(folder_name):
                            os.makedirs(folder_name)
                    except OSError as e:
                        print(f"创建文件夹失败: {folder_name}, 错误: {e}")
                        # If folder creation fails, skip this item
                        continue

                    # 下载图片
                    image_elements = item.find_elements(By.CSS_SELECTOR, "img.lazy")
                    for img_idx, image_element in enumerate(image_elements):
                        # The actual URL is in the 'data-original' attribute
                        image_url = image_element.get_attribute('data-original')
                        if image_url:
                            download_media(image_url, folder_name, f"image_{img_idx}")

                    # 尝试下载视频 (如果存在)
                    try:
                        video_element = item.find_element(By.CSS_SELECTOR, "video")
                        video_url = video_element.get_attribute('src')
                        if video_url:
                            download_media(video_url, folder_name, "video_0")
                    except Exception:
                        # It's normal for items to not have videos
                        pass
                except Exception as e:
                    print(f"处理项目 {i+1} 时出错: {e}")

        except KeyboardInterrupt:
            print("\n\n用户手动停止...正在清理并退出。")

finally:
    print("\n所有任务完成！")
    driver.quit()
