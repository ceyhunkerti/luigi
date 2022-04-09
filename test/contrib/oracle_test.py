import datetime

import luigi.contrib.oracle
import mock
import pytest
from helpers import unittest
from luigi.tools.range import RangeDaily


def datetime_to_epoch(dt):
    td = dt - datetime.datetime(1970, 1, 1)
    return td.days * 86400 + td.seconds + td.microseconds / 1e6


class MockOracleCursor(mock.Mock):
    """
    Keeps state to simulate executing SELECT queries and fetching results.
    """

    def __init__(self, existing_update_ids):
        super(MockOracleCursor, self).__init__()
        self.existing = existing_update_ids

    def execute(self, query, params):
        if query.startswith("SELECT 1 FROM table_updates"):
            self.fetchone_result = (1,) if params[0] in self.existing else None
        else:
            self.fetchone_result = None

    def fetchone(self):
        return self.fetchone_result


class DummyOracleImporter(luigi.contrib.oracle.CopyToTable):
    date = luigi.DateParameter()

    host = "dummy_host"
    port = 1521
    database = "dummy_database"
    user = "dummy_user"
    password = "dummy_password"
    table = "dummy_table"
    columns = (
        ("some_text", "text"),
        ("some_int", "int"),
    )


# Testing that an existing update will not be run in RangeDaily
@pytest.mark.oracle
class DailyCopyToTableTest(unittest.TestCase):
    @mock.patch("cx_Oracle.connect")
    def test_bulk_complete(self, mock_connect):
        mock_cursor = MockOracleCursor(
            [  # Existing update_ids
                DummyOracleImporter(date=datetime.datetime(2015, 1, 3)).task_id
            ]
        )
        mock_connect.return_value.cursor.return_value = mock_cursor

        task = RangeDaily(
            of=DummyOracleImporter,
            start=datetime.date(2015, 1, 2),
            now=datetime_to_epoch(datetime.datetime(2015, 1, 7)),
        )
        actual = sorted([t.task_id for t in task.requires()])

        self.assertEqual(
            actual,
            sorted(
                [
                    DummyOracleImporter(date=datetime.datetime(2015, 1, 2)).task_id,
                    DummyOracleImporter(date=datetime.datetime(2015, 1, 4)).task_id,
                    DummyOracleImporter(date=datetime.datetime(2015, 1, 5)).task_id,
                    DummyOracleImporter(date=datetime.datetime(2015, 1, 6)).task_id,
                ]
            ),
        )
        self.assertFalse(task.complete())


@pytest.mark.oracle
class TestCopyToTableWithMetaColumns(unittest.TestCase):
    @mock.patch(
        "luigi.contrib.oracle.CopyToTable.enable_metadata_columns",
        new_callable=mock.PropertyMock,
        return_value=True,
    )
    @mock.patch("luigi.contrib.oracle.CopyToTable._add_metadata_columns")
    @mock.patch("luigi.contrib.oracle.CopyToTable.post_copy_metacolumns")
    @mock.patch("luigi.contrib.oracle.CopyToTable.rows", return_value=["row1", "row2"])
    @mock.patch("luigi.contrib.oracle.OracleTarget")
    @mock.patch("cx_Oracle.connect")
    def test_copy_with_metadata_columns_enabled(
        self,
        mock_connect,
        mock_oracle_target,
        mock_rows,
        mock_add_columns,
        mock_update_columns,
        mock_metadata_columns_enabled,
    ):

        task = DummyOracleImporter(date=datetime.datetime(1991, 3, 24))

        mock_cursor = MockOracleCursor([task.task_id])
        mock_connect.return_value.cursor.return_value = mock_cursor

        task = DummyOracleImporter(date=datetime.datetime(1991, 3, 24))
        task.run()

        self.assertTrue(mock_add_columns.called)
        self.assertTrue(mock_update_columns.called)

    @mock.patch(
        "luigi.contrib.oracle.CopyToTable.enable_metadata_columns",
        new_callable=mock.PropertyMock,
        return_value=False,
    )
    @mock.patch("luigi.contrib.oracle.CopyToTable._add_metadata_columns")
    @mock.patch("luigi.contrib.oracle.CopyToTable.post_copy_metacolumns")
    @mock.patch("luigi.contrib.oracle.CopyToTable.rows", return_value=["row1", "row2"])
    @mock.patch("luigi.contrib.oracle.ORacleTarget")
    @mock.patch("cx_Oracle.connect")
    def test_copy_with_metadata_columns_disabled(
        self,
        mock_connect,
        mock_oracle_target,
        mock_rows,
        mock_add_columns,
        mock_update_columns,
        mock_metadata_columns_enabled,
    ):

        task = DummyOracleImporter(date=datetime.datetime(1991, 3, 24))

        mock_cursor = MockOracleCursor([task.task_id])
        mock_connect.return_value.cursor.return_value = mock_cursor

        task.run()

        self.assertFalse(mock_add_columns.called)
        self.assertFalse(mock_update_columns.called)