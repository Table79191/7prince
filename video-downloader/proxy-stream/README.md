# Proxy Stream Viewer

YouTube iframe 대신 서버가 yt-dlp로 재생 가능한 미디어 URL을 확인하고, 브라우저에는 HTTP Range 요청으로 필요한 구간만 전달하는 스트리밍 뷰어입니다.

## 특징

- 전체 영상을 파일로 먼저 저장하지 않음
- HTML5 `<video>` 사용
- 서버가 Range 헤더를 원본 스트림에 전달
- `206 Partial Content`를 그대로 전달해 탐색/재생 지원
- YouTube URL만 허용해 임의 프록시(SSRF)로 쓰이지 않도록 제한
- 추출된 임시 스트림 URL은 메모리에만 저장하고 15분 뒤 만료

## 실행

```bash
python -m pip install -r requirements.txt
python app.py
```

그 뒤 브라우저에서:

```text
http://127.0.0.1:8765/
```

운영 서버:

```bash
gunicorn -b 0.0.0.0:$PORT app:app
```

## 제한 영상

공개 영상용입니다. YouTube가 로그인 또는 연령 확인을 요구하는 영상은 기본 상태에서 재생되지 않습니다.

본인 계정으로 접근 권한이 있는 미디어를 개인 환경에서 재생해야 하는 경우에만 Netscape 형식의 `cookies.txt`를 이 폴더에 둘 수 있습니다. 인증 쿠키는 계정 자격 증명에 해당하므로 공개 GitHub나 공개 서버에 업로드하지 마세요.
