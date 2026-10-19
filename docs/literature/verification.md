# Literature verification log

Project: Maharashtra soybean yield vs rainfall and temperature (Group 28)
Date checked: 19 October 2026
Scope: every reference used in the report. Source list: `docs/literature/teammate_report.docx`.

## How the checks were done
1. Each DOI was matched to the publisher, journal or repository record (title, authors, journal, volume, issue, pages, year).
2. The abstract (for Patil & Shende, the full PDF) was read and compared with the one-line claim made in the report.
3. Two independent web lookups were made. Where they disagreed, the journal's own page decided.
4. Rule: the report cites only papers listed as verified below, and makes no claim stronger than the "Claim permitted" line.

Limitations of this verification (stated honestly):
- The checks were made by web lookup of publisher and repository records. The team did not click through each DOI link manually.
- Goswami et al. (2006): the publisher page blocked automated access, so the record and abstract were cross-checked through PubMed instead.
- Schlenker & Roberts (2009): the issue number (37) was confirmed by the second lookup only.

## Summary of verified references

| # | Reference | Status |
|---|---|---|
| 0 | Lobell, Schlenker & Costa-Roberts (2011) | VERIFIED (PDF in hand) |
| 1 | Schlenker & Roberts (2009) | VERIFIED |
| 2 | Lobell & Field (2007) | VERIFIED |
| 3 | Auffhammer, Ramanathan & Vincent (2012) | VERIFIED |
| 4 | Goswami et al. (2006) | VERIFIED (via PubMed cross-check) |
| 5 | Pai et al. (2014) | VERIFIED |
| 6 | Muñoz-Sabater et al. (2021) | VERIFIED |
| 7 | Patil & Shende (2022) | VERIFIED, cite with caveats (weak evidence) |
| 8 | Maiti et al. (2026) | VERIFIED (cite as "Maiti et al.") |
| 8b | Maiti et al. (2024) | VERIFIED (rice only) |

## Excluded from the report (could not be verified)
- Wooldridge (2010), *Econometric Analysis of Cross Section and Panel Data*: a textbook with no DOI; edition and publisher were not checked. Not cited in the report. Panel-data methods are described with reference to the verified papers above and the software documentation instead.
- Any other source in `docs/literature/teammate_report.docx` that does not appear in the table above was not checked and is not cited.

## Details and claims permitted in the report

### 0. Lobell, D. B., Schlenker, W., & Costa-Roberts, J. (2011)
- Science, 333(6042), 616-620. https://doi.org/10.1126/science.1204531
- Source: PDF in `docs/literature/`.
- Claim permitted: panel regressions of yield on growing-season temperature and precipitation, their squares, country intercepts and country-specific time trends; bootstrap confidence intervals; results treated as a measure of the pace of climate change, not as predictions that include adaptation.

### 1. Schlenker, W., & Roberts, M. J. (2009)
- Proceedings of the National Academy of Sciences, 106(37), 15594-15598. https://doi.org/10.1073/pnas.0906865106
- Abstract confirms: county-level US yields for corn, soybean and cotton; yields rise with temperature up to about 29 C (corn), 30 C (soybean) and 32 C (cotton), and are very harmful above these thresholds.
- Claim permitted: nonlinear temperature effects with harmful high-temperature exposure; used here only to motivate a squared temperature term.

### 2. Lobell, D. B., & Field, C. B. (2007)
- Environmental Research Letters, 2(1), 014002. https://doi.org/10.1088/1748-9326/2/1/014002
- Abstract confirms: growing-season temperature and precipitation explain roughly 30% or more of year-to-year variation in global average yields of the six most widely grown crops.
- Claim permitted: as above, no stronger.

### 3. Auffhammer, M., Ramanathan, V., & Vincent, J. R. (2012)
- Climatic Change, 111(2), 411-424. https://doi.org/10.1007/s10584-011-0208-4
- Abstract confirms: state-level Indian data, 1966-2002; drought and extreme rainfall reduced rice yield in predominantly rainfed areas, drought more than extreme rainfall.
- Claim permitted: monsoon variability and rice yield in India (rice, state level, not soybean).

### 4. Goswami, B. N., Venugopal, V., Sengupta, D., Madhusoodanan, M. S., & Xavier, P. K. (2006)
- Science, 314(5804), 1442-1445. https://doi.org/10.1126/science.1132027
- Abstract confirms: rising frequency and magnitude of extreme rain events and falling moderate events over central India in monsoon seasons 1951-2000; no significant trend in seasonal mean rainfall.
- Claim permitted: seasonal totals can hide changes within the season (context for why rainfall timing matters).

