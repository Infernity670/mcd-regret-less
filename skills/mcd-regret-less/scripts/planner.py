"""Compare explicitly quoted baskets. Internal contract, NOT an MCP schema."""
import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def quantities(value):
    return isinstance(value, dict) and all(isinstance(k, str) and k and integer(v, 1)
                                           for k, v in value.items())


def validate_preferences(prefs):
    if not isinstance(prefs, dict) or not integer(prefs.get('budget_cents')):
        raise ValueError('budget_cents 必须是非负整数分')
    for key in ('required', 'desired'):
        if not quantities(prefs.get(key, {})):
            raise ValueError(f'{key} 必须是餐品标识到正整数数量的映射')
    if not quantities(prefs.get('weights', {})):
        raise ValueError('weights 必须是正整数权重')
    forbidden = prefs.get('forbidden', [])
    if not isinstance(forbidden, list) or not all(isinstance(x, str) and x for x in forbidden):
        raise ValueError('forbidden 必须是餐品标识列表')
    if set(forbidden) & set(prefs.get('required', {})):
        raise ValueError('必选餐品与禁选项冲突，请先澄清')


def update_preferences(prefs, patch):
    result = copy.deepcopy(prefs)
    if not isinstance(patch, dict) or set(patch) - {'budget_cents', 'required', 'desired', 'weights', 'forbidden'}:
        raise ValueError('未知偏好更新字段')
    for key, value in patch.items():
        if key in ('required', 'desired', 'weights'):
            if not isinstance(value, dict) or not all(integer(v) for v in value.values()):
                raise ValueError('偏好更新数量必须为非负整数；0表示明确移除')
            result.setdefault(key, {})
            for item, count in value.items():
                if count == 0:
                    result[key].pop(item, None)
                else:
                    result[key][item] = count
        else:
            result[key] = copy.deepcopy(value)
    validate_preferences(result)
    return result


def compare(data, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('当前时间必须包含时区')
    prefs = data['preferences']
    validate_preferences(prefs)
    mode = data.get('mode')
    if mode not in ('demo', 'live'):
        raise ValueError('mode 必须为 demo 或 live')
    context = data.get('context')
    if not isinstance(context, dict) or not context.get('store_id') or not context.get('dining_mode'):
        raise ValueError('必须提供门店与就餐方式上下文')
    ttl = data.get('max_quote_age_seconds', 300)
    if not integer(ttl, 1) or ttl > 300:
        raise ValueError('报价有效窗口应为1至300秒')
    candidates = data.get('candidates', [])
    if not isinstance(candidates, list) or len(candidates) > 100:
        raise ValueError('候选必须为列表，最多100个')
    seen, valid, excluded = set(), [], []
    for c in candidates:
        if not isinstance(c, dict) or not isinstance(c.get('id'), str) or not c['id'] or c['id'] in seen:
            raise ValueError('候选 id 必须是唯一非空字符串')
        seen.add(c['id'])
        reason = None
        if c.get('is_error') or c.get('available') is False:
            reason = '试算失败或不可售'
        elif not integer(c.get('total_cents')) or not quantities(c.get('items')) or not c['items']:
            reason = '缺少有效金额或餐品组成'
        elif c.get('source') != ('demo' if mode == 'demo' else 'mcd-mcp'):
            reason = '报价来源与运行模式不一致'
        elif c.get('context') != context:
            reason = '报价上下文不一致'
        else:
            try:
                quoted = datetime.fromisoformat(c['quoted_at'])
                if quoted.tzinfo is None or not 0 <= (now - quoted).total_seconds() <= ttl:
                    reason = '报价过期或时间无效'
            except (KeyError, TypeError, ValueError):
                reason = '缺少带时区的报价时间'
        if not reason and mode == 'live':
            evidence = c.get('evidence', {})
            if (not isinstance(evidence, dict) or evidence.get('tool') != 'calculate-price'
                    or not isinstance(evidence.get('call_ref'), str) or not evidence['call_ref'].strip()):
                reason = '缺少 calculate-price 调用依据'
        if not reason and any(c['items'].get(k, 0) < v for k, v in prefs.get('required', {}).items()):
            reason = '未满足不可替换餐品'
        if not reason and set(c['items']) & set(prefs.get('forbidden', [])):
            reason = '包含禁选餐品'
        if reason:
            excluded.append({'id': c['id'], 'reason': reason})
        else:
            valid.append(c)
    desired = dict(prefs.get('desired', {}))
    for item, count in prefs.get('required', {}).items():
        desired[item] = max(count, desired.get(item, 0))
    baseline = next((c for c in valid if c['id'] == data.get('baseline_id')), None)

    def score(c):
        return sum(max(0, count - c['items'].get(item, 0)) * prefs.get('weights', {}).get(item, 1)
                   for item, count in desired.items())

    def summarize(c):
        if c is None:
            return None
        missing = {k: v - c['items'].get(k, 0) for k, v in desired.items() if c['items'].get(k, 0) < v}
        added = {k: v - desired.get(k, 0) for k, v in c['items'].items() if v > desired.get(k, 0)}
        return {'id': c['id'], 'total_cents': c['total_cents'], 'items': c['items'],
                'missing': missing, 'added': added, 'preference_loss': score(c),
                'over_budget_cents': max(0, c['total_cents'] - prefs['budget_cents']),
                'savings_cents': baseline['total_cents'] - c['total_cents'] if baseline else None,
                'quoted_at': c['quoted_at'], 'evidence': c.get('evidence')}

    keepers = [c for c in valid if score(c) == 0]
    in_budget = [c for c in valid if c['total_cents'] <= prefs['budget_cents']]
    changes = [c for c in in_budget if score(c) > 0]
    choose = lambda pool, key: min(pool, key=key) if pool else None
    cheapest = choose(valid, lambda c: (c['total_cents'], score(c), c['id']))
    return {'mode': mode, 'label': '虚构演示价格' if mode == 'demo' else '实时查询候选比较',
            'context': context, 'budget_cents': prefs['budget_cents'],
            'claim': '仅比较输入且有效的候选；不代表全菜单最低价',
            'plans': {'keep': summarize(choose(keepers, lambda c: (c['total_cents'], c['id']))),
                      'small_change': summarize(choose(changes, lambda c: (score(c), c['total_cents'], c['id']))),
                      'budget': summarize(choose(in_budget, lambda c: (c['total_cents'], score(c), c['id'])))},
            'minimum_gap_cents': max(0, cheapest['total_cents'] - prefs['budget_cents']) if cheapest else None,
            'excluded': excluded, 'valid_candidate_count': len(valid)}


def main():
    parser = argparse.ArgumentParser(description='麦麦后悔药：比较已报价候选，或增量更新偏好')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('compare'); p.add_argument('input'); p.add_argument('--now')
    p = sub.add_parser('update'); p.add_argument('preferences'); p.add_argument('patch')
    args = parser.parse_args()
    try:
        read = lambda path: json.loads(Path(path).read_text(encoding='utf-8-sig'))
        if args.command == 'compare':
            payload = read(args.input)
            if args.now and payload.get('mode') != 'demo':
                raise ValueError('--now 只用于虚构演示，实时模式使用系统当前时间')
            result = compare(payload, datetime.fromisoformat(args.now) if args.now else None)
        else:
            result = update_preferences(read(args.preferences), read(args.patch))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f'输入无效：{error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
