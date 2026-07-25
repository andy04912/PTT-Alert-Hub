from app.core.boards import normalize_board_name
from app.services.ptt_crawler import PttCrawler

HTML = """
<html>
  <body>
    <div class="r-ent">
      <div class="title">
        <a href="/bbs/Tech_Job/M.1784764800.A.001.html">[徵才] React 工程師</a>
      </div>
      <div class="meta">
        <div class="author">andy123</div>
        <div class="date"> 7/23</div>
      </div>
    </div>
    <div class="btn-group btn-group-paging">
      <a class="btn wide" href="/bbs/Tech_Job/index9999.html">‹ 上頁</a>
    </div>
  </body>
</html>
"""


def test_parse_index_page() -> None:
    articles, previous_page = PttCrawler.parse_index_page(
        HTML,
        board="Tech_Job",
        base_url="https://www.ptt.cc",
    )

    assert len(articles) == 1
    assert articles[0].title == "[徵才] React 工程師"
    assert articles[0].author == "andy123"
    assert articles[0].url.startswith("https://www.ptt.cc/")
    assert previous_page == "https://www.ptt.cc/bbs/Tech_Job/index9999.html"


def test_normalize_taichung_alias() -> None:
    assert normalize_board_name("Taichung") == "TaichungBun"
    assert normalize_board_name("taichungbun") == "TaichungBun"
