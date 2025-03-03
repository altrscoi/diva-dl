![diva-dl](https://pixeldrain.com/api/file/g5XwNJ2p)
#

diva-dl is a one-script python based downloader that specializes in acquiring audios from voice actor's on reddit (gwa, etc.). it scrapes a reddit profile to search for any soundgasm links posted by the account and automates the downloading process. it can also be used as a standalone soundgasm downloader.

![example](https://pixeldrain.com/api/file/y6nM6AV3)

## features
- multi-user & multi-threading support – download from multiple reddit va profiles at once
-  reddit thread parsing – automatically extracts soundgasm links from entire reddit threads, no manual searching needed
- organized downloads – files are neatly sorted by voice actor username, making it have a much nicer look
- live progress tracking – see successful vs failed downloads, real-time speed tracking, and automatic file size warnings for 2gb+ collections
- import from text files – if you have a list of reddit/soundgasm links in a text file, diva has the ability to download them
- safe termination handling – diva gracefully finishes current downloads instead of corrupting files
- customizable settings – toggle multi-threading, verbosity, file size warnings, and more to fine-tune your experience
- beautiful ui with rich – styled with spinners, progress bars, live updates, and a modern CLI experience

## requirements

```
requests>=2.28.0
praw>=7.6.0
beautifulsoup4>=4.11.1
mutagen>=1.45.1
rich>=12.5.1
```

## installation

1. clone this repository:
```bash
git clone https://github.com/altrscoi/diva-dl.git
cd diva-dl
```

2. install the requirements:
```bash
pip install -r requirements.txt
```

3. create a reddit application at https://www.reddit.com/prefs/apps, select script, name it whatever, and give it the redirect url http://localhost:8080 . from there grab your:
   * Client ID — underneath where it says "personal use script"
   * Client Secret — next to "secret"

*these will be asked for when you first start the script and are essential for diva to run correctly. if you get nothing but errors when trying to download audios, you messed this part up. please open your `config.json` file and enter the correct credentials.*

## usage

Run the script:
```bash
python diva.py
```

from there on, diva is ready for hoarding and will guide you!!

## Disclaimer

i designed diva-dl for a friend and released it out of request. i spent a very long time squashing bugs before this release. before you open an issue in the issue tracker, please make sure it's nothing on your part. i don't plan on updating this project much more unless i reeeeallly feel like it, or if anything changes in regards to how the script works (some of you have suggested expanding beyond reddit which... i dunno, let me think about it)

please respect any voice actors' wishes that have rules in place against archiving their audios. diva-dl is meant to download publicly avaliable audios and not infringe on anyones privacy :) nonetheless, i am not responsible for what you do with this script.
