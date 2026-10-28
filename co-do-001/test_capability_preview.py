"""Pure-standard-library unit tests for the A2A skill-preview composition."""
import unittest
from types import SimpleNamespace as NS

from capability_preview import selection_description


def card(description="", skills=()):
    return NS(description=description, skills=list(skills))


def skill(name, description=""):
    return NS(name=name, description=description)


class SkillPreviewTests(unittest.TestCase):
    def test_no_skills_preserves_base_description(self):
        self.assertEqual(selection_description(card("General agent")), "General agent")

    def test_skills_exposed_for_capability_selection(self):
        result = selection_description(
            card("Research agent", [skill("bibliography", "Find papers"),
                                    skill("analysis", "Analyze datasets")])
        )
        self.assertIn("Research agent", result)
        self.assertIn("bibliography: Find papers", result)
        self.assertIn("analysis: Analyze datasets", result)

    def test_explicit_override_is_unchanged(self):
        result = selection_description(
            card("Generic", [skill("analysis", "Use R")]),
            explicit_description="Only for approved legal research",
        )
        self.assertEqual(result, "Only for approved legal research")

    def test_card_content_collapsed_to_single_line(self):
        result = selection_description(
            card("Generic", [skill("lab\ninstrument", "Measure\tvoltage")])
        )
        self.assertIn("lab instrument: Measure voltage", result)

    def test_output_is_bounded(self):
        result = selection_description(
            card("D" * 1000, [skill("measure", "x" * 1000)]), max_chars=80
        )
        self.assertLessEqual(len(result), 80)

    def test_skill_limit_applies(self):
        result = selection_description(
            card("agent", [skill("one"), skill("two"), skill("three")]),
            max_skills=2,
        )
        self.assertIn("one", result)
        self.assertIn("two", result)
        self.assertNotIn("three", result)

    def test_no_named_skills_does_not_fabricate_capabilities(self):
        result = selection_description(card("Base", [skill("", "Mystery")]))
        self.assertEqual(result, "Base")

    def test_invalid_limits_rejected(self):
        with self.assertRaises(ValueError):
            selection_description(card(), max_chars=20)
        with self.assertRaises(ValueError):
            selection_description(card(), max_skills=-1)

    def test_two_generic_agents_expose_distinct_skills(self):
        a = selection_description(card("General assistant", [skill("translation", "Translate documents")]))
        b = selection_description(card("General assistant", [skill("statistics", "Analyze samples")]))
        self.assertNotEqual(a, b)
        self.assertIn("translation", a)
        self.assertIn("statistics", b)

    def test_determinism(self):
        c = card("Agent", [skill("audit", "Review docs")])
        self.assertEqual(selection_description(c), selection_description(c))


if __name__ == "__main__":
    unittest.main(verbosity=2)
