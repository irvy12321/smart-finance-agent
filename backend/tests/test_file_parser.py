"""
文件解析器单元测试
"""

import pytest

from app.rag.file_parser import (
    FileParserError,
    get_supported_extensions,
    parse_file,
    parse_pdf_file,
    parse_text_file,
)


class TestParseTextFile:
    """测试文本文件解析"""

    def test_utf8_text(self):
        """测试 UTF-8 文本"""
        content = "Hello World\n你好世界".encode()
        result = parse_text_file(content, "test.txt")
        assert result == "Hello World\n你好世界"

    def test_gbk_text(self):
        """测试 GBK 编码文本"""
        content = "你好世界".encode("gbk")
        result = parse_text_file(content, "test.txt")
        assert result == "你好世界"

    def test_empty_text(self):
        """测试空文本"""
        content = b""
        result = parse_text_file(content, "test.txt")
        assert result == ""


class TestParsePdfFile:
    """测试 PDF 文件解析"""

    def test_pdf_not_installed(self):
        """测试 PyPDF2 未安装的情况"""
        # 这个测试在 PyPDF2 已安装时会跳过
        try:
            import PyPDF2

            pytest.skip("PyPDF2 is installed")
        except ImportError:
            with pytest.raises(FileParserError, match="PyPDF2 未安装"):
                parse_pdf_file(b"fake pdf", "test.pdf")


class TestParseFile:
    """测试文件解析主函数"""

    def test_txt_file(self):
        """测试 TXT 文件"""
        content = b"Hello World"
        result = parse_file(content, "test.txt")
        assert result == "Hello World"

    def test_md_file(self):
        """测试 Markdown 文件"""
        content = b"# Title\n\nContent"
        result = parse_file(content, "test.md")
        assert result == "# Title\n\nContent"

    def test_csv_file(self):
        """测试 CSV 文件"""
        content = b"name,age\nAlice,30\nBob,25"
        result = parse_file(content, "test.csv")
        assert "Alice" in result

    def test_json_file(self):
        """测试 JSON 文件"""
        content = b'{"key": "value"}'
        result = parse_file(content, "test.json")
        assert '"key"' in result

    def test_unsupported_type(self):
        """测试不支持的文件类型"""
        with pytest.raises(FileParserError, match="不支持的文件类型"):
            parse_file(b"content", "test.xyz")

    def test_docx_not_installed(self):
        """测试 python-docx 未安装的情况"""
        try:
            import docx

            pytest.skip("python-docx is installed")
        except ImportError:
            with pytest.raises(FileParserError, match="python-docx 未安装"):
                parse_file(b"fake docx", "test.docx")


class TestGetSupportedExtensions:
    """测试获取支持的扩展名"""

    def test_returns_set(self):
        """测试返回类型"""
        result = get_supported_extensions()
        assert isinstance(result, set)

    def test_contains_common_types(self):
        """测试包含常见类型"""
        result = get_supported_extensions()
        assert ".txt" in result
        assert ".md" in result
        assert ".pdf" in result
        assert ".docx" in result
