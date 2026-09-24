# Video Downloader + Realtime Viewer

이 폴더에는 두 가지 방식이 있습니다.

## 1. 다운로드 없이 바로 보기 — 권장

`open_viewer.bat` 또는 `index.html`을 엽니다.

1. 영상 URL을 붙여넣습니다.
2. **바로 재생**을 누릅니다.
3. 전체 영상 파일을 먼저 다운로드하지 않고 브라우저에서 스트리밍합니다.

지원 형식:

- YouTube: 공식 embed player 사용
- 직접 MP4 / WebM / OGV / MOV / M4V 링크
- HLS `.m3u8` 스트림
- 모바일 화면 대응

페이지 주소에 `?url=...`을 붙이면 열자마자 해당 영상을 로드합니다.

예:

```text
index.html?url=https%3A%2F%2Fyoutu.be%2FNNyJmOhbVXU
```

### 중요한 차이

이 모드는 `yt-dlp`로 영상을 저장하지 않습니다. YouTube는 YouTube 플레이어가 네트워크로 스트리밍하고, 직접 영상/HLS는 브라우저가 필요한 데이터만 순차적으로 받아 재생합니다.

직접 영상이나 HLS는 원본 서버가 브라우저 재생 및 CORS를 허용해야 합니다. YouTube 영상 중 업로더가 외부 임베드를 막은 영상은 브라우저 임베드에서도 재생할 수 없습니다.

---

## 2. MP4 파일로 저장하기

기존 다운로드 기능도 유지되어 있습니다.

Windows:

1. `run_windows.bat`을 더블클릭합니다.
2. URL을 붙여넣고 Enter를 누릅니다.
3. 기본적으로 **Downloads** 폴더에 MP4가 저장됩니다.

첫 실행에서는 전용 `.venv`를 만들고 `yt-dlp`와 ffmpeg 패키지를 설치합니다.

명령줄:

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

## YouTube 로그인/연령 확인이 필요한 다운로드

브라우저에서 본인 계정의 쿠키를 **Netscape cookies.txt 형식**으로 내보내 이 폴더에 `cookies.txt`라는 이름으로 둘 수 있습니다. 이 파일은 인증 정보이므로 **GitHub에 커밋하면 안 됩니다.**

```bash
python video_downloader.py "URL" --cookies "C:\path\to\cookies.txt"
```

## 테스트

Python 다운로드기:

```bash
python video_downloader.py --self-test
```

HTML 뷰어는 GitHub Actions에서 Chromium/Playwright로 YouTube embed 생성과 직접 MP4 스트림 연결을 실제 브라우저 테스트합니다.
