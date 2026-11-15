# Zombie rows (6 of 600)

Every row with verdict `zombie` in `full/o.csv`, with the rule that fired. Hard gates: dead (404/410/unreachable), parked, shutdown notice on the site itself, archived repo, redirect to an unrelated domain, TinySet/Agent-reported shutdown that the own site also confirms. Otherwise a zombie needs structured dated sources on the organisation's own domain or own GitHub repo, all older than 730 days: two independent ones, or one plus zero open jobs and sign-up not working; never social, news or third-party domains, never text-parsed dates, never dates before 2010.

| # | name | URL | what fired | date | evidence URL | evidence on own domain (Y/N) | confidence |
|---|---|---|---|---|---|---|---|
| 1 | RocketGit | https://rocketgit.com | staleness: 2 structured own-domain source(s) (feed, sitemap), newest 2015-01-28, all over 730 days | 2015-01-28 | https://rocketgit.com/sitemap.xml | Y | high |
| 2 | RequestBin.com | https://requestbin.com | hard gate: redirect to an unrelated domain | - | https://pipedream.com/ | Y | high |
| 3 | RunMyJob | https://runmyjob.io | hard gate: redirect to an unrelated domain | - | https://runjob.eu/ | Y | high |
| 4 | Dependabot | https://dependabot.com/ | hard gate: redirect to an unrelated domain | - | https://github.com/security/advanced-security | N | high |
| 5 | pyup.io | https://pyup.io | hard gate: redirect to an unrelated domain | - | https://www.getsafety.com/?utm_source=data&utm_medium=redirect&utm_campaign=data_rd&utm_id=0624&utm_content=marketing | Y | high |
| 6 | logtail.com | https://logtail.com/ | hard gate: redirect to an unrelated domain | - | https://betterstack.com/log-management | Y | high |
