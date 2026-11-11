"""Notes to TAP's 2025 consolidated accounts, copied as printed.

Writes data/notes/TAP_2025_notes.xlsx: one sheet per table of the notes that a
due diligence reader opens first (other income, other expenses, borrowings,
maturities, leases, provisions, contingencies, related parties, segments, staff).

Source: Transportes Aéreos Portugueses, S.A., 2025 Integrated Report (English
translation), notes to the consolidated financial statements. Every number is
the one printed on the page given in the sheet; nothing is computed. The sums
at the end only check the copying against the totals the note prints.

The note tables print no unit of their own; the consolidated statements
(p.152 onwards) print "Amounts stated in euros".

Unlabelled total lines are written as "[Total]" (the report prints the figure
under a rule, with no label).

Run:  python scripts\\notes_tap_2025.py
"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

OUT = Path(__file__).resolve().parents[1] / "data" / "notes" / "TAP_2025_notes.xlsx"
REPORT = "2025 Integrated Report"
UNIT = "Amounts stated in euros"
N19 = "19. Borrowings and Lease liabilities with and without purchase option"

# Each row is "label | value | value ..." exactly as printed: (1,234) is negative,
# "-" is a printed dash. A row with no " | " is a caption or a sentence of the note.
SHEETS = [
    dict(
        sheet="N25 Other income", topic="other_income", note="25",
        title="25. Other income", page="p.212",
        header=["2025", "2024"],
        rows="""
Catering | 16,874,150 | -
Services provided | 7,450,219 | 10,160,333
Heathcare | 4,063,851 | -
Sales | 2,026,697 | 1,053,736
Rents and Subleases | 1,604,607 | 2,742,872
Operating government grants | 1,127,756 | 487,614
Gains from tangible fixed assets (Notes 4 and 5) | 718,030 | 482,884
Publicity | 586,438 | 345,488
Other supplementary income | 8,090,424 | 9,531,051
[Total] | 42,542,172 | 24,803,978
""",
        sums=[(9, range(0, 9))],
    ),
    dict(
        sheet="N29 Other expenses", topic="other_expenses", note="29",
        title="29. Other expenses", page="p.215",
        header=["2025", "2024"],
        rows="""
Specialised work and subcontracts | 95,437,554 | 81,139,844
Rents | 44,450,374 | 21,853,898
Conservation and repair of other assets | 11,932,581 | 13,609,418
Transportation | 9,884,970 | 5,522,236
Insurance | 8,702,584 | 11,222,606
Comunication | 7,087,584 | 7,921,356
Cleaning, hygiene and comfort | 5,203,709 | 1,922,236
Travel costs | 3,217,531 | 2,220,773
Electricity | 3,083,937 | 2,546,769
Surveillance and security | 2,829,869 | 2,590,956
Losses in inventories | 2,821,768 | 733,049
Taxes | 2,682,694 | 2,825,321
Losses in fixed assets | 2,065,914 | 2,454,218
Fees | 1,596,664 | 31,159
Books and technical documentation | 1,463,232 | 1,310,618
Licenses and fees | 1,110,109 | 857,614
Other operating expenses | 8,194,944 | 2,548,228
[Total] | 211,766,018 | 161,310,299
The increase in the other expenses caption is mainly attributable to the inclusion of Portugália, UCS and Cateringpor in the Group’s consolidation perimeter (Note 2.4).
In the year ended 31 December 2025, the rents caption includes short-term lease contracts relating to engines, properties and software amounting to EUR 21.4 million, EUR 5.8 million and EUR 14.3 million, respectively (EUR 6.6 million, EUR 4.5 million and EUR 8.8 million, respectively, in the year ended 31 December 2024).
""",
        sums=[(17, range(0, 17))],
    ),
    dict(
        sheet="N30 Restructuring", topic="other_expenses", note="30",
        title="30. Restructuring", page="p.216",
        header=["2025", "2024"],
        rows="""
Restructuring provision (Note 18) | - | 1,176,003
Employee indemnities | (307,170) | (241,006)
[Total] | (307,170) | 934,997
""",
        sums=[(2, range(0, 2))],
    ),
    dict(
        sheet="N31 Other non-recurring", topic="other_expenses", note="31",
        title="31. Other non-recurring items", page="p.216",
        header=["2025", "2024"],
        rows="""
TAP Group corporate restructuring | 36,888,012 | 49,403,518
Annulation of pre-existing relationships Portugália – ACMI contracts | - | (20,704,253)
Labor contingencies | (9,466,779) | 40,600,000
Other non-recurring costs | 1,306,000 | -
Other non-recurring gains | (11,912,903) | (107,288)
[Total] | 16,814,330 | 69,191,977
During the year ended 31 December 2025, the Board of Directors increased the impairment losses recognised on receivables from SIAVILO by EUR 29.2 million (Note 10), mainly relating to interest income accrued and the corresponding stamp duty recognised in the year ended 31 December 2025 (Note 33).
TAP S.A. granted TAP ME Brazil a loan amounting to EUR 3.0 million, on which a full impairment was recognised due to the low expectation of recovery (Note 10). In addition, considering that TAP ME Brazil remains subject to other contingencies until its liquidation, the Group recognised, in December 2025, a provision amounting to EUR 4.7 million corresponding to the estimated remaining obligations (Note 18).
In view of the above, in the year ended 31 December 2024 a provision amounting to EUR 40.6 million was recognised under other non recurring items (Note 18), considered non usual, relating to potential legal proceedings of a similar nature associated with the aforementioned judgment. In the year ended 31 December 2025, this provision was reassessed, reflecting an updated evaluation of the contingency.
In the year ended 31 December 2025, the Group incurred in expenses related to work performed in connection with the ongoing privatization process, amounting to EUR 1.3 million, which were recognised under other non-recurring costs.
In the year ended 31 December 2025, the Group reversed a provision amounting to EUR 11.9 million, which had previously been recognised in connection with contingencies associated with a cyberattack that occurred in 2022 (Note 18).
""",
        sums=[(5, range(0, 5))],
    ),
    dict(
        sheet="N19a Borrowings", topic="borrowings", note="19",
        title=N19, page="pp.205–206",
        header=["Current 2025", "Non-Current 2025", "Current 2024", "Non-Current 2024"],
        rows="""
