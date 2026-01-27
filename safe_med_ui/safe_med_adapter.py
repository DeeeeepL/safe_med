import importlib
import inspect
import pkgutil
from dataclasses import dataclass
from typing import Callable, Optional, Tuple, Any, Dict


CANDIDATE_PACKAGES = [
    "safe_text",
    "anonymizers",
    "ner",
]

# 你仓库里“可能存在的入口名”（你可以继续加）
CANDIDATE_CALLABLE_NAMES = [
    "deidentify",
    "deidentify_text",
    "deid",
    "deid_text",
    "anonymize",
    "anonymize_text",
    "mask",
    "process",
    "run",
]


def _iter_modules(package_name: str):
    try:
        pkg = importlib.import_module(package_name)
    except Exception:
        return
    if not hasattr(pkg, "__path__"):
        return
    for m in pkgutil.walk_packages(pkg.__path__, prefix=pkg.__name__ + "."):
        yield m.name


def _find_callable_in_module(mod) -> Optional[Callable]:
    # 1) 直接找函数
    for name in CANDIDATE_CALLABLE_NAMES:
        if hasattr(mod, name):
            obj = getattr(mod, name)
            if callable(obj):
                return obj

    # 2) 找 class（含同名方法）
    for _, cls in inspect.getmembers(mod, inspect.isclass):
        for name in CANDIDATE_CALLABLE_NAMES:
            if hasattr(cls, name):
                # 实例方法
                try:
                    inst = cls()  # 要求可无参构造；否则跳过
                    meth = getattr(inst, name)
                    if callable(meth):
                        return meth
                except Exception:
                    continue

    return None


@dataclass
class SafeMedAdapter:
    """
    目标：尽量自动调用你 safe_med 仓库现有脱敏实现。
    约定：callable(text: str, **kwargs) -> str 或 -> (str, stats)
    """
    found: bool = False
    fn: Optional[Callable] = None
    where: str = ""

    def discover(self) -> "SafeMedAdapter":
        for pkg_name in CANDIDATE_PACKAGES:
            # 先尝试包本身
            try:
                mod0 = importlib.import_module(pkg_name)
                fn0 = _find_callable_in_module(mod0)
                if fn0:
                    self.found = True
                    self.fn = fn0
                    self.where = pkg_name
                    return self
            except Exception:
                pass

            # 再遍历子模块
            for mod_name in _iter_modules(pkg_name) or []:
                try:
                    mod = importlib.import_module(mod_name)
                    fn = _find_callable_in_module(mod)
                    if fn:
                        self.found = True
                        self.fn = fn
                        self.where = mod_name
                        return self
                except Exception:
                    continue

        self.found = False
        self.fn = None
        self.where = ""
        return self

    def deidentify(self, text: str, **kwargs) -> Tuple[str, Dict[str, int]]:
        if not self.found or not self.fn:
            raise RuntimeError("未发现可调用的 safe_med 脱敏入口")

        out = self.fn(text, **kwargs)

        # 兼容返回 str 或 (str, stats)
        if isinstance(out, tuple) and len(out) == 2 and isinstance(out[0], str) and isinstance(out[1], dict):
            return out[0], out[1]
        if isinstance(out, str):
            return out, {"safe_med_native": 1}
        return str(out), {"safe_med_native": 1}
