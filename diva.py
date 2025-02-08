import requests
import praw
import re
import os
import json
from bs4 import BeautifulSoup
from mutagen.easymp4 import EasyMP4
from typing import List, Set, Tuple, Optional

class SoundgasmDownloader:
    """schmart"""
    
    def __init__(self):
        self.output_folder = "downloads"
        self.soundgasm_pattern = r"https?://soundgasm.net/u/[\w-]+/[\w-]+"
        os.makedirs(self.output_folder, exist_ok=True)
        
    def _extract_audio_metadata(self, soup: BeautifulSoup) -> Tuple[str, str, Optional[str]]:
        """extract title, description and m4a link from the soundgasm page"""
        title_tag = soup.find('div', class_='jp-title')
        title = title_tag.text.strip() if title_tag else "untitled_audio"
        title = re.sub(r'[\/:*?"<>|]', '-', title)
        
        description_tag = soup.find('div', class_='jp-description')
        description = description_tag.get_text(strip=True, separator=" ") if description_tag else "No description available"
        
        m4a_link = None
        for script in soup.find_all('script'):
            if script.string and "m4a" in script.string:
                match = re.search(r'm4a:\s*"([^"]+)"', script.string)
                if match:
                    m4a_link = match.group(1)
                    break
                    
        return title, description, m4a_link

    def download_audio(self, url: str) -> None:
        """download and save audio from a soundgasm url."""
        try:
            print(f"processing: {url}")
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title, description, m4a_link = self._extract_audio_metadata(soup)
            
            if not m4a_link:
                print(f"no audio link found for {url}. skipping.")
                return
                
            file_extension = os.path.splitext(m4a_link)[-1]
            file_name = os.path.join(self.output_folder, f"{title}{file_extension}")
            
            print(f"downloading: {title}")
            audio_response = requests.get(m4a_link)
            audio_response.raise_for_status()
            
            with open(file_name, 'wb') as file:
                file.write(audio_response.content)
            
            print(f"embedding metadata for: {title}")
            audio = EasyMP4(file_name)
            audio['title'] = title
            audio['comment'] = description
            audio.save()
            
            print(f"done: {title}")
            
        except Exception as e:
            print(f"error with {url}: {e}")

class RedditScraper:
    """reddit schmart"""
    
    def __init__(self):
        self.client_id, self.client_secret = self._load_credentials()
        self.reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent="script:soundgasm_downloader:v3.3 (by b)"
        )
    
    def _load_credentials(self) -> Tuple[str, str]:
        """load or create reddit API credentials"""
        config_path = "config.json"
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                return config["REDDIT_CLIENT_ID"], config["REDDIT_CLIENT_SECRET"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            print("no credentials detected in config. you're probably new to this script, please enter your reddit API credentials:")
            client_id = input("Client ID: ").strip()
            client_secret = input("Client Secret: ").strip()
            
            config = {
                "REDDIT_CLIENT_ID": client_id,
                "REDDIT_CLIENT_SECRET": client_secret
            }
            
            with open(config_path, "w") as f:
                json.dump(config, f, indent=4)
            return client_id, client_secret

    def get_soundgasm_links(self, username: str) -> List[str]:
        """scrape soundgasm links from a reddit user's posts"""
        print(f"fetching all posts from u/{username}...")
        soundgasm_links: Set[str] = set()
        
        # break in case of praw failure hehe
        pushshift_url = f"https://api.pushshift.io/reddit/search/submission/?author={username}&limit=1000"
        try:
            response = requests.get(pushshift_url)
            if response.status_code == 200:
                data = response.json().get("data", [])
                for post in data:
                    text = post.get("selftext", "") + " " + post.get("title", "")
                    matches = re.findall(r"https?://soundgasm.net/u/[\w-]+/[\w-]+", text)
                    soundgasm_links.update(matches)
        except Exception as e:
            print(f"error fetching pushshift data: {e}")

        try:
            user = self.reddit.redditor(username)
            for post in user.submissions.new(limit=1000):
                text = post.selftext + " " + post.title
                matches = re.findall(r"https?://soundgasm.net/u/[\w-]+/[\w-]+", text)
                soundgasm_links.update(matches)
                
                if "soundgasm.net" in post.url:
                    soundgasm_links.add(post.url)
        except Exception as e:
            print(f"error fetching reddit posts: {e}")

        print(f"found {len(soundgasm_links)} soundgasm links.")
        return list(soundgasm_links)

def get_links_from_input() -> List[str]:
    """get soundgasm links from user input or file."""
    print("enter your links (one per line, enter an empty line to finish)")
    print("you can also enter a file path to load links from a text file:")
    
    first_line = input().strip()
    if os.path.isfile(first_line):
        try:
            with open(first_line, 'r') as f:
                content = f.read()
            links = re.findall(r"https?://soundgasm.net/u/[\w-]+/[\w-]+", content)
            print(f"loaded {len(links)} links from file")
            return list(set(links))
        except Exception as e:
            print(f"error reading file: {e}")
            return []
    
    links = [first_line] if first_line else []
    while True:
        line = input().strip()
        if not line:
            break
        if re.match(r"https?://soundgasm.net/u/[\w-]+/[\w-]+", line):
            links.append(line)
        else:
            print(f"skipping invalid link: {line}")
    
    return links

def main():
    print("\n=== DIVA ===\n")
    print("hi hi! please select your download mode:")
    print("1. download from a reddit va's profile")
    print("2. download your own individual links")
    
    mode = input("\nenter mode (1 or 2): ").strip()
    
    downloader = SoundgasmDownloader()
    links: List[str] = []
    
    if mode == "1":
        reddit_username = input("\nenter the reddit username of the voice actor: ").strip()
        scraper = RedditScraper()
        links = scraper.get_soundgasm_links(reddit_username)
    elif mode == "2":
        links = get_links_from_input()
    else:
        print("invalid mode selected. exiting...")
        return

    if links:
        print(f"\nprocessing {len(links)} links...")
        for link in links:
            downloader.download_audio(link)
        print("\nall downloads completed!")
    else:
        print("\nno valid soundgasm links found.")

if __name__ == "__main__":
    main()