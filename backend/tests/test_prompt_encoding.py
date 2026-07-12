from pathlib import Path


def test_chinese_prompt_files_are_readable_utf8():
    prompt_dir = Path(__file__).resolve().parents[1] / "prompts"
    combined = "\n".join(
        (prompt_dir / name).read_text(encoding="utf-8")
        for name in ("reasoner.yaml", "report.yaml")
    )

    assert "你是一个推理引擎" in combined
    assert "你是一个报告生成器" in combined
    assert "关键规则" in combined
    assert "浣犳槸" not in combined
    assert "鍏抽敭" not in combined
    assert "鎶ュ憡" not in combined
