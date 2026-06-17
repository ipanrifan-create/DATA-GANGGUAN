import time
import requests
import json
import os
import sys
import traceback

from github import Github
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


def upload_to_github(data, filename="data_gangguan.json"):
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("[ERROR] GITHUB_TOKEN tidak ditemukan di environment variables!")
        return False

    try:
        g = Github(token)
        repo = g.get_repo("ipanrifan-create/DATA-KR") # Ganti jika nama repo berbeda
        
        file_content = json.dumps(data, indent=4, ensure_ascii=False)

        try:
            contents = repo.get_contents(filename)
            repo.update_file(
                path=contents.path,
                message="Update data gangguan otomatis",
                content=file_content,
                sha=contents.sha
            )
            print(f"[OK] File {filename} berhasil diperbarui di GitHub.")
        except Exception:
            repo.create_file(
                path=filename,
                message="Commit data gangguan pertama",
                content=file_content
            )
            print(f"[OK] File {filename} berhasil dibuat di GitHub.")
        return True

    except Exception as e:
        print(f"[ERROR] Gagal upload ke GitHub: {e}")
        traceback.print_exc()
        return False


def create_chrome_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--remote-allow-origins=*')
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )

    from selenium.webdriver.chrome.service import Service
    import shutil

    chromedriver_path = shutil.which('chromedriver')
    if chromedriver_path:
        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)

    driver.set_page_load_timeout(60)
    return driver


def jalankan_bot():
    print("=" * 50)
    print("=== [START] Operasi Bot Ambil Data API ===")
    print("=" * 50)

    email = os.environ.get('EMAIL_WEB')
    password = os.environ.get('PASS_WEB')

    driver = create_chrome_driver()

    try:
        # ===== STEP 1: Login ke Web =====
        if email and password:
            print("[STEP 1] Membuka halaman login...")
            driver.get("https://amc-kal-2-gudang.pages.dev/login") 
            wait = WebDriverWait(driver, 30)

            print("[STEP 1] Mengisi email...")
            email_input = wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='text' or @placeholder='Email']"))
            )
            email_input.clear()
            email_input.send_keys(email)

            print("[STEP 1] Mengisi password...")
            password_input = driver.find_element(By.XPATH, "//input[@type='password']")
            password_input.clear()
            password_input.send_keys(password)

            print("[STEP 1] Klik tombol Login...")
            login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Log in')]")
            login_button.click()

            print("[STEP 1] Menunggu redirect setelah login...")
            time.sleep(5)
            print("[STEP 1] Login berhasil!")
        else:
            print("[STEP 1] Tidak ada kredensial, langsung mengakses web...")

        # ===== STEP 2: Ambil Cookies =====
        print("[STEP 2] Mengambil session cookies...")
        driver.get("https://amc-kal-2-gudang.pages.dev/dashboard/gangguan")
        time.sleep(3)
        session_cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        print(f"[STEP 2] Berhasil mengambil {len(session_cookies)} cookies.")

        # ===== STEP 3: Request API JSON =====
        headers = {
            'accept': '*/*',
            'referer': 'https://amc-kal-2-gudang.pages.dev/dashboard/gangguan',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        api_url = "https://amc-kal-2-gudang.pages.dev/api/gangguan-transactions"
        print(f"[STEP 3] Mengambil data JSON dari: {api_url}")

        response_api = requests.get(
            api_url,
            cookies=session_cookies,
            headers=headers,
            timeout=60
        )

        # ===== STEP 4: Upload ke GitHub =====
        if response_api.status_code == 200:
            print("[STEP 3] Berhasil mengambil data!")
            print("[STEP 4] Mengupload langsung ke GitHub...")
            
            data_json = response_api.json()
            success = upload_to_github(data_json, filename="data_gangguan.json")

            if success:
                print("[STEP 4] Data JSON berhasil diupload ke GitHub!")
            else:
                print("[STEP 4] Gagal mengupload ke GitHub!")
        else:
            status = response_api.status_code
            print(f"[ERROR] Gagal request API! Status: {status}")
            print(f"[DEBUG] Response Text: {response_api.text[:500]}")
            return False

        print("=" * 50)
        print("=== [FINISH] Operasi Selesai ===")
        print("=" * 50)
        return True

    except Exception as e:
        print(f"[FATAL ERROR] Terjadi error: {e}")
        traceback.print_exc()
        try:
            screenshot_path = "/tmp/web_error_screenshot.png"
            driver.save_screenshot(screenshot_path)
            print(f"[DEBUG] Screenshot disimpan ke: {screenshot_path}")
            print(f"[DEBUG] URL saat error: {driver.current_url}")
        except Exception:
            pass
        return False

    finally:
        driver.quit()
        print("[INFO] Browser ditutup.")


if __name__ == "__main__":
    result = jalankan_bot()
    sys.exit(0 if result else 1)
