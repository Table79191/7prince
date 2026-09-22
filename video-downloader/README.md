# Video Downloader

URL을 붙여넣으면 영상을 **MP4**로 다운로드하는 간단한 실행기입니다.

> 본인이 소유하거나 다운로드 권한이 있는 미디어에만 사용하세요.

## Windows에서 가장 간단하게 사용

1. 이 폴더를 내려받습니다.
2. `run_windows.bat`을 더블클릭합니다.
3. 영상 URL을 붙여넣고 Enter를 누릅니다.
4. 기본적으로 Windows의 **Downloads** 폴더에 저장됩니다.

첫 실행에서는 전용 `.venv`를 만들고 필요한 `yt-dlp` 및 내장 ffmpeg 패키지를 자동 설치합니다.

## 명령줄 사용

```bash
python -m pip install -r requirements.txt
python video_downloader.py "https://example.com/video"
```

저장 폴더 지정:

```bash
python video_downloader.py "URL" -o "./downloads"
```

플레이리스트 허용:

```bash
python video_downloader.py "URL" --playlist
```

## YouTube 로그인/연령 확인이 필요한 경우

브라우저에서 본인 계정의 쿠키를 **Netscape cookies.txt 형식**으로 내보내 이 폴더에 `cookies.txt`라는 이름으로 둡니다. 이 파일은 계정 인증 정보이므로 **절대로 GitHub에 커밋하지 마세요.**

또는:

```bash
python video_downloader.py "URL" --cookies "C:\path\to\cookies.txt"
```

Node.js가 설치되어 있으면 최신 YouTube JavaScript 추출 지원을 자동으로 사용합니다.

## 자체 점검

```bash
python video_downloader.py --self-test
```
