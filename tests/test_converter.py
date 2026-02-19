"""Tests for Confluence HTML → Markdown converter."""

from confluence_2_md.converter import convert


class TestCodeBlocks:
    def test_code_macro(self):
        html = """
        <ac:structured-macro ac:name="code">
            <ac:parameter ac:name="language">python</ac:parameter>
            <ac:plain-text-body>print("hello")</ac:plain-text-body>
        </ac:structured-macro>
        """
        md = convert(html)
        assert "```python" in md
        assert 'print("hello")' in md

    def test_code_block_no_language(self):
        html = """
        <ac:structured-macro ac:name="code">
            <ac:plain-text-body>some code</ac:plain-text-body>
        </ac:structured-macro>
        """
        md = convert(html)
        assert "```" in md
        assert "some code" in md


class TestInfoPanels:
    def test_info_panel(self):
        html = """
        <ac:structured-macro ac:name="info">
            <ac:rich-text-body><p>Important info here</p></ac:rich-text-body>
        </ac:structured-macro>
        """
        md = convert(html)
        assert "**Info**" in md
        assert "Important info here" in md

    def test_warning_panel(self):
        html = """
        <ac:structured-macro ac:name="warning">
            <ac:rich-text-body><p>Be careful!</p></ac:rich-text-body>
        </ac:structured-macro>
        """
        md = convert(html)
        assert "**Warning**" in md
        assert "Be careful!" in md

    def test_panel_with_title(self):
        html = """
        <ac:structured-macro ac:name="note">
            <ac:parameter ac:name="title">My Title</ac:parameter>
            <ac:rich-text-body><p>Content here</p></ac:rich-text-body>
        </ac:structured-macro>
        """
        md = convert(html)
        assert "**Note: My Title**" in md


class TestExpandMacro:
    def test_expand(self):
        html = """
        <ac:structured-macro ac:name="expand">
            <ac:parameter ac:name="title">Details</ac:parameter>
            <ac:rich-text-body><p>Hidden content</p></ac:rich-text-body>
        </ac:structured-macro>
        """
        md = convert(html)
        assert "<details>" in md
        assert "<summary>Details</summary>" in md
        assert "Hidden content" in md


class TestTaskLists:
    def test_checked_and_unchecked(self):
        html = """
        <ac:task-list>
            <ac:task>
                <ac:task-status>complete</ac:task-status>
                <ac:task-body>Done task</ac:task-body>
            </ac:task>
            <ac:task>
                <ac:task-status>incomplete</ac:task-status>
                <ac:task-body>Todo task</ac:task-body>
            </ac:task>
        </ac:task-list>
        """
        md = convert(html)
        assert "[x]" in md
        assert "Done task" in md
        assert "[ ]" in md
        assert "Todo task" in md


class TestUserMentions:
    def test_user_mention(self):
        html = """
        <ac:link>
            <ri:user ri:account-id="abc123" />
            <ac:plain-text-link-body>John Doe</ac:plain-text-link-body>
        </ac:link>
        """
        md = convert(html)
        assert "@John Doe" in md


class TestStatusMacro:
    def test_status(self):
        html = """
        <ac:structured-macro ac:name="status">
            <ac:parameter ac:name="title">Done</ac:parameter>
        </ac:structured-macro>
        """
        md = convert(html)
        assert "**[DONE]**" in md


class TestEmoticons:
    def test_smile(self):
        html = '<ac:emoticon ac:name="smile" />'
        md = convert(html)
        assert "\U0001f642" in md

    def test_tick(self):
        html = '<ac:emoticon ac:name="tick" />'
        md = convert(html)
        assert "\u2705" in md


class TestImages:
    def test_attachment_image(self):
        html = """
        <ac:image>
            <ri:attachment ri:filename="diagram.png" />
        </ac:image>
        """
        md = convert(html, download_images=True)
        assert "![diagram.png](assets/diagram.png)" in md

    def test_url_image(self):
        html = """
        <ac:image>
            <ri:url ri:value="https://example.com/img.png" />
        </ac:image>
        """
        md = convert(html)
        assert "https://example.com/img.png" in md


class TestTocMacro:
    def test_toc_removed(self):
        html = """
        <ac:structured-macro ac:name="toc" />
        <p>Content after toc</p>
        """
        md = convert(html)
        assert "toc" not in md.lower() or "Content after toc" in md


class TestBasicHtml:
    def test_paragraph(self):
        md = convert("<p>Hello world</p>")
        assert "Hello world" in md

    def test_heading(self):
        md = convert("<h2>My Heading</h2>")
        assert "## My Heading" in md

    def test_table(self):
        html = """
        <table>
            <tr><th>A</th><th>B</th></tr>
            <tr><td>1</td><td>2</td></tr>
        </table>
        """
        md = convert(html)
        assert "A" in md
        assert "1" in md

    def test_empty_input(self):
        assert convert("") == ""
        assert convert("   ") == ""

    def test_noformat(self):
        html = """
        <ac:structured-macro ac:name="noformat">
            <ac:plain-text-body>raw text here</ac:plain-text-body>
        </ac:structured-macro>
        """
        md = convert(html)
        assert "raw text here" in md


class TestPageLinks:
    def test_page_link(self):
        html = """
        <ac:link>
            <ri:page ri:content-title="Other Page" />
        </ac:link>
        """
        md = convert(html)
        assert "Other Page" in md
