"""Tests for scripts/validate_skills.py. Run with: python3 -m unittest discover -s tests"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate_skills  # noqa: E402

GOOD = '---\nname: "{name}"\ndescription: "Does a thing. Use when the user asks for the thing."\n---\n\n# Body\n'


def make_repo(tmp: Path, skills: dict[str, str], marketplace: dict | None = None) -> Path:
    for folder, content in skills.items():
        (tmp / "skills" / folder).mkdir(parents=True)
        (tmp / "skills" / folder / "SKILL.md").write_text(content, encoding="utf-8")
    if marketplace is not None:
        (tmp / ".claude-plugin").mkdir()
        (tmp / ".claude-plugin" / "marketplace.json").write_text(json.dumps(marketplace), encoding="utf-8")
    return tmp


class ValidateSkillsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_this_repo_is_valid(self):
        self.assertEqual(validate_skills.validate_repo(ROOT), [])

    def test_good_skill_passes(self):
        repo = make_repo(self.tmp, {"my-skill": GOOD.format(name="my-skill")})
        self.assertEqual(validate_skills.validate_repo(repo), [])

    def test_missing_frontmatter_fails(self):
        repo = make_repo(self.tmp, {"my-skill": "# No frontmatter\n"})
        self.assertIn("frontmatter", validate_skills.validate_repo(repo)[0])

    def test_name_must_match_folder(self):
        repo = make_repo(self.tmp, {"my-skill": GOOD.format(name="other-skill")})
        self.assertTrue(any("must match its folder" in p for p in validate_skills.validate_repo(repo)))

    def test_bad_name_characters_fail(self):
        repo = make_repo(self.tmp, {"My_Skill": GOOD.format(name="My_Skill")})
        self.assertTrue(any("lowercase" in p for p in validate_skills.validate_repo(repo)))

    def test_reserved_word_in_name_fails(self):
        repo = make_repo(self.tmp, {"claude-helper": GOOD.format(name="claude-helper")})
        self.assertTrue(any("must not contain" in p for p in validate_skills.validate_repo(repo)))

    def test_long_description_fails(self):
        content = f'---\nname: "my-skill"\ndescription: "{"x" * 1025}"\n---\nBody\n'
        repo = make_repo(self.tmp, {"my-skill": content})
        self.assertTrue(any("max 1024" in p for p in validate_skills.validate_repo(repo)))

    def test_angle_brackets_in_description_fail(self):
        content = '---\nname: "my-skill"\ndescription: "Use for <tags>"\n---\nBody\n'
        repo = make_repo(self.tmp, {"my-skill": content})
        self.assertTrue(any("angle brackets" in p for p in validate_skills.validate_repo(repo)))

    def test_empty_body_fails(self):
        content = '---\nname: "my-skill"\ndescription: "Does a thing."\n---\n'
        repo = make_repo(self.tmp, {"my-skill": content})
        self.assertTrue(any("no instructions" in p for p in validate_skills.validate_repo(repo)))

    def test_missing_reference_file_fails(self):
        content = GOOD.format(name="my-skill") + "Load `references/style.md` when needed.\n"
        repo = make_repo(self.tmp, {"my-skill": content})
        self.assertTrue(any("'references/style.md', which doesn't exist" in p for p in validate_skills.validate_repo(repo)))
        (repo / "skills" / "my-skill" / "references").mkdir()
        (repo / "skills" / "my-skill" / "references" / "style.md").write_text("x", encoding="utf-8")
        self.assertEqual(validate_skills.validate_repo(repo), [])

    def test_marketplace_must_list_every_skill(self):
        market = {"name": "m", "owner": {"name": "x"}, "plugins": [{"name": "a", "source": "./", "skills": ["./skills/a"]}]}
        repo = make_repo(self.tmp, {"a": GOOD.format(name="a"), "b": GOOD.format(name="b")}, market)
        self.assertTrue(any("'b' must be listed exactly once" in p for p in validate_skills.validate_repo(repo)))

    def test_marketplace_path_must_exist(self):
        market = {"name": "m", "owner": {"name": "x"}, "plugins": [{"name": "a", "source": "./", "skills": ["./skills/a", "./skills/missing"]}]}
        repo = make_repo(self.tmp, {"a": GOOD.format(name="a")}, market)
        self.assertTrue(any("has no SKILL.md" in p for p in validate_skills.validate_repo(repo)))


if __name__ == "__main__":
    unittest.main()
