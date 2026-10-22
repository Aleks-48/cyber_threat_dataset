from html.parser import HTMLParser
from pathlib import Path
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class LocalLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "href" in attrs:
            self.hrefs.append(attrs["href"])


def test_russian_site_links_and_mobile_layout():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert '<html lang="ru">' in html
    assert "@media(max-width:720px)" in html
    assert "0 / 13 500" in html
    assert "0,710346" in html and "0,558617" in html
    assert "raw_harvest_snapshot.jsonl" not in html
    parser = LocalLinks()
    parser.feed(html)
    for href in parser.hrefs:
        if href.startswith("./"):
            assert (ROOT / href[2:]).resolve().is_file(), href


def test_download_package_is_aggregate_only():
    package = ROOT / "downloads" / "ru_experiment_results.zip"
    with zipfile.ZipFile(package) as archive:
        assert archive.testzip() is None
        members = set(archive.namelist())
        assert members == {
            "analysis/experiments/ru_obscene_ml/metrics.json",
            "analysis/experiments/ru_obscene_ml/audit.json",
            "analysis/external_sources/MCA_Russian_Toxic_Comments/source_manifest.json",
            "analysis/target_corpus_status.json",
            "README_RU.txt",
        }
        metrics = json.loads(archive.read("analysis/experiments/ru_obscene_ml/metrics.json"))
        assert len(metrics["models"]) == 5
        status = json.loads(archive.read("analysis/target_corpus_status.json"))
        assert status["verified_target_messages"] == 0
        assert status["required_target_messages"] == 13500

