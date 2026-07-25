from app.services.board_directory import BoardDirectoryService

POPULAR_HTML = """
<html>
  <body>
    <a href="/bbs/Tech_Job/index.html">
      <div>Tech_Job</div><div>321</div><div>工作</div><div>科技業工作板</div>
    </a>
    <a href="/bbs/TaichungBun/index.html">
      <div>TaichungBun</div><div>120</div><div>台中</div><div>台中板</div>
    </a>
  </body>
</html>
"""

CATEGORY_HTML = """
<html>
  <head><title>分類看板 - 批踢踢實業坊</title></head>
  <body>
    <a href="/cls/10">H_Group 遊戲與科技</a>
    <a href="/bbs/Tech_Job/index.html">Tech_Job 321 工作 科技業工作板</a>
  </body>
</html>
"""


def test_parse_popular_page() -> None:
    boards = BoardDirectoryService.parse_popular_page(POPULAR_HTML)

    assert [board.board for board in boards] == ["Tech_Job", "TaichungBun"]
    assert boards[0].popularity == 321
    assert boards[0].category == "工作"
    assert boards[0].title == "科技業工作板"


def test_parse_category_page() -> None:
    category = BoardDirectoryService.parse_category_page(CATEGORY_HTML, category_id=1)

    assert category.category_id == 1
    assert category.entries[0].kind == "category"
    assert category.entries[0].category_id == 10
    assert category.entries[1].kind == "board"
    assert category.entries[1].board == "Tech_Job"
