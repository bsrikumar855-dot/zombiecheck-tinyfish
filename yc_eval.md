# YC ground-truth validation (500 rows)

Ground truth is YC's own company status (`yc-oss` list): Inactive, Acquired, Active/Public. Batches W12 to S19, companies with a website, seeded sample (seed 42): 250 Inactive, 125 Acquired, 125 Active/Public. Command: `python zombiecheck.py yc500.csv -o yc/o.csv --no-tinyset --agent-budget 20` (Fetch + Search + a 20-row Agent budget, no TinySet). No rule was changed for this test.

## Tool verdict by YC status (count, % of that status)

| YC status (rows) | alive | slowing down | unclear | zombie |
|---|---|---|---|---|
| Inactive (250) | 13 (5.2%) | 67 (26.8%) | 119 (47.6%) | 51 (20.4%) |
| Acquired (125) | 26 (20.8%) | 34 (27.2%) | 43 (34.4%) | 22 (17.6%) |
| Active/Public (125) | 61 (48.8%) | 39 (31.2%) | 21 (16.8%) | 4 (3.2%) |

## Headline numbers

- **(a) Recall:** 51 of 250 Inactive rows called zombie = **20.4%**.
- **(b) Abstain:** 186 of 250 Inactive rows called unclear or slowing down = **74.4%** (unclear 119, slowing down 67). The remaining 13 (5.2%) were called alive.
- **(c) False-zombie rate:** 4 of 125 Active/Public rows called zombie = **3.2%**.
- **(d) Acquired rows:** 65 of 125 were zombie or unclear (22 zombie, 43 unclear); 18 of those were via a redirect to another domain (3 zombie, 15 unclear).

## (c) Every Active/Public row the tool called zombie

| name | URL | YC status | what fired | evidence URL |
|---|---|---|---|---|
| Juno College of Technology | http://junocollege.com | Active | site unreachable (page_not_found 404) | http://junocollege.com |
| Gamebytes | http://www.gamebytes.io | Active | site unreachable (page_not_found 404) | http://www.gamebytes.io |
| Tall Poppy | https://tallpoppy.com | Active | site unreachable (target_unreachable) | https://tallpoppy.com |
| Helicarrier (prev Buycoins) | https://helicarrier.studio | Active | site unreachable (page_not_found 404) | https://helicarrier.studio |

## Zombie calls by YC status, with evidence URLs

