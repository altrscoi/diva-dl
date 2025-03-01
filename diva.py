# standard
import os
import re
import json
import time
import threading
import signal
import sys
from typing import List, Set, Dict, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# third
import requests
import praw
from bs4 import BeautifulSoup
from mutagen.easymp4 import EasyMP4
from rich.console import Console
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    DownloadColumn,
    SpinnerColumn,
)
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.live import Live

terminate_flag = False

# c
SOUNDGASM_PATTERN = r"https?://soundgasm\.net/u/[\w-]+/[\w-]+"
REDDIT_POST_PATTERN = r"https?://(?:www\.)?reddit\.com/r/\w+/comments/[\w-]+/[\w-]*"
DEFAULT_USER_AGENT = "script:soundgasm_downloader:v3.9 (by akrscoi)"
CONFIG_PATH = "config.json"
DEFAULT_OUTPUT_FOLDER = "downloads"
CHUNK_SIZE = 8192
MAX_WORKERS = 4
GB_2_IN_BYTES = 2 * 1024 * 1024 * 1024

# initialize console once
console = Console()

class DownloadStats:
    def __init__(self):
        self.successful = 0
        self.failed = 0
        self.start_time = time.time()
        self.total_bytes = 0
        self.lock = threading.Lock()
        self.current_tasks = {}  # track active downloads

    def add_success(self, bytes_downloaded: int):
        with self.lock:
            self.successful += 1
            self.total_bytes += bytes_downloaded

    def add_failure(self):
        with self.lock:
            self.failed += 1

    def get_average_speed(self) -> float:
        elapsed_time = time.time() - self.start_time
        return self.total_bytes / elapsed_time if elapsed_time > 0 else 0

    def add_task(self, task_id, title):
        with self.lock:
            self.current_tasks[task_id] = title

    def remove_task(self, task_id):
        with self.lock:
            if task_id in self.current_tasks:
                del self.current_tasks[task_id]

class Config:
    def __init__(self):
        self.multithreaded = True
        self.size_warning = True
        self.client_id = ""
        self.client_secret = ""
        self.verbose = False  # yaaaaaa no more mess
        self.load_config()
        
        # check for credentials on the first run
        if not self.client_id or not self.client_secret:
            console.print("\n[yellow]First time setup: Please enter your Reddit API credentials:")
            self.client_id = Prompt.ask("Client ID").strip()
            self.client_secret = Prompt.ask("Client Secret").strip()
            self.save_config()

    def load_config(self):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
                self.multithreaded = config.get("multithreaded", True)
                self.size_warning = config.get("size_warning", True)
                self.client_id = config.get("REDDIT_CLIENT_ID", "")
                self.client_secret = config.get("REDDIT_CLIENT_SECRET", "")
                self.verbose = config.get("verbose", False)  # load verbose setting
        except (FileNotFoundError, json.JSONDecodeError):
            self.save_config()

    def save_config(self):
        config = {
            "multithreaded": self.multithreaded,
            "size_warning": self.size_warning,
            "REDDIT_CLIENT_ID": self.client_id,
            "REDDIT_CLIENT_SECRET": self.client_secret,
            "verbose": self.verbose  # save verbose setting
        }
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)

