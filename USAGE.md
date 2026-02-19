# confluence2md 사용법

## 사전 설정

`.env` 파일을 프로젝트 루트 또는 `~/.confluence_2_md.env`에 생성:

```
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net/wiki
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_TOKEN=your-api-token
```

설치:

```bash
pip install -e ".[dev]"
```

---

## CLI

### 파일로 저장

```bash
# output/ 폴더에 페이지 제목으로 자동 저장 (기본)
confluence2md "<url>" -o

# 특정 폴더에 저장
confluence2md "<url>" -o docs

# 파일명 직접 지정
confluence2md "<url>" -o my-file.md
```

출력 구조:

```
output/
├── 페이지_제목.md
└── 페이지_제목/        ← 이미지 폴더 (md 파일과 동일 이름)
    ├── diagram.jpg
    └── screenshot.png
```

### 기타 옵션

```bash
# stdout 출력 (파일 생성 안 함)
confluence2md "<url>"

# JSON 출력 (프로그래밍용, 이미지 다운로드 안 함)
confluence2md "<url>" --json

# 이미지 다운로드 생략
confluence2md "<url>" -o --no-images
```

### 지원하는 URL 형식

```bash
# 표준 URL
confluence2md "https://domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Title" -o

# 짧은 URL
confluence2md "https://domain.atlassian.net/wiki/x/AbCdEf" -o

# 페이지 ID만
confluence2md "123456" -o
```

---

## Claude Code 플러그인

### /confluence 커맨드

```
/confluence <url>           → output/{페이지제목}.md 에 저장
/confluence <url> docs      → docs/{페이지제목}.md 에 저장
```

### Skill (자동 트리거)

대화에 `atlassian.net/wiki` URL을 포함하면 자동으로 페이지 내용을 가져와서 답변에 활용합니다.

```
이 페이지 요약해줘: https://domain.atlassian.net/wiki/x/AbCdEf
```

---

## 삭제

페이지 제목과 동일한 이름의 `.md` 파일과 폴더를 함께 삭제하면 됩니다.

```bash
rm output/페이지_제목.md
rm -rf output/페이지_제목/
```
