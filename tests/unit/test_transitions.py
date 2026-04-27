from __future__ import annotations

import unittest

from quoteguard.orchestration.state import ConversationState, missing_required_slots, next_phase


class TransitionTest(unittest.TestCase):
    def test_risk_profile_waits_for_missing_slots(self) -> None:
        state = ConversationState(phase="risk_profile", product_type="home_contents", slots={"postcode": "3000"})
        self.assertIn("property_type", missing_required_slots(state))
        self.assertEqual(next_phase(state), "risk_profile")

    def test_risk_profile_advances_when_slots_complete(self) -> None:
        state = ConversationState(
            phase="risk_profile",
            product_type="home_contents",
            slots={
                "property_type": "house",
                "postcode": "3000",
                "security_features": "alarm",
                "occupancy": "owner_occupied",
            },
        )
        self.assertEqual(next_phase(state), "coverage_questions")


if __name__ == "__main__":
    unittest.main()
