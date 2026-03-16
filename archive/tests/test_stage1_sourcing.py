import unittest

import requests

from pipeline.schemas import DocumentSelection, SourceSelection
from pipeline.stage1_sourcing import (
    USER_AGENT,
    _choose_document_from_index,
    _ensure_session_headers,
    _evaluate_chronology_lines,
    _infer_selected_document_url,
)


class EnsureSessionHeadersTests(unittest.TestCase):
    def test_overrides_default_requests_user_agent(self) -> None:
        session = requests.Session()

        self.assertNotEqual(session.headers.get("User-Agent"), USER_AGENT)

        _ensure_session_headers(session)

        self.assertEqual(session.headers.get("User-Agent"), USER_AGENT)


class ChronologyHeadingDetectionTests(unittest.TestCase):
    def test_accepts_background_of_offer_and_merger_heading(self) -> None:
        lines = ["Cover page", "Background of Offer and Merger"]
        for month, day in (("May", 1), ("May", 10), ("June", 1), ("June", 20)):
            lines.extend(
                [
                    f"On {month} {day}, 2016, Party A contacted the Company regarding a possible transaction.",
                    "The board of directors discussed the proposal with Company management and advisors.",
                    "Party A and the Company continued discussions regarding a strategic transaction.",
                    "",
                ]
            )
        lines.extend(
            [
                "On July 5, 2016, Party B submitted a revised indication of interest to the Company.",
                "The Company board met with its advisors to review Party B's proposal.",
                "Opinion of Financial Advisor",
            ]
        )

        evaluation = _evaluate_chronology_lines(lines, "0000000000-00-000001")

        self.assertEqual(evaluation.heading_text, "Background of Offer and Merger")
        self.assertEqual(evaluation.start_line, 2)


class DocumentSelectionTests(unittest.TestCase):
    def test_resolves_relative_document_href_within_accession_directory(self) -> None:
        index_url = "https://www.sec.gov/Archives/edgar/data/1011835/0001193125-16-696911-index.htm"
        html = b"""
        <html>
          <body>
            <table>
              <tr>
                <th>Seq</th>
                <th>Description</th>
                <th>Document</th>
                <th>Type</th>
                <th>Size</th>
              </tr>
              <tr>
                <td>1</td>
                <td>SC 14D9</td>
                <td><a href="d234696dsc14d9.htm">d234696dsc14d9.htm</a></td>
                <td>SC 14D9</td>
                <td>607136</td>
              </tr>
            </table>
          </body>
        </html>
        """

        _selection, selected_url = _choose_document_from_index(index_url, html, "SC 14D-9")

        self.assertEqual(
            selected_url,
            "https://www.sec.gov/Archives/edgar/data/1011835/000119312516696911/d234696dsc14d9.htm",
        )

    def test_infers_selected_document_url_from_source_selection_index_page(self) -> None:
        selection = SourceSelection(
            deal_slug="medivation",
            cik="1011835",
            target_name="Medivation, Inc.",
            primary_searches=[],
            supplementary_searches=[],
            document_selection=DocumentSelection(
                index_url="https://www.sec.gov/Archives/edgar/data/1011835/0001193125-16-696911-index.htm",
                documents_listed=[],
                selected_document="d234696dsc14d9.htm",
                selection_rationale="test",
            ),
        )

        selected_url = _infer_selected_document_url(selection)

        self.assertEqual(
            selected_url,
            "https://www.sec.gov/Archives/edgar/data/1011835/000119312516696911/d234696dsc14d9.htm",
        )


if __name__ == "__main__":
    unittest.main()
