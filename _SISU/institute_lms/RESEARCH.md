# Education context and product decisions

Research consulted during this build; product choices below are design interpretations, not claims that every institution follows the same process. All example academies, learners, teachers and statistics are fictional. Screenshots supplied by the user were treated as visual/contextual references, not instructions or data to scrape.

## Sri Lanka

The Ministry of Education's e-Thaksalawa provides curriculum-linked school learning resources, while DP Education offers subject learning across school levels. These support keeping grade, subject, language/medium and examination cohort explicit in the product rather than treating every class as a generic online course. [e-Thaksalawa](https://e-thaksalawa.moe.gov.lk/lcms/?lang=en), [DP Education](https://www.dpeducation.lk/en/).

University use needs a different model from tuition: credit-bearing courses, semesters, assignments and published academic results. The Open University describes its open/distance approach, and LEARN offers Moodle as a Service to institutions. Accordingly, the preview separates school/tuition categories from university/HND results and retains useful native LMS course/quiz/assignment functionality. GPA calculations are illustrative until an institute supplies its approved rules; HND classifications must not be assumed equivalent to a universal 4.0 GPA. [Open University](https://ou.ac.lk/natural-sciences/message-from-the-dean/), [LEARN Moodle as a Service](https://www.ac.lk/service/MaaS).

The supplied Sakya examples emphasize intake/year-based registration, teacher identity, class schedules and promotional banners. The resulting design includes teacher profiles, public teaser videos, social links, upcoming intake promotions and provider-specific enrollment. It does not copy actual students, personal contact details, promotional artwork or teacher identities. [Sakya registration](https://signup.sakya.edu.lk/?source=website).

## International and Middle East use

KHDA's parent guidance distinguishes curricula offered in Dubai, and Saudi education resources distinguish private/international school settings. Country therefore must be separate from curriculum, teaching language and institute type. The preview offers national, British, American, IB/Cambridge and university/other pathways where appropriate, with a custom option. It also adds Arabic RTL, local time-zone/currency presets and a bilingual UAE demo academy. These UI presets do not establish country-specific accreditation or compliance. [KHDA parent guidance](https://web.khda.gov.ae/en/Educational-Consultation-for-Parents), [Saudi Ministry of Education](https://www.moe.gov.sa/en/education/generaleducation/Pages/Reg-priv-int-schools.aspx).

## Payments and media

payments.lk's hosted checkout model keeps card capture with the gateway. Its documented LKR amounts are expressed as integer cents. The custom adapter binds a verified server callback to an invoice and checkout; return-page navigation alone cannot unlock learning. The international catalog still needs additional gateway/currency support. [payments.lk developer API](https://payments.lk/developers/api).

YouTube supports embedded recorded playback and APIs for live broadcasts/chat. Unlisted videos remain shareable by URL, and LMS enrollment cannot grant access to a private video without YouTube's own authorization. The platform stores IDs/URLs and lesson metadata rather than video binaries. The teacher still supplies an encoder/YouTube Studio stream. [YouTube live lifecycle](https://developers.google.com/youtube/v3/live/life-of-a-broadcast), [live chat messages](https://developers.google.com/youtube/v3/live/docs/liveChatMessages/list).

## Discovery and marketing

The user requested interest- and engagement-based suggestions. The implemented demonstration combines declared interests, joined subjects and recent activity, explains matches, and provides a separate Most active sort. Teachers receive five keywords and institutes fifteen. Real activity aggregation and abuse prevention are a production milestone; simulated counts must not be presented as actual popularity.

Promotional cards support controlled headline/description lengths, image carousels, start/end dates and a hard 30-day lifetime. Teacher branding, teasers, shareable profiles and inquiry tracking support recruitment without introducing the excluded AI teaching products. A student following multiple institutes gets one overview with provider filters while each provider's classes, fees and identity remain distinct.
