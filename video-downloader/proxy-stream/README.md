# Proxy Stream Viewer

YouTube iframe 대신 서버가 yt-dlp로 재생 가능한 미디어 URL을 확인하고, 브라우저에는 HTTP Range 요청으로 필요한 구간만 전달하는 스트리밍/다운로드 뷰어입니다.

## 특징

- HTML5 `<video>` 재생
- **영상 다운로드** 버튼 제공
- 서버가 Range 헤더를 원본 스트림에 전달
- `206 Partial Content`를 그대로 전달해 탐색/재생 지원
- YouTube URL만 허용해 임의 프록시(SSRF)로 쓰이지 않도록 제한
- 추출된 임시 스트림 URL은 메모리에만 저장하고 15분 뒤 만료

## 실행

```bash
python -m pip install -r requirements.txt
python app.py
```

브라우저에서:

```text
http://127.0.0.1:8765/
```

운영 서버:

```bash
gunicorn -b 0.0.0.0:$PORT app:app
```

## YouTube 봇 확인 대응

데이터센터 IP(Render/GitHub Actions 등)는 YouTube의 **Sign in to confirm you're not a bot** 제한에 걸릴 수 있습니다. 이 경우 서버에 다음 중 하나를 설정합니다.

- `YOUTUBE_COOKIE_FILE`: 서버에 존재하는 Netscape 형식 cookies.txt 경로
- `YOUTUBE_COOKIES_B64`: cookies.txt 전체를 base64로 인코딩한 값

`YOUTUBE_COOKIES_B64`는 런타임의 임시 파일로만 복원하며 저장소에는 기록하지 않습니다.

인증 쿠키는 계정 자격 증명에 해당하므로 공개 GitHub에 커밋하지 마세요.