Bank loans | 10,976,972 | 44,171,717 | 11,148,090 | 55,319,807
Interest accrued | 273,711 | - | 599,900 | -
Initial expenses | (90,742) | (75,208) | (157,688) | (167,174)
Remunerated bank debt | 11,159,941 | 44,096,509 | 11,590,302 | 55,152,633
Bonds | 3,363,532 | 663,069,851 | 5,360,003 | 466,331,743
Interest accrured | 6,300,896 | - | 4,853,466 | -
Initial expenses | (833,573) | (4,611,952) | (1,795,998) | (8,438,662)
Bond issuance | 8,830,855 | 658,457,899 | 8,417,471 | 457,893,081
Total borrowings | 19,990,796 | 702,554,408 | 20,007,773 | 513,045,714
Lease liabilities with purchase option | 114,362,662 | 743,068,555 | 104,808,614 | 761,544,313
Interest accrued | 2,915,166 | - | 3,586,774 | -
Initial expenses | (175,807) | (528,883) | (269,891) | (743,297)
Lease liabilities with purchase option | 117,102,021 | 742,539,672 | 108,125,497 | 760,801,016
Lease liabilities without purchase option | 265,084,936 | 1,033,575,276 | 303,795,617 | 1,295,428,780
Total borrowings and lease liabilities | 402,177,753 | 2,478,669,356 | 431,928,887 | 2,569,275,510
As of 31 December 2025, the bank loans heading includes two loans with a national credit institution, totalling EUR 53.8 million.
This heading also includes a loan obtained from a U.S. financial institution in the total amount of EUR 1.3 million.
TAP S.A. carried out a bond issue through a private placement, fully subscribed on 14 January 2019, in the amount of EUR 137.2 million and maturing in 2034.
As of 31 December 2025, the outstanding principal of this loan amounted to EUR 66.4 million.
On 7 November 2024, TAP S.A. issued a five-year bond offering, with a fixed annual interest rate of 5.125%, amounting to EUR 400 million, denominated “TAP 2024–2029 Bonds”, targeted at European and American institutional investors. On 7 March 2025, TAP S.A. issued additional bonds under the same issuance agreement governing the “TAP 2024–2029 Bonds”, in the amount of EUR 200 million, maturing on the same date, at a final issue price of 102.75% and, therefore, with an implied yield to maturity of 4.467% for this additional amount. The total amount of the bond issuance therefore reached EUR 600 million.
As of 31 December 2025 and 2024, all the bond loans are denominated in EUR.
""",
        sums=[(3, range(0, 3)), (7, range(4, 7)), (8, [3, 7]), (12, range(9, 12)),
              (14, [8, 12, 13])],
    ),
    dict(
        sheet="N19b Net debt", topic="borrowings", note="19",
        title=N19 + " — Net debt", page="p.206",
        header=["2025", "2024"],
        rows="""
Borrowings except lease liabilities without purchase option
Non-Current | 1,445,094,080 | 1,273,846,730
Current | 137,092,817 | 128,133,270
[Total] | 1,582,186,897 | 1,401,980,000
Cash and Cash Equivalents (Note 14)
Cash | 60,218 | 70,763
Bank deposits available on demand | 124,082,366 | 134,726,289
Other deposits | 641,186,776 | 516,845,478
[Total] | 765,329,360 | 651,642,530
Net debt | 816,857,537 | 750,337,470
""",
        sums=[(3, [1, 2]), (8, [5, 6, 7]), (9, [3, (8, -1)])],
    ),
    dict(
        sheet="N19c Debt maturity", topic="borrowings_maturity", note="19",
        title=N19 + " — interest-bearing debt and leasing liabilities with a purchase "
                    "option, by maturity and by type of interest rate",
        page="pp.206–207",
        header=["2025", "2024"],
        rows="""
Variable rate
Up to 1 year | 73,931,396 | 57,808,957
1 to 2 years | 46,224,605 | 65,764,734
2 to 3 years | 46,761,577 | 40,057,171
Over 3 years | 318,904,232 | 290,272,305
[Total] | 485,821,810 | 453,903,167
Fixed rate
Up to 1 year | 63,161,421 | 70,324,313
1 to 2 years | 50,850,465 | 58,200,984
2 to 3 years | 64,769,345 | 52,760,972
Over 3 years | 917,583,856 | 766,790,564
[Total] | 1,096,365,087 | 948,076,833
[Total] | 1,582,186,897 | 1,401,980,000
Financial Covenants
The financial covenants in the lease and financing contracts are typical for operations of this nature, including provisions such as the obligation to maintain activity as an air operator, commitments to provide periodic financial information, as well as, in the specific case of leases without purchase option, operational obligations related to records in official entities, information regarding leased aircraft, strict compliance with all regulations, procedures defined by authorities, among others.
Additionally, commitments were made to monitor the Group's financial performance through the analysis and compliance with certain ratios related to the Group's consolidated financial statements, namely Net Debt/EBITDAR and a minimum amount of unrestricted cash and cash equivalents.
As of 31 December 2025, there is no breach of covenants with reference to the financial statements as of that date.
""",
        sums=[(5, range(1, 5)), (11, range(7, 11)), (12, [5, 11])],
    ),
    dict(
        sheet="N3a Liquidity 2025", topic="borrowings_maturity", note="3",
        title="3. Financial risk management policies — Liquidity risk — 2025", page="p.178",
        header=["< 1 ano", "1 - 2 anos", "3 - 5 anos", "6 - 10 anos", "> 10 anos", "Total"],
        rows="""