### 5. Pai, D. S., Rajeevan, M., Sreejith, O. P., Mukhopadhyay, B., & Satbha, N. S. (2014)
- MAUSAM, 65(1), 1-18. https://doi.org/10.54302/mausam.v65i1.851
- Confirms: IMD daily gridded rainfall at 0.25 x 0.25 degrees, 1901-2010, built from 6,955 rain gauges.
- Authors: taken from the journal's own page. Some third-party citations list an extra author (L. Sridhar) and spell the last name "Satbhai"; use the journal page's list.
- Claim permitted: data-source citation for the IMD gridded rainfall product. Our download covers 2000-2017 of the IMD gridded data; the paper documents the 1901-2010 product.

### 6. Muñoz-Sabater, J., Dutra, E., Agusti-Panareda, A., et al. (2021)
- Earth System Science Data, 13(9), 4349-4383. https://doi.org/10.5194/essd-13-4349-2021
- Title: "ERA5-Land: a state-of-the-art global reanalysis dataset for land applications". Published 7 September 2021.
- Claim permitted: citation for the ERA5-Land product. Note: the single-point ERA5-Land file supplied with the project was rejected (one Konkan-coast grid point) and is not used in the model.

### 7. Patil, A., & Shende, N. (2022)
- Journal of Food Legumes, 35(4), 267-273. https://doi.org/10.59797/journaloffoodlegumes.v35i4.315
- Year: the PDF prints 35(4), 2022; the journal's web page shows a 2024 upload date. Use 2022 consistently.
- Data period: the abstract says 1901-2020, but the methods section states the analysis uses 30 years, 1991-2020. Cite 1991-2020 as the analysed period.
- Evidence strength: one district (Akola); R-squared 0.33 but the overall regression is not significant (p = 0.30; adjusted R-squared 0.074); no individual climatic variable significant; the only significant link is a simple correlation of productivity with rainfall (about 0.43, n = 30). The text also refers to cotton in places despite the soybean table heading.
- Claim permitted: weak, single-district descriptive evidence that soybean productivity in Akola is positively correlated with rainfall. Do not present the 33% as significant explained variation.

### 8. Maiti, A., et al. (2026)
- Earth's Future, 14(6), e2025EF007801. https://doi.org/10.1029/2025EF007801
- Title: "Excess Rainfall Threatens Monsoon Crop Yield Stability Under Climate Change". First published June 2026.
- Confirms: district-level Indian yield data, 1990-2017, for eight Kharif crops including cotton and soybean; beyond an optimal rainfall threshold, yield falls by 0.20% (cotton) and 0.11% (soybean) per 1% (about 17 mm) increase in seasonal rainfall; excess-rainfall losses are comparable to those from equivalent deficits; rainfall intensity on rainy days matters more than the frequency of rainy days.
- Author list: only "Maiti et al." was confirmed; the full list was not captured, so the report cites it as "Maiti et al." and the reference entry uses "et al.".
- Claim permitted: qualitative support for a concave rainfall response, with losses on both sides of an optimum. Do NOT compare their numbers with ours: theirs are measured beyond a threshold per 1% of seasonal rainfall; ours are a 100 mm deficit from each district's mean.

### 8b. Maiti, A., Hasan, M. K., Sannigrahi, S., Bar, S., Chakraborti, S., Mahto, S. S., Chatterjee, S., Pramanik, S., Pilla, F., Auerbach, J., Sonnentag, O., Song, C., & Zhang, Q. (2024)
- Communications Earth & Environment, 5, article 302. https://doi.org/10.1038/s43247-024-01414-7
- Title: "Optimal rainfall threshold for monsoon rice production in India varies across space and time".
- Confirms: rice, 1990-2017; excessive rainfall reduces rice yield by 33.7% and deficit by 19%; national optimum threshold 1621 +/- 34 mm.
- Claim permitted: rice-specific evidence of a nonlinear rainfall optimum. It is not soybean evidence.

## Corrections applied in the reference list
1. Patil & Shende: year 2022; DOI link without any tracking parameter.
2. Pai et al.: five-author list from the journal page.
3. Maiti 2026: cited as "Maiti et al."
4. Wooldridge: removed (not verified).
5. Apply the professor's citation style to the final list when known (not yet received).
