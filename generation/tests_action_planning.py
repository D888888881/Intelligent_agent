"""动作规划 L3.5 契约测试（不依赖完整策划 LLM）。"""

from django.test import SimpleTestCase

from generation.services.action_planning import apply_action_planning
from generation.services.action_planning.role_allow import allowed_action_ids_for_shot
from generation.services.pipeline.layer3_5_action import run_layer3_5_action_planning


def _listing_shots():
    roles = [
        (1, "hero_hook"),
        (2, "white_bg_catalog"),
        (3, "pain_empathy"),
        (4, "usp_primary"),
        (5, "usp_secondary"),
    ]
    return [
        {"index": i, "role": r, "human_cast_mode": "none"}
        for i, r in roles
    ]


class ActionPlanningTests(SimpleTestCase):
    def test_preserves_roles(self):
        plan = {
            "plan_template": "generic",
            "product_analysis": {"category": "kitchen gadget"},
            "shots": _listing_shots(),
        }
        roles_before = {s["index"]: s["role"] for s in plan["shots"]}
        plan = apply_action_planning(plan)
        roles_after = {int(s["index"]): s["role"] for s in plan["shots"]}
        self.assertEqual(roles_before, roles_after)

    def test_white_bg_limited_actions(self):
        shot = {"index": 2, "role": "white_bg_catalog", "human_cast_mode": "none"}
        allowed = allowed_action_ids_for_shot(
            shot, plugin_ids=("G01", "G02", "B05"), shot_ordinal=2
        )
        self.assertEqual(allowed, ("G01", "G02"))

    def test_beauty_plugin_uses_increment(self):
        plan = {
            "plan_template": "tk_mx_ecommerce_9",
            "category_strategy": {"category_bucket": "beauty_skincare"},
            "product_analysis": {"category": "facial serum"},
            "shots": _listing_shots(),
        }
        plan = apply_action_planning(plan)
        self.assertEqual(plan["action_planning"]["plugin"], "beauty_skincare")
        ids = {s.get("primary_action_id") for s in plan["shots"]}
        self.assertTrue(all(x for x in ids))
        white = next(s for s in plan["shots"] if s["role"] == "white_bg_catalog")
        self.assertIn(white["primary_action_id"], ("G01", "G02"))

    def test_skips_reference_guided(self):
        plan = {"plan_template": "reference_guided", "shots": _listing_shots()}
        plan, snap = run_layer3_5_action_planning(plan)
        self.assertEqual(snap["status"], "skip")
        self.assertFalse(any(s.get("primary_action_id") for s in plan["shots"]))

    def test_each_shot_gets_lock(self):
        plan = {
            "plan_template": "generic",
            "shots": _listing_shots(),
        }
        plan = apply_action_planning(plan)
        for shot in plan["shots"]:
            self.assertTrue(shot.get("product_action_lock_en"))
            self.assertTrue(shot.get("primary_action_id"))

    def test_shampoo_uses_beauty_pool(self):
        plan = {
            "plan_template": "generic",
            "product_analysis": {
                "category": "personal care",
                "product_name_en": "Argan Oil Shampoo 500ml",
            },
            "shots": _listing_shots(),
        }
        plan = apply_action_planning(plan)
        self.assertEqual(plan["action_planning"]["plugin"], "beauty_skincare")

    def test_body_wash_zh_prompt(self):
        from generation.services.beauty_personal_care import plan_uses_beauty_action_pool

        self.assertTrue(
            plan_uses_beauty_action_pool(
                {"product_analysis": {}, "user_prompt": "帮我做沐浴露9张主图"}
            )
        )