Other payables | 727,646,558 | 4,683,006 | - | - | - | 732,329,564
Borrowings | 52,881,895 | 51,184,607 | 697,872,938 | 60,072,516 | - | 862,011,956
Lease liabilities with purchase option | 155,059,749 | 120,436,375 | 394,461,459 | 357,725,423 | 18,448,751 | 1,046,131,757
Lease liabilities without purchase option | 286,934,862 | 274,965,294 | 904,161,819 | 185,479,680 | - | 1,651,541,655
Total | 1,222,523,064 | 451,269,282 | 1,996,496,216 | 603,277,619 | 18,448,751 | 4,292,014,932
In the table below, covering capital and interest, theoretical assumptions were made for market interest rates and EUR/USD exchange rates. The liabilities are the amounts payable within the specified time limits, including the estimate of all contractual cash flows with amortisation and undiscounted interest, until the end of the life of the loans.
""",
        sums=[(4, range(0, 4))], rowsums=[(5, range(0, 5))],
    ),
    dict(
        sheet="N3b Liquidity 2024", topic="borrowings_maturity", note="3",
        title="3. Financial risk management policies — Liquidity risk — 2024 Restated",
        page="p.178",
        header=["< 1 ano", "1 - 2 anos", "3 - 5 anos", "6 - 10 anos", "> 10 anos", "Total"],
        rows="""
Other payables | 680,369,532 | - | 2,008,837 | - | - | 682,378,369
Borrowings | 44,490,269 | 41,782,755 | 505,895,060 | 75,001,598 | - | 667,169,682
Lease liabilities with purchase option | 148,403,489 | 149,336,040 | 395,635,034 | 343,993,908 | 35,088,765 | 1,072,457,236
Lease liabilities without purchase option | 328,163,872 | 308,997,811 | 1,078,507,990 | 390,688,843 | - | 2,106,358,516
Total | 1,201,427,162 | 500,116,606 | 1,982,046,921 | 809,684,349 | 35,088,765 | 4,528,363,803
""",
        sums=[(4, range(0, 4))], rowsums=[(5, range(0, 5))],
    ),
    dict(
        sheet="N19d Leases with option", topic="leases", note="19",
        title=N19 + " — lease liabilities with purchase option, by maturity", page="p.207",
        header=["2025", "2024"],
        rows="""
Up to 1 year | 117,102,020 | 108,125,497
1 to 2 years | 84,734,810 | 111,312,760
2 to 3 years | 99,428,072 | 81,289,027
3 to 4 years | 135,157,493 | 97,469,144
4 to 5 years | 86,274,514 | 134,727,106
More than 5 years | 336,944,784 | 336,002,979
[Total] | 859,641,693 | 868,926,513
As of 31 December 2025 and 2024, leasing liabilities with option to purchase (plus interest expense minus initial charges) essentially relate to aircraft and engines.
""",
        sums=[(6, range(0, 6))],
    ),
    dict(
        sheet="N19e Leases without option", topic="leases", note="19",
        title=N19 + " — lease liabilities without purchase option per maturity", page="p.207",
        header=["2025", "2024"],
        rows="""
Up to 1 year | 265,084,936 | 303,795,617
1 to 2 years | 247,750,618 | 277,201,947
2 to 3 years | 221,388,784 | 239,278,641
3 to 4 years | 188,959,369 | 214,274,686
4 to 5 years | 160,326,385 | 188,102,939
More than 5 years | 215,150,120 | 376,570,567
[Total] | 1,298,660,212 | 1,599,224,397
The Lease liabilities without purchase option item refers essentially to the Company’s non-cancellable payments under lease contracts, which vary in duration up to 14 years and may be extended at the express wish of the contracting parties, which are recognised in the statement of financial position.
As of 31 December 2025, there were 76 aircraft, of which 2 were not in an airworthy condition (Note 4), and 7 engines under lease agreements without purchase option.
Lease liabilities without purchase option regarding aircraft and engines are denominated in USD, while the remaining lease liabilities are denominated in EUR.
""",
        sums=[(6, range(0, 6))],
    ),
    dict(
        sheet="N19f Leases by currency", topic="leases", note="19",
        title=N19 + " — leases with purchase option, by currency", page="p.206",
        header=["2025", "2024"],
        rows="""
Lease liabilities in EUR | 508,646,327 | 431,176,023
Lease liabilities in USD | 339,330,080 | 437,750,490
Lease liabilities in JPY | 11,665,286 | -
[Total] | 859,641,693 | 868,926,513
""",
        sums=[(3, range(0, 3))],
    ),
    dict(
        sheet="N19g Financing cash flows", topic="leases", note="19",
        title=N19 + " — Reconciliation of finance cash flows", page="pp.207–208",
        header=["Remunerated bank debt and bonds", "Leases with purchase option",
                "Leases without purchase option", "Total"],
        rows="""
