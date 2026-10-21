import pytest

from skillaudit import frontmatter


def test_basic_scalars_and_body():
    p = frontmatter.parse('---\nname: a\ndescription: "Hi: there"\n---\n# Body\n')
    assert p.data == {"name": "a", "description": "Hi: there"}
    assert p.body.startswith("# Body")
    assert p.body_start_line == 5


def test_block_scalars():
    p = frontmatter.parse("---\ndescription: >\n  one\n  two\n\n  three\nname: x\n---\n")
    assert p.data["description"] == "one two\nthree"
    q = frontmatter.parse("---\ndescription: |\n  a\n  b\n---\n")
    assert q.data["description"] == "a\nb"


def test_nested_map_and_list():
    p = frontmatter.parse('---\nmetadata:\n  author: me\n  version: "1.0"\ntags:\n  - a\n  - b\n---\n')
    assert p.data["metadata"] == {"author": "me", "version": "1.0"}
    assert p.data["tags"] == ["a", "b"]


def test_comment_stripped_and_bom():
    p = frontmatter.parse("﻿---\nname: x # trailing\n---\n")
    assert p.data["name"] == "x"


@pytest.mark.parametrize(
    "text", ["no fence", "---\nname: x\n", "---\nname x\n---\n", "---\na: 1\na: 2\n---\n", "---\na: 'open\n---\n"]
)
def test_errors(text):
    with pytest.raises(frontmatter.FrontmatterError):
        frontmatter.parse(text)
