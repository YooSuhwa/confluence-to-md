# confluence-to-md

Confluence 위키 페이지를 깔끔한 Markdown으로 변환하는 CLI 도구 + [Agent Skill](https://agentskills.io).

Confluence storage-format HTML을 Obsidian 호환 Markdown으로 변환하며, 이미지 첨부파일도 함께 다운로드합니다.

## 설치

```bash
pip install -e .
```

## 설정

`~/.confluence_2_md.env` 파일을 생성합니다:

```
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net/wiki
CONFLUENCE_USERNAME=your-email@example.com
CONFLUENCE_TOKEN=your-api-token
```

API 토큰은 [Atlassian API tokens](https://id.atlassian.com/manage-profile/security/api-tokens)에서 발급받을 수 있습니다.

## CLI 사용법

```bash
# stdout 출력
confluence2md "<url>"

# 파일로 저장 (output/ 폴더)
confluence2md "<url>" -o

# 특정 디렉토리에 저장
confluence2md "<url>" -o docs

# JSON 출력
confluence2md "<url>" --json

# 이미지 다운로드 생략
confluence2md "<url>" -o --no-images
```

### 지원 URL 형식

- 표준 URL: `https://domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Title`
- 짧은 URL: `https://domain.atlassian.net/wiki/x/AbCdEf`
- 페이지 ID: `123456`

## Obsidian Skill로 사용

이 프로젝트는 [Agent Skills 사양](https://agentskills.io/specification)을 따르는 skill을 포함합니다.

### Claude Code에서 사용

Obsidian vault의 `/.claude/skills/` 디렉토리에 `skills/confluence-to-md/` 폴더를 복사합니다:

```bash
cp -r skills/confluence-to-md /path/to/vault/.claude/skills/
```

이후 Claude Code에서 Confluence URL을 입력하면 자동으로 Markdown 파일로 변환합니다.

## 변환 지원 항목

- 코드 블록 (언어 지정 포함)
- 정보 패널 (info, note, warning, tip)
- 접기/펼치기 (expand)
- 체크리스트 (task list)
- 사용자 멘션
- 페이지 링크
- 상태 배지
- 이모티콘
- 이미지/첨부파일
- 테이블

## 라이선스

MIT
