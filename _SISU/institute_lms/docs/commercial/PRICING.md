# V2 commercial model

The current primary quote model is the [V2 product reference](sources/Global_LMS_Product_Pricing_Customization_Requirements_v2.docx). The exact regional table below takes precedence over approximate percentage multipliers. The earlier proposals below remain separate historical/custom contract options, not additional fees automatically stacked on a subscription.

| Plan | Active students up to | Tier A USD | B | C | D | E |
|---|---:|---:|---:|---:|---:|---:|
| Free | 100 | 0 | 0 | 0 | 0 | 0 |
| Starter | 250 | 20 | 30 | 40 | 49 | 59 |
| Growth | 500 | 40 | 60 | 79 | 99 | 119 |
| Professional | 1,000 | 72 | 109 | 143 | 179 | 215 |
| Business | 2,500 | 120 | 179 | 239 | 299 | 359 |
| Scale | 5,000 | 200 | 299 | 399 | 499 | 599 |
| Enterprise | 5,001+ | Custom | Custom | Custom | Custom | Custom |

To-do and Journal are optional student products, **US$1 per month each**. Study Plus and GPA launch prices remain unapproved. AI features are Coming soon. The preview provides 30-day synthetic access, never a real recurring purchase.

Configuration/quote UI and pure pricing rules are implemented. Server month-end billing, tokenized cards, PAYG usage, invoices, tax/currency conversion, renewals, cancellation and entitlements remain pending. The previous backend legacy billing routine is unchanged: do not run it for a V2 subscription customer until a reviewed migration/contract router exists.

## Earlier framework (historical reference)


## Reconciled proposal

The two supplied documents describe the same hybrid model. Teachers, tutors, tuition academies and course creators pay a percentage of eligible collected class/course fees. Schools and universities use fixed monthly pricing per active student or an enterprise contract. Optional student and teacher add-ons are a separate product category.

This model is implemented as a **quote preview**, not automatic settlement. The original Frappe monthly billing routine still uses the earlier base-fee/500-student model. No existing bill has been migrated and no provider rate is applied to real transactions.

Sources: [Pricing Strategy Process and Examples](sources/LMS_Pricing_Strategy_Process_and_Examples.docx) and [Revenue Model and How It Works](sources/LMS_Revenue_Model_and_How_It_Works.docx). Both contain replacement glyphs in a few ranges/formulas; ranges such as “5–8” and “501–2,000” were interpreted from surrounding labels and matching examples. The originals are preserved unchanged.

## Provider pricing models

| Model | Audience | Draft rate | Status |
|---|---|---|---|
| Revenue share | Teacher, tutor, academy, online-course creator | Tier A 2.5%, B 3%, C 4%, D 5%, E 7% | Quote calculator implemented; settlement ledger/payout integration pending |
| Institutional | School, university, large institute | Country/contract per-active-student monthly rate | Quote calculator implemented; recurring snapshot/invoice service pending |
| Legacy/custom | Existing earlier-plan customer | Agreed base fee includes 500 active students; LKR 50 per extra student | Kept separate; existing backend billing rule remains |
| Enterprise | Large/custom contract | Negotiated fixed amount, student rate or approved fee | Quoting and approval workflow pending |

The country examples in the documents are commercial references, not economic classifications or automatic permanent assignments. Sri Lanka's revenue-share example is 2.5%; the UAE/Gulf premium example is 7%. A verified billing country and approved commercial policy should suggest a versioned default, with controlled contract overrides. Do not infer a teacher's commercial rate from interface language, nationality or student location.

An account uses one agreed primary model. Do not add institutional per-student billing on top of legacy overage or revenue share unless a specifically reviewed contract requires it.

## Institutional reference rates

| Reference | Rate per active student per month |
|---|---|
| Sri Lanka launch | LKR 100 |
| Emerging market | USD 1 |
| Growth market | USD 2.50 |
| Developed market | USD 5–8 |
| Premium Gulf | Up to USD 10 or an enterprise quote |

The documents allow **up to** 10% discount for 501–2,000 students and **up to** 20% for 2,001–10,000. Discounts are not automatically granted by the calculator. Above 10,000 requires an enterprise quote. Approved discount scope must be recorded: the demo applies it to the entire monthly subtotal. Progressive/marginal slabs are not assumed.

