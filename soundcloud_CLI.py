# check this website to download youtube-dl http://ytdl-org.github.io/youtube-dl/download.html
import subprocess
import os
import json
import urllib.request

def download_audio(url):
    print(f"Downloading audio from: {url}")

    try:
        filename = subprocess.check_output(['youtube-dl', '--get-filename', url], encoding='utf-8', stderr=subprocess.DEVNULL).strip()
        print(f"Detected filename: {filename}")

        subprocess.call(['youtube-dl', '--write-info-json', '--skip-download', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        json_files = [pos_json for pos_json in os.listdir('.') if pos_json.endswith('.info.json')]
        if json_files:
            with open(json_files[0], 'r') as fp:
                data = json.load(fp)

            file_url = data['url']
            title = data['fulltitle']
            file_name = f"{title.replace('/', '_')}.mp3"  # Replace slash with underscore
            print(f"Downloading audio file: {file_name}")

            urllib.request.urlretrieve(file_url, file_name, reporthook=progress_update)
            print(f"Audio download complete: {file_name}")

            os.remove(json_files[0])
            print("Info JSON file removed.")
        else:
            print("Error: Failed to locate info JSON file.")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to download audio. {e}")
    except (IndexError, FileNotFoundError):
        print("Error: Failed to locate info JSON file.")
    except urllib.error.URLError as e:
        print(f"Error: Failed to download audio. {e}")

def progress_update(block_num, block_size, total_size):
    downloaded = block_num * block_size
    percent = min(round(downloaded / total_size * 100, 2), 100)
    print(f"Downloading... {percent:.2f}% completed", end='\r')

url = input("Enter the SoundCloud URL: ")

download_audio(url)
