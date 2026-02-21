# Standards

- Tests use pytest (no unittest.TestCase subclassing)
- Fixtures in conftest.py for shared state
- Mocking via `unittest.mock.patch`
- Test files mirror source structure: `likedmusic/foo.py` -> `tests/test_foo.py`
- No tests touch the real filesystem outside of `tmp_path`
- No tests make real network calls or spawn real subprocesses