Working active-student definition: one distinct enabled Student membership in a provider's billing period snapshot, counted once even across multiple classes. A login-based or paid-enrollment-based definition would change the invoice and needs an explicit contract decision. Snapshot date, mid-cycle joins/removals, proration and duplicate global identities must be agreed before production.

## Student products

| Product | Included | Commercial treatment |
|---|---|---|
| Study essentials | Countdown, stopwatch, breaks, quiet garden, cozy/dark theme, encouragement and pause controls | Free |
| Study Plus | Three original synthesized soundscapes, premium blossom/rainy/moonlit wallpapers, cute theme and extra profile accent colors | Optional monthly subscription; price configurable and not yet approved |
| GPA calculator | Credit-weighted planning and what-if scenarios | Separate optional student add-on; price and billing cadence not yet approved |

Published grades are readable without GPA purchase. Course materials remain subject to their course's enrollment/payment rules. Study Plus does not unlock classes or alter grades. The preview simulates 30 days of Study Plus for the selected demo account, with no card, charge, subscription contract or renewal. Ending demo access immediately relocks premium study features while leaving the free timer and saved sessions.

Study Plus preferences and entitlement live in this browser only. They are not secure paid entitlements and cannot be reused for production. Real subscriptions require verified gateway events, a server-owned entitlement with `starts_at`, `current_period_end`, `cancel_at_period_end`, plan/price version and account identity; expiry/refund/cancellation must revoke access. Do not promise recurring card debits until the chosen gateway supports the required flow and it has been tested. A manually renewed paid period is a separate supported design option.

## Teacher add-ons and future packages

AI Quiz remains a separate optional teacher product, with manual quizzes free. Its price, usage allowance, generation cost, model and review workflow remain open. SOUL product guidance is separate from that entitlement.

Starter, Growth and Professional are package concepts in the documents. No exact monthly price or reduced percentage is supplied. Keep them unpublished/configurable until fixed amounts, rates, limits and upgrade/proration rules are approved. School/Enterprise transaction fees are negotiated; a zero fee must be explicit rather than inferred.

## Calculation rules and examples

Use integer minor units and basis points. In the quote preview, LKR/USD/AED/GBP amounts use two decimal places; this is not a universal rule for every currency. Each currency must define its exponent before supporting JPY, KWD, BHD or OMR. Never convert or add different currencies implicitly.

Example: 100 collected payments of LKR 5,000 produce LKR 500,000 gross. At 2.5%, the platform fee is LKR 12,500, leaving LKR 487,500 before any gateway/tax/refund deductions. A USD 10,000 collection at 7% produces USD 700 platform revenue before other adjustments.

Quote identity: `provider balance = gross − refunds − net platform fee − gateway deductions − tax deductions`. The demo assumes user-entered gateway and tax values are deductions, not a legal tax treatment. On a proportional fee-reversal policy, the refund reverses its corresponding platform fee; the original fee and reversal remain separately visible. Actual tax basis, gateway refundability, minimum fees, disputes and negative balances require approved policy. The calculator does not initiate payouts or calculate tax law.

## Production billing process

1. Capture account type, verified billing country, currency and legal billing details.
2. Present an approved versioned quote, including every fee and the renewal/refund terms.
3. Record contract acceptance, effective date and any authorized override with an audit trail.
4. On a verified payment event, atomically snapshot gross, fee rate/version, currency, platform fee and provider/gateway identifiers. Use the provider event as the idempotency key.
5. Record refunds and reversals as new ledger entries; preserve originals. Reconcile settlements and disputes.
6. Issue recurring institution invoices from immutable active-student snapshots. Maintain a distinct ledger for the platform's own student/teacher add-on sales.
7. Report gross, platform fees, gateway fees, taxes, refunds and provider balance separately by customer, country, class, currency and period.

## Open commercial decisions

- Study Plus monthly price, supported countries/currencies, and guardian purchase flow where applicable.
- Whether the earlier 500-included model is legacy-only or available to new custom contracts. Until clarified it remains separate and unchanged.
- Exact Starter/Growth/Professional prices and reduced transaction rates.
- Country-to-tier policy, verification/override authority, tax basis, fee rounding and refund policy.
- Active-student snapshot/proration definition and discount scope.
- Whether collection uses each institute's merchant account or a platform marketplace arrangement. The existing student-invoice adapter alone does not establish split payouts or platform commission collection.

No live charges, payouts, contract changes or new external subscriptions were created while organizing this model.
