# Filing Types Reference

## Primary Filing Types (Always Search All 6)

| Type | Description |
|------|-------------|
| DEFM14A | Definitive proxy statement for mergers. Target-side. Usually has the most complete "Background of the Merger" narrative. |
| PREM14A | Preliminary proxy statement for mergers. Target-side. Viable primary when DEFM14A has not yet been filed. |
| SC 14D-9 | Solicitation/recommendation statement. Target-side response to a tender offer. Contains "Background of the Offer" narrative. |
| SC 13E-3 | Going-private transaction statement. Filed by issuer or affiliate. Contains background narrative for freeze-out mergers. |
| S-4 | Registration statement for stock-for-stock mergers. Acquirer-side. Contains background narrative when stock is part of consideration. |
| SC TO-T | Tender offer statement. Bidder-side. Contains "Background of the Offer" from the acquirer's perspective. |

## Supplementary Filing Types (Also Search)

| Type | Description |
|------|-------------|
| SC 13D | Beneficial ownership report. Filed by activists or large shareholders. Provides pre-deal context (activist pressure, initial stake building). |
| DEFA14A | Additional definitive proxy soliciting materials. Often contains updated or supplemental deal information. |
| 8-K | Current report. Filed for material events: merger announcement, execution date, completion, termination. Useful for execution dates and press releases. |

## Filing Preference Ranking

Select the filing with the most complete "Background of the Merger/Offer"
section as primary. The ranking below reflects typical completeness, but
the agent must check all 6 types and select on content quality.

```
Primary preference (fuller auction narrative):
  DEFM14A > PREM14A > SC 14D-9 > SC 13E-3

Also viable as primary:
  SC TO-T, S-4

Rule: Pick whichever filing has the most complete
"Background of the Merger/Offer" section, regardless
of which side filed it. Target-side usually wins,
but the agent checks all 6 and selects on content quality.
```

## Filing Disposition Values

| Disposition | Meaning |
|-------------|---------|
| `selected` | This filing was chosen as primary or supplementary. Will be fetched by Skill 2. |
| `searched_not_used` | Filing found but not needed. Include reason (e.g., "DEFM14A selected; shorter background"). |
| `not_applicable` | Filing type does not apply to this deal structure. Include reason (e.g., "all-cash deal; no S-4 needed"). |
| `not_found` | No filings of this type found for this CIK. |
| `uncertain` | Filing found but unclear if useful. Logged for manual review. |
