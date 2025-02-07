# DIVA (darling, i'm very acquisitive)

DIVA is a python-based downloader that specializes in acquiring specific voice actors' content from reddit. it scrapes a Reddit profile to search for any soundgasm links posted by said user, and automatically saves the audios for you.

it can also be used as a standalone soundgasm downloader if needed.


## cool features

* preserves original metadata and descriptions
* handles both single links and bulk downloads
* supports file-based input for those *extensive* collections
* automatic metadata embedding (cause yeah)

## Requirements

```
beautifulsoup4>=4.9.3
praw>=7.7.0
requests>=2.26.0
mutagen>=1.45.1
```

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/DIVA.git
cd DIVA
```

2. Install the requirements:
```bash
pip install -r requirements.txt
```

3. Create a Reddit application at https://www.reddit.com/prefs/apps and obtain your:
   * Client ID
   * Client Secret

*Don't worry, darling, DIVA will ask for these on first run~*

## Usage

Run the script:
```bash
python diva.py
```

Choose your mode:
1. Download from a Reddit user's profile
2. Input your own list of links

That's it! DIVA will handle the rest with *impeccable* grace.

## Features in Detail

### Mode 1: Reddit Profile Download
* Simply provide a Reddit username
* DIVA will fetch ALL Soundgasm links from their:
  * Subreddit posts
  * Profile posts
  * Direct link submissions

### Mode 2: Manual Link Input
* Enter links one per line
* Submit a text file containing links
* Press Enter twice when done (DIVA needs her cue~)

## Output

All files are saved to a `downloads` folder with:
* Original title
* Original description
* Embedded metadata
* High-quality audio preserved

## Disclaimer

DIVA is designed for downloading publicly available content only. Be fabulous, but be respectful of content creators' rights and permissions.

## Contributing

Found a bug? Have a feature request? DIVA accepts pull requests with the same grace she accepts compliments~

## License

MIT License - Because DIVA believes in sharing the spotlight.

---
*"Downloads? I Volunteer, Actually~"*