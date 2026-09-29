# Searchable profile education levels

The profile editor searches display labels, categories and common aliases. It supports multiple selections, removal and custom local names. Existing comma-separated `grades` values load as selections; the existing authenticated profile API stores them with its 150-character server limit. This change does not claim credential equivalence or alter account permissions.

Coverage includes general education stages, Grades 1–13, Years 1–13, Cambridge, Pearson Edexcel, IB, Sri Lankan exams, UAE pathways, higher education and vocational/lifelong learning. It is a starting catalogue, not an exhaustive registry of every national qualification. Custom entries accommodate other systems without blocking registration or profile updates.

Catalogue sources checked 28 September 2026:

- UNESCO ISCED framework: https://uis.unesco.org/sites/default/files/documents/international-standard-classification-of-education-isced-2011-en.pdf
- Cambridge programmes: https://www.cambridgeinternational.org/programmes-and-qualifications/
- IB programmes: https://ibo.org/programmes
- Pearson qualifications: https://qualifications.pearson.com/en/qualifications.html
- Sri Lanka Department of Examinations: https://www.doenets.lk/news
- UAE Ministry of Education: https://www.moe.gov.ae/en/guides/Pages/Parents-%26-Students-Guide-to-the-Educational-Streams-in-Cycle-3-2025-2026.aspx

Catalogue definitions: `frontend/src/commerce/educationLevels.js`. Review names as providers change their offerings. Do not infer age, admission eligibility or recognition from these self-reported profile values.