1 January 2024 | 650,488,469 | 789,958,352 | 1,801,118,407 | 3,241,565,228
Receipts | 400,000,000 | - | - | 400,000,000
Payments | (554,121,524) | (138,004,580) | (430,946,569) | (1,123,072,673)
New lease agreements / renegotiations | - | 143,881,905 | 98,554,047 | 242,435,952
Change in consolidation perimeter | - | - | (106,191,440) | (106,191,440)
Exchange variation | 178,753 | 27,243,768 | 97,103,298 | 124,525,819
Interest cost (Note 33) | 32,457,594 | 45,838,612 | 136,932,552 | 215,228,758
Other | 4,050,195 | 8,456 | 2,654,102 | 6,712,753
31 December 2024 | 533,053,487 | 868,926,513 | 1,599,224,397 | 3,001,204,397
Receipts | 200,000,000 | - | - | 200,000,000
Payments | (44,710,689) | (152,176,161) | (311,641,797) | (508,528,647)
New lease agreements / renegotiations | - | 144,677,880 | 67,279,766 | 211,957,646
Change in consolidation perimeter | - | 429,562 | 14,028,294 | 14,457,856
Transfers (Note 7) | - | (278,496) | (6,680,731) | (6,959,227)
Exchange variation | (221,886) | (49,349,499) | (176,384,486) | (225,955,871)
Interest cost (Note 33) | 23,799,367 | 43,495,372 | 110,230,920 | 177,525,659
Other | 10,624,925 | 3,916,522 | 2,603,849 | 17,145,296
31 December 2025 | 722,545,204 | 859,641,693 | 1,298,660,212 | 2,880,847,109
The amounts considered as other refer essentially to the impact of the recognition of the effective interest rate.
""",
        sums=[(8, range(0, 8)), (17, range(8, 17))], rowsums=[(3, range(0, 3))],
    ),
    dict(
        sheet="N18 Provisions", topic="provisions", note="18",
        title="18. Provisions", page="pp.204–205",
        header=["Provision for legal claims (Notes 28 and 31)", "Other (Notes 28 and 31)",
                "Redelivery costs (Notes 4 and 28)", "Sub-total Provisions",
                "Restructuring provision (Note 30)", "Total"],
        rows="""
1 January 2024 | 61,828,866 | 43,720,293 | 199,685,619 | 305,234,778 | 2,108,784 | 307,343,562
Changes in consolidation perimeter | - | - | 101,154,322 | 101,154,322 | - | 101,154,322
Increases | 8,972,180 | 70,272,409 | 49,943,190 | 129,187,779 | - | 129,187,779
Reversals | (3,031,438) | (248,091) | (22,240,988) | (25,520,517) | (1,176,003) | (26,696,520)
Utilization | (965,105) | (28,886,830) | (27,976,220) | (57,828,155) | (749,989) | (58,578,144)
Exchange and interests | - | - | 20,563,907 | 20,563,907 | - | 20,563,907
31 December 2024 | 66,804,503 | 84,857,781 | 321,129,830 | 472,792,114 | 182,792 | 472,974,906
Changes in consolidation perimeter | 319,044 | 815,221 | - | 1,134,265 | - | 1,134,265
Increases | 14,566,247 | 10,000,985 | 64,256,146 | 88,823,378 | - | 88,823,378
Reversals | (1,379,222) | (26,733,207) | (35,575,964) | (63,688,393) | - | (63,688,393)
Utilization | (2,476,982) | (22,877,742) | (27,051,024) | (52,405,748) | - | (52,405,748)
Exchange and interests | - | - | (31,295,368) | (31,295,368) | - | (31,295,368)
Transfers (Note 7) | - | (458,232) | - | (458,232) | - | (458,232)
31 December 2025 | 77,833,590 | 45,604,806 | 291,463,620 | 414,902,016 | 182,792 | 415,084,808
As of 31 December 2025, the existing provision of EUR 77.8 million is intended to deal with various legal proceedings brought against the Group in Portugal and abroad.
As of 31 December 2025, the balance of this item includes, among other estimates, a provision of EUR 14.3 million (EUR 28.0 million as of 31 December 2024 which were partially utilised in 2025) related to compensations to be paid to passengers.
In the year ended 31 December 2024, and considering the potential impact of the unification of case law on similar legal proceedings, the Group recognised a provision amounting to EUR 40.6 million, recorded under other non-recurring items (Note 31).
This provision was reassessed in the year ended 31 December 2025 and reduced to EUR 21.7 million, mainly reflecting an updated assessment of the assumptions associated with the contingency, based on developments up to that date, as well as payments made.
In addition, as of 31 December 2025, the Group continues to recognise a specific provision for legal proceedings of this nature already filed, amounting to EUR 45.0 million, of which EUR 37.3 million had already been recognised as of 31 December 2024.
Additionally, considering that TAP ME Brasil remains subject to other contingencies until its liquidation, the Group recognised, in December 2025, a provision in the amount of EUR 4.7 million, corresponding to the estimated remaining liabilities (Note 31).
During this year, a gain amounting to EUR 13.7 million was recognised in connection with the reversal of the redelivery provision relating to aircraft whose phase-out occurred in the year 2025 (Note 28), of which EUR 5.5 million relates to the entry of an A330 CEO aircraft into a lease with purchase option, which previously already belonged to the fleet under a lease agreement without purchase option.
As of 31 December 2025, and considering the payments already made, the balance of the provision for restructuring expenses amounts to EUR 183 thousand, which relates to future payments already agreed upon.
""",
        sums=[(6, range(0, 6)), (13, range(6, 13))],
        rowsums=[(3, range(0, 3)), (5, [3, 4])],
    ),
    dict(
        sheet="N37a Contingencies", topic="contingencies", note="37",
        title="37. Contingencies", page="pp.220–221",
        header=["2025", "2024"],
        rows="""
