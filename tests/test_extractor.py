from click.testing import CliRunner

from camofox_extract import cli
from camofox_extract.client import CamofoxAPIError
from camofox_extract.extractor import extract_urls


class FakeClient:
    def __init__(self, fail_on=None):
        self.fail_on = fail_on
        self.closed = []
        self.cleaned = False
        self._n = 0

    def create_tab(self):
        self._n += 1
        return f"t{self._n}"

    def navigate(self, tab_id, url):
        if url == self.fail_on:
            raise CamofoxAPIError(502, "boom")

    def wait_for_ready(self, tab_id, timeout=30, wait_for_network=True):
        pass

    def snapshot(self, tab_id):
        return '- heading "T" [level=1]\n- paragraph: body'

    def close_tab(self, tab_id):
        self.closed.append(tab_id)

    def cleanup(self):
        self.cleaned = True


def test_extract_urls_success_and_error():
    c = FakeClient(fail_on="https://bad")
    res = extract_urls(["https://ok", "https://bad"], client=c)
    assert res[0]["title"] == "T" and res[0]["content"] == "# T\n\nbody" and res[0]["error"] is None
    assert "HTTP 502" in res[1]["error"]
    assert c.closed == ["t1", "t2"]  # tabs closed even on failure


def test_cli_json_and_exit_code(monkeypatch):
    fake = FakeClient(fail_on="https://bad")
    monkeypatch.setattr(cli, "CamofoxClient", lambda **kw: fake)
    r = CliRunner().invoke(cli.main, ["--json", "https://ok"])
    assert r.exit_code == 0, r.output
    assert '"title": "T"' in r.output
    r = CliRunner().invoke(cli.main, ["https://bad"])
    assert r.exit_code == 1
