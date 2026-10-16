# CERBER — Object Review

[Русский](README.md) · [Contributing / Как помочь](CONTRIBUTING.md) · [First tasks](VOLUNTEER_TASKS.md)

An independent CR20KB open source module for reviewing object hypotheses based on
public [Europol Trace an Object cards](https://www.europol.europa.eu/stopchildabuse).
**This project is not affiliated with, partnered with, or endorsed by Europol.**

This version validates structured records offline and produces a local note for
human review. It does not recognise images, search products automatically, identify
people or include the CERBER Windows scanner.

## Run

Python 3.10+; no third-party packages, API keys or paid services. From the repository root:

```console
python -m trace_object demo
python -m trace_object validate examples/known-object.json
python -m trace_object validate examples/insufficient-data.json
python -m trace_object report examples/known-object.json
python -m unittest discover -s tests -v
python tools/audit_publication.py
```

On Windows, `py -3` can replace `python`. Reports receive unique filenames under
`.local/reports/`, which is excluded from Git. Do not post working reports to Issues.
These commands make no network requests and send nothing to Europol.

## Human review workflow

1. Manually open a current official card and verify its ID, URL and object.
2. Keep real JSON records under `.local/`. Copy the example structure, set `demo`
   to `false`, and use the actual official ID and card URL.
3. Separate visible observations from hypotheses. For each candidate provide public
   product sources, matches, contradictions, qualitative confidence and what to check next.
4. Run `validate` and read a local report. `candidate` remains unconfirmed;
   `insufficient_data` is a valid outcome. No numerical probabilities are produced.
5. Public Issues may contain only object information, official card IDs/links and
   public product sources. Check every field manually before posting.
6. After human verification, send substantial investigative information through the
   form **on the official Europol card**; explain limitations and disclose any AI use.
   [General official form](https://www.europol.europa.eu/stopchildabuse/can-you-help).
   GitHub Issues are not an investigative reporting channel.

## Limits and boundaries

- No personal data, suspected persons, victim addresses, identifiable people or accusations
  in public Issues or commits. Do not seek original abuse material.
- An object match does not identify a person. Product distribution does not establish
  the location of a photograph. No generative reconstruction or unscaled dimensions.
- No automatic copying of Europol or seller images. Public access is not a licence.
  This repository contains no external images or logos.
- Validation checks structure, not truth, image rights, link availability or absence
  of every kind of personal data. Human review is mandatory before publication.
- No scraping, monitoring, OCR, LLM, automatic matching or submission is implemented.
  A real official image pilot has not been performed.

Both demos are fictional and unrelated to any case. The known object is supplied by
the scenario author; the result does not demonstrate automated recognition.
`example.invalid` is deliberately a non-resolving demonstration source.

## Licence

Original code, documentation and synthetic examples are [MIT](LICENSE).
External Europol material and product catalogues retain their own rights and are not
covered by this licence. See [sources and rights](docs/SOURCES_AND_RIGHTS.md),
[record format](docs/RECORD_FORMAT.md), [publication audit](docs/PUBLICATION.md).
Keep working reports, downloads, credentials and case data out of Git.