Tax contingencies | 116,006 | 204,038
Civil contingencies | 34,070,945 | 28,584,636
Regulatory contingencies | 6,426,612 | 16,012,678
Total | 40,613,563 | 44,801,352
As of 31 December 2025 and 2024, the Group does not have contingent assets that are required to be disclosed. The contingent liabilities of a fiscal, civil and regulatory nature as of those dates were as follows:
Civil contingencies mainly include legal proceedings brought by customers in relation to operational irregularities, as well as a lawsuit filed by the former Chief Executive Officer of TAP S.A., Christine Ourmières Widener, concerning the termination of her duties.
Regulatory contingencies mainly include proceedings initiated by national regulatory authorities.
Based on the opinion of its legal advisors, the Group has considered that an unfavourable outcome of these proceedings is not probable.
As of 6 August 2025, the date on which SIAVILO was declared insolvent by the Lisbon Commercial Court of the Judicial District of Lisbon, the outstanding amounts of these tranches amounted to EUR 181.1 million and EUR 59.7 million, respectively.
Based on the opinion of its legal advisors regarding the qualification of the aforementioned bond loans as shareholder loans and the consequent nullity of the guarantees granted under the applicable legal framework, (however, according to the contract, the maximum guaranteed amount would be EUR 90 million) the Board of Directors considers that this situation is not expected to result in material impacts for TAP S.A. that could affect the Group’s financial position as of 31 December 2025.
""",
        sums=[(3, range(0, 3))],
    ),
    dict(
        sheet="N37b Guarantees", topic="contingencies", note="37",
        title="37. Contingencies — Guarantees provided", page="pp.220–221",
        header=["2025", "2024"],
        rows="""
Bank guarantees provided by Head Office
Aircraft | 7,008,158 | 34,074,829
Airports | 3,894,809 | 2,396,817
Labour Court | 415,242 | 415,242
Other | 4,415,532 | 4,402,821
Bank guarantees provided by Representations | 3,018,320 | 3,444,575
Bank guarantees provided by other Group companies | 215,349 | 7,349
[Total] | 18,967,410 | 44,741,633
The decrease in guarantees provided in respect of aircraft is mainly due to the cancellation of guarantees following negotiations with the respective lessors.
""",
        sums=[(7, range(1, 7))],
    ),
    dict(
        sheet="N41 Subsequent events", topic="contingencies", note="41",
        title="41 Subsequent events — Legal action by Azul", page="p.225",
        header=[],
        rows="""
On 13 March 2026, Azul brought legal action against TAP S.A., seeking payment by TAP S.A. to Azul of a total amount of EUR 188,985,150 for the alleged breach of the obligations assumed under the Security Agreement (Note 37). The deadline for TAP S.A. to submit its statement of defence is currently running and will expire on 13 May 2026.
""",
    ),
    dict(
        sheet="N38a RP assets 2025", topic="related_parties", note="38",
        title="38. Related parties — Balances — 2025 - Assets", page="p.222",
        header=["Customers (Note 10)", "Advances to suppliers (Note 10)",
                "Other receivables non-current (Note 10)", "Deferred expenses (Note 13)",
                "Supplementary capital contributions (Note 10)",
                "Other receivables current (Note 10)",
                "Impairment on accounts receivable (Note 10)",
                "Non-current assets held for sale (Note 7)", "Total"],
        rows="""
SIAVILO | 151,183 | - | - | - | - | 1,111,756,403 | (1,111,907,243) | - | 343
SPdH | 150,450 | - | 5,143,230 | - | - | 19,267,696 | - | 2,942 | 24,564,318
TAP ME Brazil | 15,162,376 | 504,620 | 2,959,062 | 112,967 | - | 10,236,751 | (28,563,111) | - | 412,665
[Total] | 15,464,009 | 504,620 | 8,102,292 | 112,967 | - | 1,141,260,850 | (1,140,470,354) | 2,942 | 24,977,326
""",
        sums=[(3, range(0, 3))], rowsums=[(8, range(0, 8))],
    ),
    dict(
        sheet="N38b RP assets 2024", topic="related_parties", note="38",
        title="38. Related parties — Balances — 2024 - Assets", page="p.222",
        header=["Customers (Note 10)", "Advances to suppliers (Note 10)",
                "Accrued income (Note 10)", "Deferred expenses (Note 13)",
                "Supplementary capital contributions (Note 10)",
                "Other receivables current (Note 10)",
                "Impairment on accounts receivable (Note 10)",
                "Non-current assets held for sale (Note 7)", "Total"],
        rows="""
