import importlib.util
import unittest
from pathlib import Path
from datetime import datetime, timezone

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/mcd-regret-less/scripts/planner.py'
spec = importlib.util.spec_from_file_location('planner', SCRIPT) if SCRIPT.exists() else None
planner = importlib.util.module_from_spec(spec) if spec else None
if spec:
    spec.loader.exec_module(planner)

NOW = datetime(2026, 10, 10, 4, tzinfo=timezone.utc)
CONTEXT = {'store_id': 'demo-store', 'dining_mode': 'pickup'}

def quote(identifier, amount, items, **extra):
    return dict(id=identifier, total_cents=amount, items=items, source='demo',
                quoted_at='2026-10-10T12:00:00+08:00', context=CONTEXT, **extra)

def data():
    return {'mode': 'demo', 'context': CONTEXT, 'baseline_id': 'original',
            'preferences': {'budget_cents': 3000, 'required': {'burger': 1},
                            'desired': {'burger': 1, 'fries-m': 1, 'cola': 1},
                            'forbidden': [], 'weights': {'fries-m': 3, 'cola': 2}},
            'candidates': [quote('original', 3600, {'burger': 1, 'fries-m': 1, 'cola': 1}),
                           quote('bundle', 3200, {'burger': 1, 'fries-m': 1, 'cola': 1}),
                           quote('small-fries', 2900, {'burger': 1, 'fries-s': 1, 'cola': 1}),
                           quote('cheap', 2400, {'burger': 1})]}

class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(planner, '价格比较功能尚未实现')

    def test_three_plans_and_real_gap(self):
        out = planner.compare(data(), NOW)
        self.assertEqual(out['plans']['keep']['id'], 'bundle')
        self.assertEqual(out['plans']['keep']['over_budget_cents'], 200)
        self.assertEqual(out['plans']['small_change']['id'], 'small-fries')
        self.assertEqual(out['plans']['budget']['id'], 'cheap')
        self.assertEqual(out['plans']['small_change']['savings_cents'], 700)
        self.assertEqual(out['plans']['small_change']['missing'], {'fries-m': 1})

    def test_locked_cola_cannot_be_removed(self):
        d = data(); d['preferences']['required']['cola'] = 1
        self.assertEqual(planner.compare(d, NOW)['plans']['budget']['id'], 'small-fries')

    def test_forbidden_excludes_even_the_cheapest(self):
        d = data(); d['preferences']['forbidden'] = ['fries-s']
        self.assertNotEqual(planner.compare(d, NOW)['plans']['budget']['id'], 'small-fries')

    def test_no_plan_in_budget_explains_gap(self):
        d = data(); d['preferences']['budget_cents'] = 2000
        out = planner.compare(d, NOW)
        self.assertIsNone(out['plans']['budget'])
        self.assertEqual(out['minimum_gap_cents'], 400)

    def test_stale_future_and_wrong_store_are_excluded(self):
        for field, value in [('quoted_at', '2026-10-10T11:00:00+08:00'),
                             ('quoted_at', '2026-10-10T13:00:00+08:00'),
                             ('context', {'store_id': 'other', 'dining_mode': 'pickup'})]:
            d = data(); d['candidates'][3][field] = value
            out = planner.compare(d, NOW)
            self.assertNotEqual(out['plans']['budget']['id'], 'cheap')
            self.assertTrue(out['excluded'])

    def test_demo_never_mixes_with_live(self):
        d = data(); d['mode'] = 'live'
        out = planner.compare(d, NOW)
        self.assertIsNone(out['plans']['keep'])
        self.assertEqual(len(out['excluded']), 4)

    def test_error_quote_cannot_rank(self):
        d = data(); d['candidates'][3]['is_error'] = True
        self.assertEqual(planner.compare(d, NOW)['plans']['budget']['id'], 'small-fries')

    def test_money_is_integer_nonnegative(self):
        for value in [-1, 24.9, True, '2400']:
            d = data(); d['candidates'][3]['total_cents'] = value
            self.assertNotEqual(planner.compare(d, NOW)['plans']['budget']['id'], 'cheap')

    def test_unavailable_baseline_does_not_invent_savings(self):
        d = data(); d['baseline_id'] = 'unknown'
        self.assertIsNone(planner.compare(d, NOW)['plans']['keep']['savings_cents'])

    def test_duplicate_id_rejected(self):
        d = data(); d['candidates'][1]['id'] = 'original'
        with self.assertRaises(ValueError): planner.compare(d, NOW)

    def test_incremental_preference_update(self):
        prefs = data()['preferences']
        updated = planner.update_preferences(prefs, {'budget_cents': 3500, 'required': {'cola': 1}})
        self.assertEqual(updated['required'], {'burger': 1, 'cola': 1})
        self.assertEqual(updated['desired'], prefs['desired'])
        self.assertEqual(prefs['budget_cents'], 3000)

    def test_unlock_is_explicit(self):
        updated = planner.update_preferences(data()['preferences'], {'required': {'burger': 0}})
        self.assertNotIn('burger', updated['required'])

    def test_invalid_preferences_rejected(self):
        d = data(); d['preferences']['budget_cents'] = -1
        with self.assertRaises(ValueError): planner.compare(d, NOW)

    def test_live_requires_quote_evidence(self):
        d = data(); d['mode'] = 'live'
        for c in d['candidates']: c['source'] = 'mcd-mcp'
        self.assertEqual(len(planner.compare(d, NOW)['excluded']), 4)

if __name__ == '__main__': unittest.main()
