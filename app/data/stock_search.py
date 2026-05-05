"""
股票搜索工具
提供全量A股/港股/美股列表 + 模糊联想搜索
"""
import json
import time
from pathlib import Path
from functools import lru_cache

CACHE_FILE = Path(__file__).parent / "stock_list.json"


def _ensure_dir():
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_stock_list() -> list[dict]:
    """
    获取全量股票列表，优先从本地缓存（24h有效），否则从 AKShare 拉取。
    返回: [{"code": "sh600519", "name": "贵州茅台", "market": "沪市"}, ...]
    """
    _ensure_dir()

    if CACHE_FILE.exists():
        age = time.time() - CACHE_FILE.stat().st_mtime
        if age < 86400:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)

    try:
        import akshare as ak
        stocks: list[dict] = []

        # 静默 AKShare 进度条
        try:
            import tqdm
            _orig_update = tqdm.tqdm.update
            tqdm.tqdm.update = lambda self, n=1: None  # noqa: E731
        except Exception:
            pass

        # 沪市
        try:
            df = ak.stock_info_sh_name_code(symbol="主板A股")
            for _, r in df.iterrows():
                code = str(r.get("证券代码", "")).strip()
                name = str(r.get("证券简称", "")).strip()
                if code and name:
                    stocks.append({"code": f"sh{code}", "name": name, "market": "沪市"})
        except Exception as e:
            print(f"沪市股票列表获取失败: {e}")

        # 深市
        try:
            df = ak.stock_info_sz_name_code(symbol="A股列表")
            for _, r in df.iterrows():
                code = str(r.get("A股代码", r.get("代码", ""))).strip()
                name = str(r.get("A股简称", r.get("简称", ""))).strip()
                if code and name:
                    stocks.append({"code": f"sz{code}", "name": name, "market": "深市"})
        except Exception as e:
            print(f"深市股票列表获取失败: {e}")

        # 北交所（数据量较大，跳过以加快加载速度）
        # try:
        #     df = ak.stock_info_bj_name_code()
        #     for _, r in df.iterrows():
        #         code = str(r.get("股票代码", "")).strip()
        #         name = str(r.get("公司简称", "")).strip()
        #         if code and name:
        #             stocks.append({"code": f"bj{code}", "name": name, "market": "北交所"})
        # except Exception as e:
        #     print(f"北交所股票列表获取失败: {e}")

        # 去重（按 code）
        seen = set()
        unique = []
        for s in stocks:
            if s["code"] not in seen:
                seen.add(s["code"])
                unique.append(s)

        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(unique, f, ensure_ascii=False)

        print(f"股票列表已缓存，共 {len(unique)} 条")
        return unique

    except Exception as e:
        print(f"股票列表获取失败: {e}")
        return []


def search_stocks(query: str, top_n: int = 15) -> list[dict]:
    """
    模糊搜索股票
    query: 代码或名称中的任意字符（不区分大小写）
    """
    query = query.strip().lower()
    if not query:
        return []

    all_stocks = get_stock_list()

    # 精确 code 匹配（含前缀，如 sh600519）
    exact = [s for s in all_stocks if s["code"].lower() == query]
    # 纯数字 code 匹配（去掉前缀，如 600519）
    code_num = [s for s in all_stocks if s["code"][2:].lower() == query]
    # code 前缀匹配
    prefix = [s for s in all_stocks
              if s["code"][2:].lower().startswith(query) and s not in exact and s not in code_num]
    # 名称包含匹配
    name_hit = [s for s in all_stocks
                if query in s["name"].lower() and s not in exact and s not in code_num and s not in prefix]

    result = []
    seen = set()
    for s in exact + code_num + prefix + name_hit:
        if s["code"] not in seen:
            seen.add(s["code"])
            result.append(s)
            if len(result) >= top_n:
                break
    return result


# ── 演示 ──────────────────────────────────────────────
if __name__ == "__main__":
    print("搜索 '茅台':", search_stocks("茅台"))
    print("搜索 '600519':", search_stocks("600519"))
    print("搜索 'ai':", search_stocks("ai"))
