# Banking77 attribution (benchmark data only)

The calibration and verification inputs in this directory are derived from
the public Banking77 dataset published by PolyAI in
`PolyAI-LDN/task-specific-datasets` at commit
`57ec275d8078af65b7731c2a98be812d844a6d6b` (tree
`05eb3f1c7b43a6e1f2b8576b882115423e9031e3`). The dataset is licensed under
the Creative Commons Attribution 4.0 International license; the exact
`LICENSE` bytes of that commit are preserved beside this file as
`BANKING77_LICENSE` (SHA-256
`7e7170e3cebf88a9f60c7b8421418323c09304da1af4d5e90f4da1dc1c8a2661`). The
dataset license is separate from Actseal's Apache-2.0 code license and
applies only to the data files here.

Please cite, as the dataset README requests:

> Iñigo Casanueva, Tadas Temcinas, Daniela Gerz, Matthew Henderson and
> Ivan Vulic (2020). *Efficient Intent Detection with Dual Sentence
> Encoders*. Proceedings of the 2nd Workshop on NLP for ConvAI, ACL 2020.
> https://arxiv.org/abs/2003.04807

## Changes made

The original data is a 77-intent corpus with 10,003 training and 3,080 test
rows. These files contain a selection, not the corpus:

- the first 16 category strings in Python's case-sensitive sort;
- `calibration.jsonl`: per selected label, in that label order, the first 20
  training rows (original record order) whose `strip().casefold()` text is
  neither a normalized test text nor already selected (320 rows; selected-label
  training records 3104, 3117 and 4577 match test texts and are excluded);
- `verification.jsonl`: every test row of a selected label in original test
  order, first occurrence per normalized text (639 rows; test record 1462 is
  a normalized duplicate and is omitted).

Text bytes are unchanged; normalization is used only for exclusion and
deduplication. Case ids are `<split>:<1-based data record number>` in the
original CSV files. The original disclaimer in the LICENSE applies: the data
is provided as-is without warranties.

This selection is a finite public benchmark subset. It is not IID population
evidence, not the full 77-class task, not a powered calibration study, and
makes no claim about label truth or about the data's absence from any model's
training set.
