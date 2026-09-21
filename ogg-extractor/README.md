# OGG Extractor

Small `yt-dlp + ffmpeg` utility for extracting or converting audio to **OGG Vorbis**.

Use it only for media you own or are authorized to process.

## Local file

```bash
sudo apt-get install -y ffmpeg
python -m pip install -r ogg-extractor/requirements.txt
python ogg-extractor/extract_ogg.py input.mp4 -o output.ogg
```

## Authorized URL

```bash
python ogg-extractor/extract_ogg.py "https://example.com/media" -o output.ogg
```

For an authenticated URL, export a Netscape-format `cookies.txt` file and pass it explicitly:

```bash
python ogg-extractor/extract_ogg.py "https://example.com/media" \
  --cookies /path/to/cookies.txt \
  -o output.ogg
```

YouTube URLs automatically enable yt-dlp's Node/EJS support. URL mode disables playlists and validates the final output with `ffprobe`.

## GitHub Actions

The `OGG Extractor` workflow runs a synthetic 1-second smoke test whenever this tool changes.

For authenticated YouTube extraction:

1. Export your logged-in YouTube cookies in Netscape `cookies.txt` format.
2. In the repository, open **Settings → Secrets and variables → Actions → New repository secret**.
3. Name the secret exactly `YOUTUBE_COOKIES`.
4. Paste the entire contents of `cookies.txt` as the secret value.
5. Open **Actions → OGG Extractor → Run workflow** and enter the authorized YouTube URL.

The workflow writes the secret only to a temporary runner file with mode `600`, never commits it, and uploads only the resulting `.ogg` artifact.