Portuguese State | - | - | - | - | 343,000,000 | - | - | - | 343,000,000
SIAVILO | (67) | - | 885 | - | - | 1,082,706,085 | (1,082,705,989) | - | 914
SPdH | 4,806,447 | - | 6,081,872 | - | - | 13,266,363 | - | - | 24,154,682
TAP ME Brazil | 17,009,173 | 510,772 | - | 112,967 | - | 10,508,038 | (27,647,671) | - | 493,279
Cateringpor | 145,720 | - | 2,017,407 | - | - | 166,577 | - | - | 2,329,704
UCS | 66,706 | - | - | - | - | 118,358 | - | - | 185,064
[Total] | 22,027,979 | 510,772 | 8,100,164 | 112,967 | 343,000,000 | 1,106,765,421 | (1,110,353,660) | - | 370,163,643
""",
        sums=[(6, range(0, 6))], rowsums=[(8, range(0, 8))],
    ),
    dict(
        sheet="N38c RP liabilities 2025", topic="related_parties", note="38",
        title="38. Related parties — Balances — 2025 - Liabilities", page="p.222",
        header=["Suppliers (Note 20)", "Accrued expenses (Note 20)", "Deferred income (Note 21)",
                "Other accounts payable current (Note 20)", "Total"],
        rows="""
Portuguese State | - | - | - | (24,990,000) | (24,990,000)
SIAVILO | (1,891) | - | - | - | (1,891)
SPdH | (4,877,931) | (3,341,579) | (89,006) | (29,888) | (8,338,404)
TAP ME Brazil | (299,347) | - | - | - | (299,347)
[Total] | (5,179,168) | (3,341,579) | (89,006) | (25,019,888) | (33,629,642)
""",
        sums=[(4, range(0, 4))], rowsums=[(4, range(0, 4))],
    ),
    dict(
        sheet="N38d RP liabilities 2024", topic="related_parties", note="38",
        title="38. Related parties — Balances — 2024 - Liabilities", page="p.222",
        header=["Suppliers (Note 20)", "Accrued expenses (Note 20)", "Deferred income (Note 21)",
                "Other accounts payable current (Note 20)", "Total"],
        rows="""
SIAVILO | (30) | - | - | - | (30)
SPdH | (5,672,854) | (3,205,374) | (89,006) | - | (8,967,234)
TAP ME Brazil | (373,737) | - | - | - | (373,737)
Cateringpor | (2,207,692) | (2,374,943) | (238,982) | - | (4,821,617)
UCS | (15,760) | (70,643) | - | (427,005) | (513,408)
[Total] | (8,270,073) | (5,650,960) | (327,988) | (427,005) | (14,676,026)
""",
        sums=[(5, range(0, 5))], rowsums=[(4, range(0, 4))],
    ),
    dict(
        sheet="N38e RP transactions 2025", topic="related_parties", note="38",
        title="38. Related parties — Transactions — 2025", page="p.223",
        header=["Operating income", "Operating expenses", "Depreciation right-of-use",
                "Interest income", "Interest expenses", "Total"],
        rows="""
SIAVILO | - | (1,131) | - | 27,703,683 | - | 27,702,552
SPdH | 6,972,560 | (111,243,023) | - | 1,006,476 | (216,469) | (103,480,456)
TAP ME Brazil | - | - | - | 46,441 | - | 46,441
Cateringpor | 494,432 | (12,889,972) | - | - | - | (12,395,540)
UCS | 51,567 | (425,788) | - | - | - | (374,221)
[Total] | 7,518,559 | (124,559,914) | - | 28,756,600 | (216,469) | (88,501,224)
Operating expenses with SPdH refer to ground handling services provided by SPdH to support aircraft, passengers, luggage, cargo and mail.
These transactions are carried out under terms and conditions similar to those practiced in commercial agreements usually celebrated with other airlines.
The inclusion of UCS and Cateringpor in the Group’s consolidation perimeter on 21 January 2025 and 9 April 2025, respectively (Note 2.4), resulted in these entities no longer qualifying as related parties of the Group since those dates.
""",
        sums=[(5, range(0, 5))], rowsums=[(5, range(0, 5))],
    ),
    dict(
        sheet="N38f RP transactions 2024", topic="related_parties", note="38",
        title="38. Related parties — Transactions — 2024", page="p.223",
        header=["Operating income", "Operating expenses", "Depreciation right-of-use",
                "Interest income", "Interest expenses", "Total"],
        rows="""
SIAVILO | - | (60) | - | 40,073,520 | - | 40,073,460
Portugália | 2,406,069 | (1,152,889) | (74,588,999) | - | (16,220,638) | (89,556,457)
SPdH | 6,762,599 | (105,650,525) | - | - | (993,018) | (99,880,944)
Cateringpor | 1,920,765 | (56,827,057) | - | - | - | (54,906,292)
UCS | 670,091 | (5,401,448) | - | - | - | (4,731,357)
[Total] | 11,759,524 | (169,031,979) | (74,588,999) | 40,073,520 | (17,213,656) | (209,001,590)
""",
        sums=[(5, range(0, 5))], rowsums=[(5, range(0, 5))],
    ),
    dict(
        sheet="N24a Segments", topic="segments", note="24",
        title="24. Segment Reporting — Financial information by business segments", page="p.211",
        header=["2025 Air Transport", "2025 Maintenance and engeneering", "2025 Other",
                "2025 Intersegment eliminations", "2025 Total", "2024 Air Transport",
                "2024 Maintenance and engeneering", "2024 Other", "2024 Total"],
        rows="""
