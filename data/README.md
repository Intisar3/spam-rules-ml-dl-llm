# Data card

All messages are **synthetic**, written by hand as templates for teaching spam detection. They do not come from real people, and no real organization is named. They are meant for detection research and training only: do not send them.

## Files

| File | Rows | Columns |
|---|---|---|
| `messages.csv` | 520 | `text`, `lang` (ar / en), `label` (ham / spam), `category`, `template_id` |
| `tricky.csv` | 40 | `text`, `lang`, `label`, `why_tricky` |
| `templates/*.json` | source | hand-written templates, two variants each |
| `build_dataset.py` | script | builds both CSV files from the templates, then runs the audit |
| `audit.py` | script | automatic audit: safety, train/test leakage, one-feature shortcuts, balance; fails the build on any problem |
| `v1/` | local archive | the first version, kept locally for comparison and excluded from publication (`.gitignore`) because it contains real link shorteners and brand names; see `reports/تدقيق البيانات - الإصدار الأول.md` |

## Definition of spam

spam = fraud (phishing, stealing a code or password, fake prize, fake job, fee before delivery, impersonation) **or** unsolicited bulk marketing from an unknown sender. Messages from a known service the person uses (bill, appointment, delivery, real one-time code, subscribed store offer) are ham.

## Design choices

- **Split by template.** Both variants of a template share a `template_id`. The notebook keeps every template entirely in train or entirely in test, so the test score measures generalization, not memorization.
- **Fewer shortcut features.** Length, links, phone numbers, names, amounts, codes, "!" and capital letters follow similar quotas in ham and spam. MSA and Gulf dialect appear in both labels, and so do topics such as banks, loans, customs, prizes and jobs. A small dataset cannot remove every surface cue, so the notebook reports a length-only baseline for comparison.
- **Sender domains carry meaning.** Ham from official senders uses a small set of trusted domains (`bank.example`, `pay.example`, `shop.example`, `store.example`, `gov.example`, `photos.example`). Spam never uses them, and each spam template uses its own domain, as in real phishing.
- **Known limits.** Some realistic patterns are kept: loan offers aimed at residents, scams that impersonate a friend by name.
- **Tricky set.** `tricky.csv` uses tactics reserved for it and absent from training (obfuscated spelling, Arabizi, lookalike domains, QR and crypto scams, "new number" scams).

## Safety

- Links use only reserved `.example` domains (RFC 2606), which cannot be registered.
- Phone numbers are fully masked (`+968 XXXX XXXX`, `XXXX XXXX`, `+44 XXXX XXXXXX`).
- No real organization, brand or product is named.
- Names are common first names only, Arab and expat, in varied roles.

Full rules: `templates/SPEC.md`.

## License

- Data (`messages.csv`, `tricky.csv`, `templates/`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution: "Bilingual spam teaching dataset, Intisar Al Hinai, 2026, CC BY 4.0".
- Scripts (`build_dataset.py`, `audit.py`): MIT, see [LICENSE](../LICENSE).
