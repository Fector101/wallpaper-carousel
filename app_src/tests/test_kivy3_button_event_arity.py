"""
Static guard for the Kivy 3.0 button event arity.

Kivy 3.0 changed `ButtonBehavior` so that `on_press`/`on_release`/`on_cancel`
are dispatched with a touch (`kivy/uix/behaviors/button.py`). Every callback
attached to those events therefore has to accept two positional arguments
(`instance, touch`) - a `lambda x: ...` or a `def handler(self, _)` raises
TypeError the moment the button is tapped, so the button silently dies.

Widgets can't be instantiated in the test environment (no window provider), so
this walks the AST instead of dispatching real touches.
"""

import ast
from pathlib import Path

import pytest

APP_SRC = Path(__file__).resolve().parent.parent
BUTTON_EVENTS = {"on_press", "on_release", "on_cancel"}


def _accepts_two_args(node, is_bound_method):
    args = node.args
    positional = list(args.posonlyargs) + list(args.args)
    if is_bound_method:
        positional = positional[1:]  # self is supplied by the binding
    if args.vararg is not None:
        return True
    return len(positional) - len(args.defaults) <= 2 <= len(positional)


def _unsupported_callbacks(path):
    """Describe every button-event callback in `path` that can't take a touch."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    problems = []
    for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        methods = {
            m.name: m
            for m in cls.body
            if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for call in ast.walk(cls):
            if not isinstance(call, ast.Call):
                continue
            for keyword in call.keywords:
                if keyword.arg not in BUTTON_EVENTS:
                    continue
                value = keyword.value
                if isinstance(value, ast.Lambda):
                    ok = _accepts_two_args(value, is_bound_method=False)
                    name = "lambda"
                elif (
                    isinstance(value, ast.Attribute)
                    and isinstance(value.value, ast.Name)
                    and value.value.id == "self"
                    and value.attr in methods
                ):
                    ok = _accepts_two_args(methods[value.attr], is_bound_method=True)
                    name = f"{cls.name}.{value.attr}"
                else:
                    continue  # inherited method, ObjectProperty, subscript, ...
                if not ok:
                    problems.append(f"line {value.lineno}: {name} ({keyword.arg})")
    return problems


def _source_files():
    for path in sorted(APP_SRC.rglob("*.py")):
        if path.relative_to(APP_SRC).parts[0] in {"tests", "android_notify"}:
            continue
        yield path


@pytest.mark.parametrize("path", list(_source_files()), ids=lambda p: p.name)
def test_button_event_callbacks_accept_a_touch(path):
    problems = _unsupported_callbacks(path)
    assert not problems, f"{path.name} needs (instance, touch) for: " + ", ".join(
        problems
    )
