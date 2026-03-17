import pytest
import re
from server.api.audit import _build_rules

def test_build_rules_block_mode():
    content = "service password-encryption\nno ip http server"
    rules = _build_rules(content, mode="block", should_exist=True)
    
    assert len(rules) == 1
    rule = rules[0]
    assert rule["type"] == "block"
    assert "original_words" in rule
    assert rule["original_words"] == ["service", "password-encryption", "no", "ip", "http", "server"]
    # Check if the unescaped words are present in some form
    assert "password" in rule["pattern"]

def test_build_rules_line_mode():
    content = "line1\nline2"
    rules = _build_rules(content, mode="line", should_exist=False)
    
    assert len(rules) == 2
    assert rules[0]["type"] == "line"
    assert rules[0]["original_words"] == ["line1"]
    assert rules[1]["original_words"] == ["line2"]
    assert rules[0]["should_exist"] is False

def test_build_rules_empty_content():
    rules = _build_rules("", mode="line", should_exist=True)
    assert rules == []