Operating Income | 4,025,132,626 | 263,687,624 | 79,801,393 | (55,130,625) | 4,313,491,018 | 3,981,796,334 | 242,362,167 | 18,275,519 | 4,242,434,020
Operating loss | (3,799,157,459) | (231,784,302) | (111,372,438) | 55,130,625 | (4,087,183,574) | (3,657,217,125) | (195,264,652) | (75,557,991) | (3,928,039,768)
Operating results | 225,975,167 | 31,903,322 | (31,571,045) | - | 226,307,444 | 324,579,209 | 47,097,515 | (57,282,472) | 314,394,252
External net financial results | (159,500,679) | 1,986,751 | (599,032) | - | (158,112,960) | (213,184,974) | (5,629,638) | - | (218,814,612)
Income tax | (50,311,559) | (23,553,084) | 7,785,231 | - | (66,079,412) | (45,872,660) | (10,931,851) | 14,946,851 | (41,857,660)
Net Income | 16,162,929 | 10,336,989 | (24,384,846) | - | 2,115,072 | 65,521,575 | 30,536,026 | (42,335,621) | 53,721,980
The impacts of Portugália’s operations have been included in the Air Transport segment since the subsidiary was included in the Group’s consolidation perimeter on 8 November 2024.
The Group does not present segmental assets and liabilities, considering that this information is not disclosed to the primary decision-makers for operational decisions.
""",
        sums=[(2, [0, 1]), (5, [2, 3, 4])],
        rowsums=[(4, range(0, 4)), (8, range(5, 8))],
    ),
    dict(
        sheet="N24b Operating income", topic="segments", note="24",
        title="24. Segment Reporting — operating income, excluding gains and losses in associates",
        page="p.211",
        header=["2025 Passenger", "2025 Maintenance", "2025 Cargo and Mail", "2025 Other",
                "2025 Total", "2024 Passenger", "2024 Maintenance", "2024 Cargo and Mail",
                "2024 Other", "2024 Total"],
        rows="""
Revenue
Sales | - | 5,444,809 | - | 15,640,198 | 21,085,007 | - | 7,148,141 | - | 1,053,736 | 8,201,877
Services provided | 3,849,317,194 | 256,099,794 | 160,087,049 | 14,774,720 | 4,280,278,757 | 3,820,622,937 | 229,618,049 | 162,730,935 | 10,160,333 | 4,223,132,254
Other income | - | - | - | 12,127,254 | 12,127,254 | - | - | - | 13,589,909 | 13,589,909
[Total] | 3,849,317,194 | 261,544,603 | 160,087,049 | 42,542,172 | 4,313,491,018 | 3,820,622,937 | 236,766,190 | 162,730,935 | 24,803,978 | 4,244,924,040
""",
        sums=[(4, range(1, 4))],
        rowsums=[(4, range(0, 4)), (9, range(5, 9))],
    ),
    dict(
        sheet="N24c Geography", topic="segments", note="24",
        title="24. Segment Reporting — sales and services provided by geographical area",
        page="p.212",
        header=["2025 Passenger", "2025 Maintenance", "2025 Cargo and Mail", "2025 Other",
                "2025 Total", "2024 Passenger", "2024 Maintenance", "2024 Cargo and Mail",
                "2024 Other", "2024 Total"],
        rows="""
Mainland and islands | 247,101,512 | 23,095,877 | 11,098,169 | 24,970,067 | 306,265,625 | 254,754,346 | 21,333,185 | 9,195,166 | 6,625,502 | 291,908,199
Europe | 1,288,519,027 | 232,522,157 | 9,517,590 | 1,945,903 | 1,532,504,677 | 1,280,517,904 | 206,588,430 | 10,258,145 | 2,968,855 | 1,500,333,334
South Atlantic | 1,118,292,770 | 127,944 | 88,893,117 | 1,700,957 | 1,209,014,788 | 1,105,911,271 | 104,374 | 89,864,936 | 695,482 | 1,196,576,063
North Atlantic | 781,947,670 | 1,181,014 | 26,698,385 | 1,175,496 | 811,002,565 | 788,312,411 | 4,827,563 | 28,456,728 | 523,460 | 822,120,162
Mid Atlantic | 24,711,346 | - | 3,937,263 | 34,179 | 28,682,788 | 25,898,102 | - | 3,921,755 | 19,669 | 29,839,526
Africa | 388,744,869 | 2,076,839 | 19,942,525 | 588,316 | 411,352,549 | 364,872,313 | 3,671,738 | 20,859,452 | 381,101 | 389,784,604
Other | - | 2,540,772 | - | - | 2,540,772 | 356,590 | 240,900 | 174,753 | - | 772,243
[Total] | 3,849,317,194 | 261,544,603 | 160,087,049 | 30,414,918 | 4,301,363,764 | 3,820,622,937 | 236,766,190 | 162,730,935 | 11,214,069 | 4,231,334,131
""",
        sums=[(7, range(0, 7))],
        rowsums=[(4, range(0, 4)), (9, range(5, 9))],
    ),
    dict(
        sheet="N27a Employee costs", topic="staff", note="27",
        title="27. Employee costs", page="p.214",
        header=["2025", "2024"],
        rows="""
Fixed remuneration | 502,708,999 | 407,419,004
Variable remuneration | 255,811,558 | 219,509,158
Social security contributions | 150,192,113 | 127,934,858
Other insurance | 20,084,185 | 19,901,451
Post-employment benefits (Note 17) | 16,525,930 | 10,247,170
Meals allowance | 8,304,720 | 14,033,145
Social action costs | 7,320,260 | 7,239,544
Work accident insurance | 4,863,906 | 6,954,180
Training and recruitment | 2,763,118 | 1,557,718
Uniform and work clothes | 1,745,286 | 1,453,179
Other expenses with employees | 1,800,605 | 880,252
[Total] | 972,120,680 | 817,129,659
The increase in employee costs recorded in 2025 compared to the previous year mainly results from: (i) the inclusion of Portugália, UCS and Cateringpor in the Group’s consolidation perimeter (Note 2.4), (ii) the increase in the number of employees at TAP S.A., and (iii) the salary increases provided for in collective bargaining agreements.
""",
        sums=[(11, range(0, 11))],
    ),
    dict(
        sheet="N27b Governing bodies", topic="staff", note="27",
        title="27. Employee costs — remuneration allocated to the Governing Bodies and "
              "other personnel expenses", page="p.214",
        header=["2025", "2024"],
        rows="""
