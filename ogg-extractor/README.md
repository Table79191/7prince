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

URL mode uses `yt-dlp` with playlists disabled. The script validates the final file with `ffprobe` and requires the audio codec to be Vorbis.

## GitHub Actions

The `OGG Extractor` workflow runs a synthetic 1-second audio smoke test on changes to this tool.

It can also be started manually from **Actions → OGG Extractor → Run workflow**. Leave the source field blank for the smoke test, or provide an authorized media URL. The resulting OGG is uploaded as a workflow artifact.
