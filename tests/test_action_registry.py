"""Tests for likedmusic.actions.base — action registry."""

from likedmusic.actions.base import Action, get_actions, register, _actions


class TestRegister:
    def setup_method(self):
        self._original = _actions.copy()
        _actions.clear()

    def teardown_method(self):
        _actions.clear()
        _actions.extend(self._original)

    def test_register_adds_action(self):
        register("Test", "A test action", lambda dry_run: None)
        actions = get_actions()
        assert len(actions) == 1
        assert actions[0].name == "Test"
        assert actions[0].description == "A test action"

    def test_registration_order_preserved(self):
        register("First", "desc", lambda dry_run: None)
        register("Second", "desc", lambda dry_run: None)
        register("Third", "desc", lambda dry_run: None)
        names = [a.name for a in get_actions()]
        assert names == ["First", "Second", "Third"]

    def test_get_actions_returns_copy(self):
        register("X", "desc", lambda dry_run: None)
        actions = get_actions()
        actions.clear()
        assert len(get_actions()) == 1
