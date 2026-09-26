# browser-access-probe

원본 사이트만 대상으로 하는 Playwright/Chrome 접근 진단 도구입니다.

## 원본 전용 정책

이 프로젝트는 이제 다음을 **사용하지 않습니다**.

- 미러 사이트
- 복제본
- 캐시 사본
- 대체 도메인

요청한 URL의 **원래 호스트와 최종 호스트가 정확히 같아야 성공**으로 판정합니다.

## NamuWiki 대상 실행

```bash
cd browser-access-probe
npm install
npm run namuwiki
```

이 명령은 로컬의 전용 Chrome 세션을 시작하거나 기존 세션에 붙은 뒤, 원본 `namu.wiki` 문서만 엽니다.

Cloudflare 등에서 정상적인 브라우저 검증을 요구하면 그 탭을 그대로 유지하며 기다립니다. 검증을 프로그램이 대신 풀지는 않습니다.

## 로컬 Chrome 세션

전용 Chrome 시작:

```bash
npm run chrome
```

이미 실행 중인 Chrome 세션에 붙기:

```bash
npm run attach -- "https://namu.wiki/w/..."
```

## 기타 모드

영구 Playwright 프로필:

```bash
npm run auto -- https://example.com
```

화면이 보이는 영구 프로필:

```bash
npm run browser -- https://example.com
```

임시 브라우저:

```bash
npm run probe -- https://example.com
```

## 성공 조건

- HTTP 응답이 정상적으로 로드됨
- 차단/챌린지 페이지가 아님
- 최종 URL의 호스트가 요청한 원본 호스트와 동일함

다른 도메인으로 이동하면 성공으로 처리하지 않습니다.

## 검증

```bash
npm run check
npm test
```