class SoundgasmDownloader:
    def __init__(self, output_folder: str = DEFAULT_OUTPUT_FOLDER, config: Config = None):
        self.output_folder = output_folder
        os.makedirs(self.output_folder, exist_ok=True)
        self.stats = DownloadStats()
        self.config = config or Config()  # store config for verbosity control
        
    def _extract_audio_metadata(self, soup: BeautifulSoup, url: str = None) -> Tuple[str, str, Optional[str]]:
        try:
            # get title (better error handling)
            title_element = soup.find('h1')
            if title_element:
                title = title_element.text.strip()
            else:
                # extract title from url as fallback
                if url:
                    url_parts = url.split('/')
                    title = url_parts[-1].replace('-', ' ') if url_parts else "unknown"
                else:
                    title = "unknown"
                
            # fix title incase of invalid filename characters
            title = re.sub(r'[<>:"/\\|?*]', '', title)
        
            # get description (better error handling)
            description_element = soup.find('div', class_='jp-description')
            description = description_element.text.strip() if description_element else ''
        
            # get m4a link
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string and 'm4a' in script.string:
                    m4a_match = re.search(r'(https?://media\.soundgasm\.net/sounds/[a-zA-Z0-9]+\.m4a)', script.string)
                    if m4a_match:
                        return title, description, m4a_match.group(1)
        
            return title, description, None
        except Exception as e:
            if self.config.verbose:
                console.print(f"[red]Error extracting metadata: {str(e)}")
            # return safe fallback values
            return "unknown", "", None
    
    def download_audio(self, url: str, progress: Progress, overall_task_id: int, reddit_username: str = None) -> None:
        global terminate_flag
        try:
            # get the page content without creating a status task
            if self.config.verbose:
                console.print(f"[cyan]Fetching {url}")
            
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title, description, m4a_link = self._extract_audio_metadata(soup, url)
            
            if not m4a_link:
                console.print(f"[red]No audio link found for {url}")
                self.stats.add_failure()
                return

            # extract soundgasm username
            soundgasm_username = re.search(r'soundgasm\.net/u/([\w-]+)', url)
            if soundgasm_username:
                username = soundgasm_username.group(1)
            else:
                username = "unknown"
            
            # create user-specific folder
            user_folder = os.path.join(self.output_folder, username)
            os.makedirs(user_folder, exist_ok=True)
            
            file_extension = os.path.splitext(m4a_link)[-1]
            file_path = os.path.join(user_folder, f"{title}{file_extension}")
            
            # check if file already exists
            if os.path.exists(file_path):
                if self.config.verbose:
                    console.print(f"[yellow]Skipping: {title} (already exists)")
                return
            
            response = requests.get(m4a_link, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            download_task = progress.add_task(
                description=f"[magenta]{title}",
                total=total_size,
                filename=title
            )
            
            # track
            self.stats.add_task(download_task, title)
            
            bytes_downloaded = 0
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if terminate_flag:
                        # close file and clean up on abort
                        if self.config.verbose:
                            console.print(f"[yellow]Download aborted: {title}")
                        progress.remove_task(download_task)
                        self.stats.remove_task(download_task)
                        return
                        
                    size = file.write(chunk)
                    bytes_downloaded += size
                    progress.update(download_task, advance=size)
                    progress.update(overall_task_id, advance=size)
            
            # add metadata quietly - no console output unless the users a masochist (verbose)
            audio = EasyMP4(file_path)
            audio['title'] = title
            audio['comment'] = description
            audio['artist'] = username
            audio.save()
            
            if self.config.verbose:
                console.print(f"[green]Completed: {title}")
            
            progress.remove_task(download_task)
            self.stats.remove_task(download_task)
            self.stats.add_success(bytes_downloaded)
            
        except Exception as e:
            console.print(f"[red]Error with {url}: {str(e)}")
            self.stats.add_failure()
            if 'download_task' in locals():
                progress.remove_task(download_task)
                self.stats.remove_task(download_task)

class RedditScraper:
    def __init__(self, config: Config):
        self.config = config
        self.reddit = praw.Reddit(
            client_id=self.config.client_id,
            client_secret=self.config.client_secret,
            user_agent=DEFAULT_USER_AGENT
        )
    
    def get_soundgasm_links(self, username: str) -> List[str]:
        with console.status(f"[cyan]Fetching posts from u/{username}...", spinner="dots"):
            soundgasm_links: Set[str] = set()
            
            try:
                pushshift_url = f"https://api.pushshift.io/reddit/search/submission/?author={username}&limit=1000"
                response = requests.get(pushshift_url)
                if response.status_code == 200:
                    data = response.json().get("data", [])
                    for post in data:
                        text = post.get("selftext", "") + " " + post.get("title", "")
                        matches = re.findall(SOUNDGASM_PATTERN, text)
                        soundgasm_links.update(matches)
            except Exception as e:
                if self.config.verbose:
                    console.print(f"[yellow]Warning: Error fetching Pushshift data: {e}")

            try:
                user = self.reddit.redditor(username)
                for post in user.submissions.new(limit=1000):
                    text = post.selftext + " " + post.title
                    matches = re.findall(SOUNDGASM_PATTERN, text)
                    soundgasm_links.update(matches)
                    
                    if "soundgasm.net" in post.url:
                        soundgasm_links.add(post.url)
            except Exception as e:
                console.print(f"[red]Error fetching Reddit posts: {e}")

        console.print(f"[green]Found {len(soundgasm_links)} soundgasm links for u/{username}.")
        return list(soundgasm_links)

def show_options_menu(config: Config):
    while True:
        console.print("\n=== Options ===")
        console.print(f"1. Multi-threaded downloads: {'[green]Enabled[/]' if config.multithreaded else '[red]Disabled[/]'}")
        console.print(f"2. 2GB size warning: {'[green]Enabled[/]' if config.size_warning else '[red]Disabled[/]'}")
        console.print(f"3. Verbose output: {'[green]Enabled[/]' if config.verbose else '[red]Disabled[/]'}")
        console.print("4. Back to main menu")
        
        choice = IntPrompt.ask("Select option", choices=["1", "2", "3", "4"])
        
        if choice == 1:
            config.multithreaded = not config.multithreaded
        elif choice == 2:
            config.size_warning = not config.size_warning
        elif choice == 3:
            config.verbose = not config.verbose
        elif choice == 4:
            config.save_config()
            break

def calculate_total_size(links: List[str], downloader: SoundgasmDownloader) -> int:
    total_size = 0
    with console.status("[cyan]Calculating total download size...", spinner="dots"):
        for link in links:
            try:
                response = requests.get(link)
                soup = BeautifulSoup(response.text, 'html.parser')
                title, _, m4a_link = downloader._extract_audio_metadata(soup, link)
                
                # extract username and check if file exists
                soundgasm_username = re.search(r'soundgasm\.net/u/([\w-]+)', link)
                username = soundgasm_username.group(1) if soundgasm_username else "unknown"
                
                file_extension = os.path.splitext(m4a_link)[-1] if m4a_link else ".m4a"
                file_path = os.path.join(downloader.output_folder, username, f"{title}{file_extension}")
                
                # yucky duplicates
                if os.path.exists(file_path):
                    continue
                
                if m4a_link:
                    response = requests.get(m4a_link, stream=True)
                    total_size += int(response.headers.get('content-length', 0))
            except Exception as e:
                if downloader.config.verbose:
                    console.print(f"[red]Error calculating size for {link}: {str(e)}")
                continue
    return total_size

def format_speed(bytes_per_second: float) -> str:
    if bytes_per_second >= 1024 * 1024:
        return f"{bytes_per_second / (1024 * 1024):.2f} MB/s"
    elif bytes_per_second >= 1024:
        return f"{bytes_per_second / 1024:.2f} KB/s"
    else:
        return f"{bytes_per_second:.2f} B/s"

def create_progress_bar(console: Console) -> Progress:
    """Create a configured progress bar instance"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        DownloadColumn(),
        TimeRemainingColumn(),
        console=console,
        expand=True,
        transient=not Config().verbose
    )

def download_for_user(username: str, scraper: RedditScraper, config: Config, downloader: SoundgasmDownloader, show_threading_warning: bool = True) -> None:
    global terminate_flag
    links = scraper.get_soundgasm_links(username)
    if not links:
        console.print(f"[yellow]No valid soundgasm links found for u/{username}.")
        return

    total_size = calculate_total_size(links, downloader)
    
    if config.size_warning and total_size > GB_2_IN_BYTES:
        if not Confirm.ask(f"[yellow]Warning: Total download size for u/{username} exceeds 2GB. Continue?"):
            return
    
    # add a warning for multi-threaded downloads only if needed and flag is set
    use_multithreaded = config.multithreaded
    if use_multithreaded and show_threading_warning:
        console.print("[yellow]Warning: Multi-threaded downloads may cause instability with some servers.")
        if not Confirm.ask("Continue with multi-threaded downloads?"):
            console.print("[cyan]Switching to single-threaded mode for stability.")
            use_multithreaded = False

    progress = create_progress_bar(console)
    with progress:
        overall_task = progress.add_task(
            f"[yellow]Overall Progress for u/{username}",
            total=total_size
        )
        
        if use_multithreaded:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []
                for link in links:
                    if terminate_flag:
                        break
                    futures.append(executor.submit(downloader.download_audio, link, progress, overall_task, username))
                
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        if config.verbose:
                            console.print(f"[red]Error in thread: {str(e)}")
                    
                    # check termination flag after each completed download
                    if terminate_flag:
                        console.print("[yellow]Aborting remaining downloads...")
                        for f in futures:
                            if not f.done():
                                f.cancel()
                        break
        else:
            for link in links:
                if terminate_flag:
                    console.print("[yellow]Aborting remaining downloads...")
                    break
                downloader.download_audio(link, progress, overall_task, username)

def extract_links_from_text(text: str) -> List[str]:
    """Extract soundgasm links from text input."""
    return re.findall(SOUNDGASM_PATTERN, text)

def extract_links_from_reddit_post(url: str, reddit: praw.Reddit) -> List[str]:
    """Extract soundgasm links from a Reddit post URL."""
    try:
        submission = reddit.submission(url=url)
        text = f"{submission.title} {submission.selftext}"
        for comment in submission.comments.list():
            if isinstance(comment, praw.models.Comment):
                text += f" {comment.body}"
        return extract_links_from_text(text)
    except Exception as e:
        console.print(f"[red]Error processing Reddit post {url}: {str(e)}")
        return []

def process_input_links(text: str, reddit: praw.Reddit) -> List[str]:
    """Process input text to extract both direct soundgasm links and links from Reddit posts."""
    links = set()
    
    # split input by lines or spaces
    items = re.split(r'[\n\s]+', text.strip())
    
    for item in items:
        if not item:
            continue
            
        # check if its a reddit post thingy
        if re.match(REDDIT_POST_PATTERN, item):
            reddit_links = extract_links_from_reddit_post(item, reddit)
            links.update(reddit_links)
        # check if its a direct soundgasm link thingy
        elif re.match(SOUNDGASM_PATTERN, item):
            links.add(item)
            
    return list(links)

def extract_username_from_soundgasm_url(url: str) -> str:
    """Extract username from a soundgasm URL."""
    match = re.search(r'soundgasm\.net/u/([\w-]+)', url)
    return match.group(1) if match else "unknown"

def read_links_from_file(file_path: str) -> str:
    """Read links from a text file."""
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        console.print(f"[red]Error reading file {file_path}: {str(e)}")
        return ""

def handle_manual_input(config: Config, downloader: SoundgasmDownloader):
    """Handle manual input of links or Reddit posts."""
    console.print("\n[cyan]Choose input method:")
    console.print("1. Enter links manually")
    console.print("2. Import from text file (one link per line)")
    
    input_choice = IntPrompt.ask("Select option", choices=["1", "2"])
    
    text = ""
    if input_choice == 1:
        console.print("\n[cyan]Enter Soundgasm links or Reddit post URLs (one per line, press Enter twice to finish):")
        lines = []
        
        while True:
            line = input()
            if not line:
                if lines:
                    break
                else:
                    continue
            lines.append(line)
        
        if not lines:
            console.print("[yellow]No input provided.")
            return
            
        text = "\n".join(lines)
    else:  # input_choice == 2
        file_path = Prompt.ask("\n[cyan]Enter the path to your text file (with one link per line)")
        text = read_links_from_file(file_path)
        if not text:
            console.print("[yellow]No valid content found in the file.")
            return
    
    scraper = RedditScraper(config)
    links = process_input_links(text, scraper.reddit)
    
    if not links:
        console.print("[yellow]No valid soundgasm links found.")
        return
        
    console.print(f"[green]Found {len(links)} soundgasm links.")
    
    # group links by username
    links_by_username = {}
    for link in links:
        username = extract_username_from_soundgasm_url(link)
        if username not in links_by_username:
            links_by_username[username] = []
        links_by_username[username].append(link)
    
    # calculate total size and ball
    total_size = calculate_total_size(links, downloader)
    
    if config.size_warning and total_size > GB_2_IN_BYTES:
        if not Confirm.ask("[yellow]Warning: Total download size exceeds 2GB. Continue?"):
            return
    
    # nuh
    use_multithreaded = config.multithreaded
    
    progress = create_progress_bar(console)
    with progress:
        overall_task = progress.add_task(
            "[yellow]Overall Progress",
            total=total_size
        )
        
        for username, user_links in links_by_username.items():
            console.print(f"\n[cyan]Downloading files for user: {username}")
            
            if use_multithreaded:
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = [
                        executor.submit(downloader.download_audio, link, progress, overall_task, username)
                        for link in user_links
                    ]
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            if config.verbose:
                                console.print(f"[red]Error in thread: {str(e)}")
            else:
                for link in user_links:
                    downloader.download_audio(link, progress, overall_task, username)

def signal_handler(sig, frame):
    global terminate_flag
    console.print("\n[yellow]Abort requested - Finishing current downloads and stopping...")
    terminate_flag = True

def show_active_downloads(downloader: SoundgasmDownloader):
    """Display active downloads in a continuously updating view"""
    with Live(auto_refresh=True) as live:
        while True:
            tasks = list(downloader.stats.current_tasks.values())
            if not tasks:
                live.update("No active downloads")
            else:
                task_list = "\n".join([f"• {task}" for task in tasks])
                live.update(f"Active downloads ({len(tasks)}):\n{task_list}")
            time.sleep(0.5)

def main():
    global terminate_flag
    signal.signal(signal.SIGINT, signal_handler)
    config = Config()
    
    while True:
        # reset termination flag at the start of each operation
        terminate_flag = False
        
        # create titleeeee
        title = Text("=== DIVA ===", style="bold magenta")
        console.print(Panel(title, expand=False))
        
        # menuuuuuuu
        console.print("\nPlease select your option:")
        console.print("1. Download from Reddit VA profile(s)")
        console.print("2. Download from links or Reddit threads")
        console.print("3. Options")
        console.print("4. Exit")
        
        mode = IntPrompt.ask("\nEnter mode", choices=["1", "2", "3", "4"])
        
        if mode == 4:
            console.print("[green]Goodbye!")
            break
        
        if mode == 3:
            show_options_menu(config)
            continue
        
        downloader = SoundgasmDownloader(config=config)
        
        if mode == 1:
            usernames = []
            while True:
                username = Prompt.ask("\nEnter the Reddit username of the voice actor (or press Enter to finish)").strip()
                if not username:
                    break
                usernames.append(username)
            
            if not usernames:
                console.print("[yellow]No usernames entered.")
                continue
                
            scraper = RedditScraper(config)
            
            # show threading warning only once if multiple usernames
            show_warning = len(usernames) > 1
            
            # process each username
            for i, username in enumerate(usernames):
                # only show the warning for the first username if multiple usernames are used
                download_for_user(username, scraper, config, downloader, show_warning and i == 0)
        
        elif mode == 2:
            handle_manual_input(config, downloader)
            
        # statistics
        if mode in (1, 2):
            console.print("\n[green]All downloads completed!")
            console.print(f"Successfully downloaded: [green]{downloader.stats.successful}[/] files")
            console.print(f"Failed downloads: [red]{downloader.stats.failed}[/] files")
            console.print(f"Average download speed: [cyan]{format_speed(downloader.stats.get_average_speed())}[/]")

if __name__ == "__main__":
    main()