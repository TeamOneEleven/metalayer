"""Tests for query memory ring buffer."""

from pathlib import Path

import frontmatter

from metalayer.query_memory import QueryMemory


def test_write_creates_file(queries_dir: Path):
    qm = QueryMemory(queries_dir)
    path = qm.write(
        question="What is revenue by month?",
        sql="SELECT month, SUM(amount) FROM orders GROUP BY month",
        result_summary="12 rows, $2.3M total",
        objects_in=["orders.revenue", "orders.order_date"],
        objects_not_in=["discount_rate"],
    )
    assert path.exists()
    assert path.name == "q00001.md"

    post = frontmatter.load(str(path))
    assert post.metadata["status"] == "success"
    assert post.metadata["accepted"] is False
    assert "[[orders.revenue]]" in post.metadata["objects_in_data_model"]


def test_sequential_numbering(queries_dir: Path):
    qm = QueryMemory(queries_dir)
    p1 = qm.write("Q1", "SELECT 1", "1 row")
    p2 = qm.write("Q2", "SELECT 2", "1 row")
    assert p1.name == "q00001.md"
    assert p2.name == "q00002.md"


def test_rotate_removes_oldest(queries_dir: Path):
    qm = QueryMemory(queries_dir, max_files=3)
    for i in range(5):
        qm.write(f"Q{i}", f"SELECT {i}", f"{i} rows")

    files = sorted(queries_dir.glob("q*.md"))
    assert len(files) == 3
    # Oldest should be gone
    assert not (queries_dir / "q00001.md").exists()
    assert not (queries_dir / "q00002.md").exists()


def test_accepted_never_rotated(queries_dir: Path):
    qm = QueryMemory(queries_dir, max_files=3)
    # Write an accepted query first
    qm.write("Accepted", "SELECT 1", "good", accepted=True)
    # Write 4 more non-accepted
    for i in range(4):
        qm.write(f"Q{i}", f"SELECT {i}", f"{i} rows")

    files = sorted(queries_dir.glob("q*.md"))
    # Should have accepted + 2 newest non-accepted = 3
    assert len(files) == 3
    # The accepted one should still exist
    assert (queries_dir / "q00001.md").exists()
    post = frontmatter.load(str(queries_dir / "q00001.md"))
    assert post.metadata["accepted"] is True


def test_list_queries(queries_dir: Path):
    qm = QueryMemory(queries_dir)
    qm.write("Q1", "SELECT 1", "1 row")
    qm.write("Q2", "SELECT 2", "1 row", accepted=True)
    qm.write("Q3", "SELECT 3", "1 row")

    all_queries = qm.list_queries()
    assert len(all_queries) == 3

    accepted = qm.list_queries(accepted_only=True)
    assert len(accepted) == 1
    assert accepted[0].name == "q00002.md"
