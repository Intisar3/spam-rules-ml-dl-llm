# Data spec (v2)

Shared rules for every template file in this folder. `data/build_dataset.py` reads the JSON files and writes `data/messages.csv`.

## File format

Each file is a JSON array of templates:

```json
{"template_id": "ar_ham_001", "label": "ham", "category": "bank", "register": "msa", "variants": ["...", "..."]}
```

- `label`: `ham` or `spam`.
- `category`: one of `personal`, `work`, `study`, `health`, `bank`, `bill`, `delivery`, `government`, `telecom`, `shopping`, `job`, `prize`, `loan`, `fraud_otp`, `fraud_phishing`, `fraud_fee`, `fraud_impersonation`, `promo`.
- `register`: `msa` or `dialect` (Arabic files), `formal` or `casual` (English files).
- `variants`: exactly 2 complete messages from the same template. They differ in details (name, time, amount, place, link path, code), and may differ slightly in wording. They must not be identical after replacing digits.
- Every template is written from scratch, with its own structure. No two templates share an opening phrase or sentence frame.

## Spam definition

spam = fraud (phishing, stealing a code or password, fake prize, fake job, fee before delivery, impersonation) **or** unsolicited bulk marketing from an unknown sender. A message from a known service the person uses (bill, appointment, delivery, real one-time code, subscribed store offer) is ham.

## Balance rules (prevent shortcuts)

Every file follows the same quotas so that no surface feature separates ham from spam:

| Feature | Share of templates (each file) |
|---|---|
| Length under 60 characters | about 25% |
| Length 60 to 100 characters | about 40% |
| Length 100 to 160 characters | about 35% |
| Contains a link | about 35% |
| Contains a phone number | about 20% |
| No link and no phone | at least 40% |
| Contains a personal name | about 30% |
| Contains an amount with currency | about 30% |
| Contains a code of 4 to 6 digits | about 10% |
| Contains "!" | about 20% |
| Contains an emoji | about 10% |
| Mentions an Omani place | about 20% |

Arabic files: about half `msa` and half `dialect` (Gulf / Omani), in **both** ham and spam.
English files: some words in capitals in about 20% of templates, in **both** ham and spam.

Topics appear in both labels. Ham must include genuine messages about banks, loans, customs and parcels, prizes and competitions, jobs, Ramadan and Eid offers, and government services. Spam must include casual dialect scams and scams that address a person by name.

## Safety rules

- Links: only reserved domains ending in `.example`. No real shorteners or real domains. Trusted domains (`bank.example`, `pay.example`, `shop.example`, `store.example`, `gov.example`, `photos.example`) belong to official senders and appear only in ham. Each spam template uses its own domain. Both labels mix links with and without `https://`.
- One spelling per name across all files (Grace = جريس, Yusuf).
- Phones: fully masked only: `+968 XXXX XXXX`, `XXXX XXXX`, `+44 XXXX XXXXXX`. No real digits.
- No real organization names (banks, telecoms, police, ministries, couriers, stores, apps, product brands). Use generic names: "البنك", "مزود الاتصالات", "شركة التوصيل", "the bank", "your mobile provider", "a smartphone".
- No real people. Names are common first names only, no surnames. Include expat names (Priya, Rahul, Maria, Joseph, Anil, Grace) next to Arab names.
- Codes: 4 to 6 digits only.
- No offensive content and no stereotypes.

## Language rules

- Arabic rows: Arabic script only, except inside links, codes and "OMR". No English words in Arabic sentences.
- English rows: no Arabic script.
- Verbs, pronouns and adjectives agree with the gender of the addressed name.
- Currency: ر.ع. or ريال in Arabic; OMR in English. No dollars.
- Places across Oman: مسقط، صلالة، صحار، نزوى، صور، عبري، البريمي، خصب، الرستاق، السيب / Muscat, Salalah, Sohar, Nizwa, Sur, Ibri, Buraimi, Khasab, Rustaq, Seeb.

## Reserved for tricky.csv only (never in messages.csv)

- Character obfuscation (dots between letters, digits for letters, spaced letters).
- Arabic written in Latin letters (Arabizi).
- Lookalike or homoglyph domains (`bank-secure-login.example`, `paypa1.example`).
- QR code scams, crypto investment, wrong-number romance openers, "Hi mum, new number" scams.
- A caller posing as bank staff asking for the code by phone or chat.