Remunerations
Employees | 969,346,877 | 814,708,955
Governing Bodies | 2,773,803 | 2,420,704
[Total] | 972,120,680 | 817,129,659
""",
        sums=[(3, [1, 2])],
    ),
    dict(
        sheet="N27c Average employees", topic="staff", note="27",
        title="27. Employee costs — average number of employees", page="p.215",
        unit="Number of employees (no unit printed)",
        header=["2025", "2024"],
        rows="""
Portugal
Cabin Crew employees | 3,786 | 3,273
Maintenance and engineering employees | 1,899 | 1,933
Ground employees | 2,407 | 1,365
Technical flight employees | 1,500 | 1,265
Representations
Brazil | 82 | 80
USA | 32 | 33
Spain | 28 | 29
Angola | 19 | 20
Italy | 18 | 18
France | 16 | 15
UK/Ireland | 12 | 11
Germany | 12 | 12
Venezuela | 6 | 6
Switzerland | 4 | 4
Other | 46 | 44
[Total] | 9,867 | 8,108
During fiscal years 2025 and 2024 the average number of employees serving the Group was 9,867 and 8,108, respectively:
""",
        sums=[(17, list(range(1, 5)) + list(range(6, 17)))],
    ),
]


def cell(text):
    """A printed figure: (1,234) is negative, '-' stays a dash."""
    text = text.strip()
    if text == "-":
        return "-"
    negative = text.startswith("(") and text.endswith(")")
    value = int(text.strip("()").replace(",", ""))
    return -value if negative else value


def parse(block):
    rows = []
    for line in block.strip().splitlines():
        parts = line.split(" | ")
        rows.append([parts[0].strip()] + [cell(p) for p in parts[1:]])
    return rows


def number(value):
    return 0 if value == "-" else value


def check(spec, rows):
    """Do the copied lines add up to the totals the note prints? (copying check only)"""
    problems = []
    width = len(spec["header"])
    for total, parts in spec.get("sums", []):
        for col in range(1, width + 1):
            added = 0
            for part in parts:
                index, sign = part if isinstance(part, tuple) else (part, 1)
                added += sign * number(rows[index][col])
            if added != number(rows[total][col]):
                problems.append(f"{spec['sheet']}: column '{spec['header'][col - 1]}', row "
                                f"'{rows[total][0]}' prints {rows[total][col]}, lines add to {added}")
    for total, parts in spec.get("rowsums", []):
        for row in rows:
            if len(row) == 1:
                continue
            added = sum(number(row[col + 1]) for col in parts)
            if added != number(row[total + 1]):
                problems.append(f"{spec['sheet']}: row '{row[0]}', column "
                                f"'{spec['header'][total]}' prints {row[total + 1]}, "
                                f"columns add to {added}")
    return problems


def main():
    book = Workbook()
    index = book.active
    index.title = "Index"
    index.append(["Sheet", "Topic", "Note", "Title as printed", "Page", "Unit", "Status"])
    bold = Font(bold=True)
    for c in index[1]:
        c.font = bold
    problems = []
    for spec in SHEETS:
        assert len(spec["sheet"]) <= 31, spec["sheet"]
        unit = spec.get("unit", UNIT)
        rows = parse(spec["rows"])
        for row in rows:
            assert len(row) in (1, len(spec["header"]) + 1), (spec["sheet"], row[0])
        problems += check(spec, rows)
        index.append([spec["sheet"], spec["topic"], spec["note"], spec["title"],
                      spec["page"], unit, "read"])
        sheet = book.create_sheet(spec["sheet"])
        sheet["A1"] = spec["title"]
        sheet["A1"].font = bold
        sheet["A2"] = f"Source: {REPORT}, {spec['page']}"
        sheet["A3"] = unit
        for col, text in enumerate(["Item"] + spec["header"], start=1):
            sheet.cell(row=5, column=col, value=text).font = bold
        for r, row in enumerate(rows, start=6):
            for col, value in enumerate(row, start=1):
                c = sheet.cell(row=r, column=col, value=value)
                if col > 1 and isinstance(value, int):
                    c.number_format = "#,##0;(#,##0)"
        sheet.column_dimensions["A"].width = 60
        for col in range(2, len(spec["header"]) + 2):
            sheet.column_dimensions[sheet.cell(row=5, column=col).column_letter].width = 20
    index.column_dimensions["A"].width = 28
    index.column_dimensions["B"].width = 20
    index.column_dimensions["D"].width = 80
    index.column_dimensions["F"].width = 26
    OUT.parent.mkdir(parents=True, exist_ok=True)
    book.save(OUT)
    print(f"Written: {OUT} ({len(SHEETS)} note sheets)")
    if problems:
        print("Totals that do not match the copied lines:")
        for problem in problems:
            print("  -", problem)
    else:
        print("Every printed total matches the copied lines.")


if __name__ == "__main__":
    main()
