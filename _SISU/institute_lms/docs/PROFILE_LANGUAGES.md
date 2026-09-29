# Profile language selector

The profile Languages field supports search, multiple selections, removal and custom entries. Existing comma-separated saved values remain intact. It uses the existing authenticated profile save API and its 150-character limit. This field describes a user's languages; it does not enable interface translations or notification templates.

The bundled catalogue contains 8,039 non-deprecated IANA language entries, including sign languages, historical languages and language groups. Source: https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry (registry file dated 2026-09-17; retrieved 2026-09-28). Private-use ranges and undetermined/multiple/no-content/uncoded placeholders are omitted. Duplicate display names receive their codes as suffixes. Commas in names are replaced by a middle dot to preserve the existing storage format.

Search includes registry aliases and native names where provided by the existing locale catalogue or browser Intl.DisplayNames data. Native names are not available for every entry. Custom entries cover dialects and names absent from the registry. Forty results are rendered initially; Show more adds forty without discarding selections.

Data: frontend/src/commerce/languageCatalog.json. Search: profileLanguages.js. UI: LanguageSelect.vue. Review registry updates before refreshing the data; labels are self-reported and do not certify language proficiency.
