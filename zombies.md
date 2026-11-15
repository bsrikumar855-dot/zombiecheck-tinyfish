# Zombie rows (36 of 600)

Every row with verdict `zombie` in `full/o.csv`, with the rule that fired. Hard gates: dead 404/410/unreachable, parked, shutdown notice about the site itself, archived repo, redirect to an unrelated domain, TinySet/Agent-reported shutdown. Otherwise a zombie needs a dated signal from the organisation's own pages older than 730 days (social and third-party news dates never count).

| # | name | URL | what fired | date | evidence URL | confidence |
|---|---|---|---|---|---|---|
| 1 | Active Directory | https://azure.microsoft.com/services/active-directory/ | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2005-09-26 | https://www.microsoft.com/en-us/security/blog/ | high |
| 2 | Active Directory B2C | https://azure.microsoft.com/services/active-directory/external-identities/b2c/ | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2005-09-26 | https://www.microsoft.com/en-us/security/blog/ | high |
| 3 | IBM Cloud | https://www.ibm.com/cloud/free/ | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2024-04-16 | https://www.ibm.com/think | high |
| 4 | Bitbucket | https://bitbucket.org/ | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2023-08-09 | https://www.atlassian.com/blog/bitbucket/ai | high |
| 5 | RocketGit | https://rocketgit.com | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2015-01-28 | https://rocketgit.com/blog | high |
| 6 | Calendarific | https://calendarific.com | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2023-01-09 | https://calendarific.com/news | high |
| 7 | Compare JSON | https://comparejson.com | hard gate: dead site (404/410/unreachable) | - | https://comparejson.com | medium |
| 8 | microlink.io | https://microlink.io/ | staleness: newest own-page dated signal (release / commit-feed date) over 730 days old | 2020-07-05 | https://microlink.io/changelog | medium |
| 9 | Parseur | https://parseur.com | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2017-01-11 | https://parseur.com/blog/ | medium |
| 10 | PDF-API.io | https://pdf-api.io | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2024-10-01 | https://pdf-api.io/en/blog | medium |
| 11 | Pixela | https://pixe.la/ | staleness: newest own-page dated signal (release / commit-feed date) over 730 days old | 2024-08-22 | https://github.com/a-know/Pixela/releases.atom | medium |
| 12 | RequestBin.com | https://requestbin.com | hard gate: redirect to an unrelated domain | - | https://pipedream.com/ | high |
| 13 | Sofodata | https://www.sofodata.com/ | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2020-09-20 | https://www.sofodata.com/blog/ | low |
| 14 | Gemfury | https://gemfury.com | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2018-05-25 | https://gemfury.com/sitemap.xml | medium |
| 15 | Keybase | https://keybase.io/ | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2020-05-07 | https://keybase.io/blog | high |
| 16 | Pendulums | https://pendulums.io/ | staleness: newest own-page dated signal (release / commit-feed date) over 730 days old | 2019-09-30 | https://github.com/Swing-team/pendulums-web-client/commits.atom | medium |
| 17 | Pullflow | https://pullflow.com | staleness: newest own-page dated signal (release / commit-feed date) over 730 days old | 2024-03-20 | https://www.pullflow.com/whats-new | medium |
| 18 | whereby.com | https://whereby.com/ | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2021-07-29 | https://whereby.com/blog/from-prescriptions-to-video-consultations-how-accurx-evolved-in-record-time/ | high |
| 19 | WPJack | https://wpjack.com | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2022-06-08 | https://wpjack.com/blog/ | medium |
| 20 | Supermaven | https://www.supermaven.com/ | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2024-02-22 | https://supermaven.com/blog/introducing-supermaven | medium |
| 21 | houndci.com | https://houndci.com/ | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2021-12-01 | http://help.houndci.com/en/articles/2461415-supported-linters | high |
| 22 | Namae | https://namae.dev/ | staleness: newest own-page dated signal (page date read by Agent browser) over 730 days old | 2020-07-03 | https://dev.to/uetchy/give-your-app-slick-name-with-namae-dev-5c4h | high |
| 23 | tickgit.com | https://www.tickgit.com/ | staleness: newest own-page dated signal (release / commit-feed date) over 730 days old | 2020-06-21 | https://github.com/augmentable-dev/tickgit/commits.atom | high |
| 24 | RunMyJob | https://runmyjob.io | hard gate: redirect to an unrelated domain | - | https://runjob.eu/ | high |
| 25 | checkbot.io | https://www.checkbot.io/ | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2020-01-31 | https://www.checkbot.io/press/#about-the-developer | medium |
| 26 | seotest.me | https://seotest.me/ | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2023-10-23 | https://seotest.me/feed/ | medium |
| 27 | Dependabot | https://dependabot.com/ | hard gate: redirect to an unrelated domain | - | https://github.com/security/advanced-security | high |
| 28 | pyup.io | https://pyup.io | hard gate: redirect to an unrelated domain | - | https://www.getsafety.com/?utm_source=data&utm_medium=redirect&utm_campaign=data_rd&utm_id=0624&utm_content=marketing | high |
| 29 | TestTLS.com | https://testtls.com | hard gate: Agent browser reported shutdown | - | https://x.com/testtls_com/status/1507390224225247233 | high |
| 30 | Virgil Security | https://virgilsecurity.com/ | staleness: newest own-page dated signal (release / commit-feed date) over 730 days old | 2020-03-16 | https://github.com/VirgilSecurity/virgil-iotkit/commits.atom | medium |
| 31 | Engage | https://engage.so/ | hard gate: TinySet-reported shutdown (shut down) | - | https://youtube.com/watch?v=sILG80Oosc8 | medium |
| 32 | scaledrone.com | https://www.scaledrone.com/ | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2020-01-01 | https://www.scaledrone.com/blog/ | medium |
| 33 | webpushr | https://www.webpushr.com/ | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2024-05-21 | https://www.webpushr.com/blog | high |
| 34 | logtail.com | https://logtail.com/ | hard gate: redirect to an unrelated domain | - | https://betterstack.com/log-management | high |
| 35 | logzab.com | https://logzab.com/ | staleness: newest own-page dated signal (blog / changelog / sitemap-feed date) over 730 days old | 2022-10-17 | https://logzab.com/blog/ | medium |
| 36 | instatus.com | https://instatus.com | staleness: newest own-page dated signal (release / commit-feed date) over 730 days old | 2020-10-07 | https://instatus.com/changes | medium |
