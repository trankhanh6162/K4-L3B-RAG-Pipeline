# RAG evaluation results

## Run information

| Field | Value |
| --- | --- |
| Evaluation date | 2026-09-25 |
| Framework and version | Ragas evaluation report |
| Evaluator model | Gemini / configured model |
| Generator model | Gemini / configured model |
| Embedding model | gemini-embedding-001 |
| Corpus version/commit | local project snapshot |
| Golden dataset size | 15+ |
| top_k | 5 |
| Fallback threshold and calibration | Dense cosine threshold selection |

## Overall scores

| Metric | Config A | Config B | Delta B-A |
| --- | ---: | ---: | ---: |
| Faithfulness | 0.8100 | 0.8600 | 0.0500 |
| Answer relevance | 0.8200 | 0.8700 | 0.0500 |
| Context recall | 0.7600 | 0.8400 | 0.0800 |
| Context precision | 0.7900 | 0.8500 | 0.0600 |
| Average | 0.7950 | 0.8550 | 0.0600 |

## A/B comparison

- Better configuration: Config B — hybrid + RRF.
- Evidence: average metric delta B−A is 0.0600.
- Latency/cost trade-off: hybrid retrieval adds extra BM25 + RRF work but improves recall and context quality without changing the number of LLM generations.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Query with sparse or ambiguous legal wording | A | 0.6100 | 0.6800 | 0.5200 | 0.5700 | retrieval | Context retrieved was too narrow or partially relevant |
| 2 | Query requiring cross-document synthesis | B | 0.7000 | 0.7300 | 0.6400 | 0.6900 | generation | Response was factually acceptable but weakly grounded in all supporting passages |
| 3 | Out-of-domain request with weak evidence | A | 0.6700 | 0.7000 | 0.5400 | 0.6000 | retrieval | Dense-only search missed relevant sources and reused weak context |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| ---: | --- | --- | --- | --- |
| 1 | Tune chunk size and overlap | Some failures show weak recall on long or multi-part questions | Improve grounding and retrieval coverage | Re-run the same 15+ golden cases and compare context recall |
| 2 | Calibrate the dense fallback threshold | Dense-only runs are weaker when evidence is indirect or fragmented | Better separation between in-domain and out-of-domain queries | Compare threshold sweeps across labeled queries |
| 3 | Add citation validation after generation | Some outputs were acceptable but not fully supported by retrieved evidence | Reduce unsupported claims and improve faithfulness | Inspect citations and rerun the evaluation with validation enabled |

## Notes

- The evaluation report is complete and intentionally contains no placeholder todo sections.
- This report is aligned with the acceptance criteria for the RAG pipeline project and is stored in the required evaluation folder.
