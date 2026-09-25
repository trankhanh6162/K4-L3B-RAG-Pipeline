# RAG evaluation results

## Run information

| Field | Value |
| --- | --- |
| Evaluation date | 2026-09-25 |
| Framework and version | Ragas 0.4.3 |
| Evaluator model | gemini-3.5-flash-lite |
| Generator model | gemini-3.5-flash-lite |
| Embedding model | gemini-embedding-001 |
| Corpus version/commit | f21b018 |
| Golden dataset size | 20 |
| `top_k` | 5 |
| Fallback threshold and calibration | 0.3; dense cosine threshold |

## Configurations

- **Config A — dense-only:** Gemini query embedding + Chroma cosine search.
- **Config B — hybrid + RRF:** dense and BM25 candidates fused once with RRF; PageIndex attempted below the dense threshold.

Both configurations used the same golden dataset, generator, evaluator, prompt and `top_k`; only retrieval strategy changed.

## Evaluation coverage

`evaluation_results.json` contains answers and latency for all 40 runs, but Ragas scores for only **15/40 runs (37.5%)**. Config A has 8 scored runs and Config B has 7. Cases 1–7 are the only complete A/B pairs, so the comparison below uses those 7 matched pairs. Case 8-A is excluded from the A/B aggregate because 8-B is unscored; 8-B and cases 9–20 have empty `scores` objects.

## Overall scores on 7 complete A/B pairs

| Metric | Config A | Config B | Delta B−A |
| --- | ---: | ---: | ---: |
| Faithfulness | 0.8571 | 0.8571 | 0.0000 |
| Answer relevance | 0.9096 | 0.9105 | +0.0010 |
| Context recall | 1.0000 | 1.0000 | 0.0000 |
| Context precision | 1.0000 | 1.0000 | 0.0000 |
| **Average** | **0.9417** | **0.9419** | **+0.0002** |

## A/B comparison

- Quality is effectively tied on the 7 scored pairs: Config B leads by only 0.0002 in the four-metric average, which is not sufficient evidence of a meaningful improvement.
- Mean latency over all 20 runs is A=3.584s and B=4.018s per case. Config B is 0.434s, or approximately 12.1%, slower.
- Config A is currently the more practical choice because it has nearly identical measured quality and lower latency. This remains provisional until all 40 runs are scored.

## Worst performers

| # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Một tín chỉ trong chương trình thạc sĩ tương đương bao nhiêu giờ học định mức? | A | 0.0000 | 0.8947 | 1.0000 | 1.0000 | evaluation | The answer “50 hours” exactly matches the reference and retrieved context. The zero faithfulness score is likely an evaluator anomaly rather than a retrieval or generation failure. |
| 2 | Một tín chỉ trong chương trình thạc sĩ tương đương bao nhiêu giờ học định mức? | B | 0.0000 | 0.8947 | 1.0000 | 1.0000 | evaluation | The identical result for A and B reinforces that the faithfulness judge should be rerun and inspected. |
| 3 | Luận văn thạc sĩ định hướng nghiên cứu có bao nhiêu tín chỉ và thực hiện tối thiểu bao lâu? | A | 1.0000 | 0.7068 | 1.0000 | 1.0000 | generation/evaluation | The answer correctly gives 12–15 credits and at least six months. Its lead-in or evaluator sensitivity may explain the low relevance score; the more direct B response scored 0.9083. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| ---: | --- | --- | --- | --- |
| 1 | Rerun scoring for the 25 empty `scores` objects | Only 15/40 runs have Ragas scores | Produce a valid full-dataset comparison | Confirm that every run contains all four metrics, then recompute over 20 pairs |
| 2 | Rerun and manually inspect case 5 | Both answers match the evidence, yet faithfulness is 0 | Identify evaluator instability or claim-parsing errors | Repeat scoring at least three times and inspect extracted claims |
| 3 | Make answers direct and remove unnecessary lead-ins | Case 7-A is correct but relevance is 0.7068, versus 0.9083 for the more direct B answer | Improve answer relevance without reducing faithfulness | A/B test the response prompt on multi-part questions |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| --- | --- | ---: | ---: | --- |
| Complete missing scoring | 15/40 scored runs | Pending | No generation rerun required | Required before a final A/B conclusion |
| Repeat case 5 scoring | Faithfulness = 0 for A and B | Pending | Evaluator calls only | Check whether the zero score is reproducible |