| name | YC status | reason | evidence URL |
|---|---|---|---|
| California Dreamin | Inactive | site unreachable (target_unreachable) | https://www.drinkdreamin.com/ |
| Scanate/Fellow | Inactive | site unreachable (page_not_found 404) | https://joinfellow.com |
| Fuse | Inactive | site unreachable (target_unreachable) | https://www.letsfuse.com/ |
| Zenamins | Inactive | site unreachable (page_not_found 404) | http://zenamins.com |
| Cartcam | Inactive | domain is parked / for sale | https://cartcam.com/ |
| Threadable | Inactive | site unreachable (page_not_found 404) | http://threadable.com |
| Cherry | Inactive | site unreachable (page_not_found 404) | http://www.startcherry.com |
| Start Closing | Inactive | domain is parked / for sale | https://www.atom.com/name/StartClosing |
| Whirl | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/getwhirl.com?utm_source=TDFS_BINNS2&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-binns2_base&traffic_type=TDFS_BINNS2&traffic_id=binns2& |
| Volt Health | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/volthealth.com?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| NextDrop | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/thenextdrop.com?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Prophecy Sciences | Inactive | site unreachable (page_not_found 404) | http://prophecysciences.com |
| PhysioHealth | Inactive | site unreachable (target_unreachable) | https://www.physioh.com |
| Mighty Buildings | Inactive | site unreachable (target_unreachable) | https://www.mightybuildings.com |
| ShopWith | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/shopwith.co?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Haiku | Inactive | site unreachable (target_unreachable) | https://www.haikuforteams.com/ |
| Assorted Bits | Inactive | site unreachable (page_not_found 404) | http://youthere.com |
| Capture | Inactive | site says it has shut down / been discontinued | https://www.capture.so/ |
| Yumbin | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/yumbin.com?utm_source=TDFS_BINNS&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-binns_base&traffic_type=TDFS_BINNS&traffic_id=binns& |
| Hipset | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/tracksby.com?utm_source=TDFS_BINNS2&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-binns2_base&traffic_type=TDFS_BINNS2&traffic_id=binns2& |
| Elpha | Inactive | site unreachable (target_unreachable) | https://elpha.com |
| Path | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/path.me?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| VOIQ | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/voiq.com?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Zergo | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/zergo.com?utm_source=TDFS_BINNS2&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-binns2_base&traffic_type=TDFS_BINNS2&traffic_id=binns2& |
| Looklive | Inactive | site unreachable (target_unreachable) | https://www.looklive.com/ |
| RideAlong | Inactive | domain is parked / for sale | https://www.getridealong.com/ |
| Sublime Black | Inactive | site unreachable (page_not_found 404) | http://sublimeblack.com |
| Mindori | Inactive | site says it has shut down / been discontinued | http://mindori.com/ |
| Rally Tennis | Inactive | site unreachable (target_unreachable) | https://www.rallytennis.com/ |
| Adventurous Co | Inactive | site unreachable (target_unreachable) | http://adventurous.co |
| Kenota (formerly ExVivo Labs) | Inactive | site unreachable (target_unreachable) | https://kenota.com/ |
| Brace | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/brace.io?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Glider | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/glider.io?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Restocks | Inactive | site unreachable (page_not_found 404) | https://restocks.io |
| Sunu | Inactive | domain is parked / for sale | https://www.atom.com/name/SUNU |
| Mipos.dev | Inactive | domain is parked / for sale | https://www.mipos.dev/ |
| Coco Controller | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/milkshakelabs.com?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Avalanche | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/useavalanche.com?utm_source=TDFS_BINNS2&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-binns2_base&traffic_type=TDFS_BINNS2&traffic_id=binns2& |
| Envyl | Inactive | domain is parked / for sale | https://www.fruits.co/en/buy/envyl.com |
| Warpdrive by Synthetic Minds | Inactive | site unreachable (target_unreachable) | http://warpdrive.co |
| Anasen | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/anasen.com?utm_source=TDFS_BINNS&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-binns_base&traffic_type=TDFS_BINNS&traffic_id=binns& |
| Booktrope | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/booktrope.com?utm_source=TDFS_BINNS2&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-binns2_base&traffic_type=TDFS_BINNS2&traffic_id=binns2& |
| Move Loot | Inactive | site unreachable (page_not_found 404) | http://moveloot.com |
| Modular Science | Inactive | site unreachable (target_unreachable) | https://www.modularscience.com/ |
| Airmada | Inactive | domain is parked / for sale | https://www.atom.com/name/Airmada |
| Lumineye | Inactive | site unreachable (page_not_found 404) | https://www.lumineye.com |
| VetPronto | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/vetpronto.com?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Aalo | Inactive | domain is parked / for sale | https://www.aalo.co/ |
| Metapacket | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/metapacket.com?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| OSIMple | Inactive | site unreachable (page_not_found 404) | http://osimple.co |
| Bistrobot | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/bistrobot.com?utm_source=TDFS_BINNS2&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-binns2_base&traffic_type=TDFS_BINNS2&traffic_id=binns2& |
| Goodybag | Acquired | domain is parked / for sale | https://forsale.godaddy.com/forsale/goodybag.com?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Dharma Labs | Acquired | domain is parked / for sale | https://forsale.godaddy.com/forsale/dharma.io?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Penny | Acquired | site says it has shut down / been discontinued | https://www.pennyapp.io |
| Wingman | Acquired | site unreachable (target_unreachable) | https://www.trywingman.com |
| Playment | Acquired | redirects to unrelated telusdigital.com; acquired/merged wording at https://inc42.com/buzz/indian-data-annotation-startup-playment-acquired-by-telus-internation | https://inc42.com/buzz/indian-data-annotation-startup-playment-acquired-by-telus-international/ |
| Wavy | Acquired | site unreachable (page_not_found 404) | http://downloadwavy.com |
| Ribbon Health | Acquired | site unreachable (page_not_found 404) | http://www.ribbonhealth.com |
| Rocketrip | Acquired | redirects to unrelated tabhi.ai; acquired/merged wording at https://www.businesstravelnewseurope.com/Technology/Rocketrip-acquired-by-Mondee: Rocketrip acquired | https://www.businesstravelnewseurope.com/Technology/Rocketrip-acquired-by-Mondee |
| Kip Health | Acquired | site unreachable (target_unreachable) | https://www.hellokip.com/ |
| Fat Llama | Acquired | redirects to unrelated hygglo.com; acquired/merged wording at https://app.dealroom.co/news/note/fat-llama-acquired-by-hygglo-for-41-5m: Fat Llama Acquired by Hy | https://app.dealroom.co/news/note/fat-llama-acquired-by-hygglo-for-41-5m |
| Guilded | Acquired | site says it has shut down / been discontinued | https://www.guilded.gg/ |
| Bitaccess | Acquired | site unreachable (page_not_found 404) | http://bitaccess.com |
| Actiondesk | Acquired | site unreachable (target_unreachable) | https://www.actiondesk.io/ |
| Look After My Bills | Acquired | site unreachable (page_not_found 410) | http://www.lookaftermybills.com |
| Cloudstitch | Acquired | domain is parked / for sale | https://forsale.godaddy.com/forsale/cloudstitch.com?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Flinto | Acquired | site unreachable (target_unreachable) | http://flinto.app |
| ClearBrain | Acquired | domain is parked / for sale | https://www.atom.com/name/ClearBrain |
| URX | Acquired | domain is parked / for sale | https://www.atom.com/name/URX |
| WorkClout | Acquired | site unreachable (target_unreachable) | https://www.workclout.com |
| Spire Health | Acquired | site unreachable (target_unreachable) | https://spirehealth.com/ |
| Searchlight | Acquired | site unreachable (target_unreachable) | https://www.searchlight.ai/ |
| Bouncer | Acquired | site unreachable (target_unreachable) | https://www.getbouncer.com/ |
| Juno College of Technology | Active | site unreachable (page_not_found 404) | http://junocollege.com |
| Gamebytes | Active | site unreachable (page_not_found 404) | http://www.gamebytes.io |
| Tall Poppy | Active | site unreachable (target_unreachable) | https://tallpoppy.com |
| Helicarrier (prev Buycoins) | Active | site unreachable (page_not_found 404) | https://helicarrier.studio |

## Notes

- YC's status is a label, not a live check: an `Inactive` company may still have a working website, and an `Active` one may be dormant. Disagreement is not always a tool error.
- Confidence of every row is in `yc/o.csv` (`zc_confidence`).
