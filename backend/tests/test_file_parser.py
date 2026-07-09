from importlib.util import find_spec

import pytest

from app.rag.file_parser import (
    FileParserError,
    get_supported_extensions,
    parse_docx_file,
    parse_file,
    parse_pdf_file,
    parse_text_file,
)


class TestParseTextFile:
    def test_utf8_text(self):
        content = b"Hello World\nHello Unicode"
        result = parse_text_file(content, "test.txt")
        assert result == "Hello World\nHello Unicode"

    def test_gbk_text(self):
        content = "你好世界".encode("gbk")
        result = parse_text_file(content, "test.txt")
        assert result == "你好世界"

    def test_empty_text(self):
        result = parse_text_file(b"", "test.txt")
        assert result == ""


class TestParsePdfFile:
    def test_pdf_not_installed(self):
        if find_spec("pypdf") or find_spec("PyPDF2"):
            pytest.skip("PDF parser is installed")
        with pytest.raises(FileParserError):
            parse_pdf_file(b"fake pdf", "test.pdf")

    def test_invalid_pdf_raises_parser_error(self):
        if not (find_spec("pypdf") or find_spec("PyPDF2")):
            pytest.skip("PDF parser is not installed")
        with pytest.raises(FileParserError, match="PDF"):
            parse_pdf_file(b"fake pdf", "test.pdf")


class TestParseFile:
    def test_txt_file(self):
        result = parse_file(b"Hello World", "test.txt")
        assert result == "Hello World"

    def test_md_file(self):
        result = parse_file(b"# Title\n\nContent", "test.md")
        assert result == "# Title\n\nContent"

    def test_csv_file(self):
        result = parse_file(b"name,age\nAlice,30\nBob,25", "test.csv")
        assert "Alice" in result

    def test_json_file(self):
        result = parse_file(b'{"key": "value"}', "test.json")
        assert '"key"' in result

    def test_unsupported_type(self):
        with pytest.raises(FileParserError):
            parse_file(b"content", "test.xyz")

    def test_docx_not_installed(self):
        if find_spec("docx"):
            pytest.skip("python-docx is installed")
        with pytest.raises(FileParserError):
            parse_docx_file(b"fake docx", "test.docx")


class TestGetSupportedExtensions:
    def test_returns_set(self):
        result = get_supported_extensions()
        assert isinstance(result, set)

    def test_contains_common_types(self):
        result = get_supported_extensions()
        assert ".txt" in result
        assert ".md" in result
        assert ".pdf" in result
        assert ".docx" in result
