# DIVA (darling, i'm very acquisitive)

yes, this repository is this simple on purpose.

backstory: i made this script for a friend a few months back, found it again, polished it, and figured why not release it!!

DIVA is a python-based downloader that specializes in acquiring audios from voice actor's on reddit (gwa, etc.) it scrapes a reddit profile to search for any soundgasm links posted by the profile, and automatically saves the audios for you. it can also be used as a standalone soundgasm downloader if you have a bunch of links you wanna download all at once.

the idea of this script from the beginning was always to be as simple and straightforward as possible!

## requirements

```
beautifulsoup4>=4.9.3
praw>=7.7.0
requests>=2.26.0
mutagen>=1.45.1
```

## installation

1. clone this repository:
```bash
git clone https://github.com/akrscoi/di-va.git
cd DIVA
```

2. install the requirements:
```bash
pip install -r requirements.txt
```

3. create a reddit application at https://www.reddit.com/prefs/apps and obtain your:
   * Client ID
   * Client Secret

*these will be asked for when you first start the script, and will create a config file along with them.*

## usage

Run the script:
```bash
python diva.py
```

from here on, it's quite self explanatory in the script!

## Disclaimer

DIVA is designed for downloading publicly available content only. have fun, but be mindful of content creators' rights and permissions.



## License

MIT License - Because DIVA believes in sharing the spotlight.
