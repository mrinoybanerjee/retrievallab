# Third-party notices

## MultiConIR

RetrievalLab includes aggregate benchmark results, ten transformed example cases,
and eight bounded parser-error excerpts derived from
[EIT-NLP/MultiConIR](https://github.com/EIT-NLP/MultiConIR), revision
`9884fb3e1e5c06c9e026aa0042a679412dad1425`.

- Paper: [MultiConIR: Benchmarking Retrieval on Complex Multi-Constraint Queries](https://aclanthology.org/2025.findings-emnlp.726/)
- Upstream license: Apache License 2.0
- Local modifications: rows are normalized into RetrievalLab's probe schema;
  aggregate metrics, work counters, statistics, provenance, and ten dashboard
  examples are emitted. Eight rows with unusable or unnumbered structured queries
  are excluded; bounded diagnostic excerpts explain each exclusion.
- Raw upstream datasets are not redistributed by this repository.

The Apache License 2.0 text is provided at
[`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt). RetrievalLab's original code
remains under the repository's MIT license.
