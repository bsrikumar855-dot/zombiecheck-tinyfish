# YC ground-truth validation (500 rows)

Ground truth is YC's own company status (`yc-oss` list): Inactive, Acquired, Active/Public. Batches W12 to S19, companies with a website, seeded sample (seed 42): 250 Inactive, 125 Acquired, 125 Active/Public. Command: `python zombiecheck.py yc500.csv -o yc/o.csv --no-tinyset --agent-budget 20` (Fetch + Search + a 20-row Agent budget, no TinySet). No rule was changed for this test.

## Tool verdict by YC status (count, % of that status)

| YC status (rows) | alive | slowing down | unclear | zombie |
|---|---|---|---|---|
| Inactive (250) | 13 (5.2%) | 67 (26.8%) | 120 (48.0%) | 50 (20.0%) |
| Acquired (125) | 26 (20.8%) | 34 (27.2%) | 44 (35.2%) | 21 (16.8%) |
| Active/Public (125) | 61 (48.8%) | 39 (31.2%) | 21 (16.8%) | 4 (3.2%) |

## Headline numbers

- **(a) Recall:** 50 of 250 Inactive rows called zombie = **20.0%**.
- **(b) Abstain:** 187 of 250 Inactive rows called unclear or slowing down = **74.8%** (unclear 120, slowing down 67). The remaining 13 (5.2%) were called alive.
- **(c) False-zombie rate:** 4 of 125 Active/Public rows called zombie = **3.2%**.
- **(d) Acquired rows:** 65 of 125 were zombie or unclear (21 zombie, 44 unclear); 18 of those were via a redirect to another domain (3 zombie, 15 unclear).

## (c) Every Active/Public row the tool called zombie

| name | URL | YC status | what fired | evidence URL |
|---|---|---|---|---|
| Juno College of Technology | http://junocollege.com | Active | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: Site not found. Well, this is awkward. The site you are looking for is not here. 404 Error. | http://junocollege.com |
| Gamebytes | http://www.gamebytes.io | Active | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: Your connection is not private; net::ERR_CERT_DATE_INVALID | http://www.gamebytes.io |
| Tall Poppy | https://tallpoppy.com | Active | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: error page: tallpoppy.com sent an invalid response. ERR_SSL_PROTOCOL_ERROR | https://tallpoppy.com |
| Helicarrier (prev Buycoins) | https://helicarrier.studio | Active | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: Page not found. Looks like you’ve followed a broken link or entered a URL that doesn’t exist on this sit | https://helicarrier.studio |

## Zombie calls by YC status, with evidence URLs

| name | YC status | reason | evidence URL |
|---|---|---|---|
| California Dreamin | Inactive | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: did not load: www.drinkdreamin.com unexpectedly closed the connection. E | https://www.drinkdreamin.com/ |
| Scanate/Fellow | Inactive | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: Site not found | https://joinfellow.com |
| Fuse | Inactive | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: error page: www.letsfuse.com sent an invalid response. ERR_SSL_PROTOCOL_ | https://www.letsfuse.com/ |
| Zenamins | Inactive | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: 526: Invalid SSL certificate | http://zenamins.com |
| Cartcam | Inactive | domain is parked / for sale | https://cartcam.com/ |
| Threadable | Inactive | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: Not Found | http://threadable.com |
| Cherry | Inactive | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: There's nothing here, yet. | http://www.startcherry.com |
| Start Closing | Inactive | domain is parked / for sale | https://www.atom.com/name/StartClosing |
| Whirl | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/getwhirl.com?utm_source=TDFS_BINNS2&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-binns2_base&traffic_type=TDFS_BINNS2&traffic_id=binns2& |
| Volt Health | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/volthealth.com?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| NextDrop | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/thenextdrop.com?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Prophecy Sciences | Inactive | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: 404 page not found | http://prophecysciences.com |
| PhysioHealth | Inactive | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: error page: net::ERR_CERT_COMMON_NAME_INVALID | https://www.physioh.com |
| Mighty Buildings | Inactive | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: error page: ERR_SSL_VERSION_OR_CIPHER_MISMATCH | https://www.mightybuildings.com |
| ShopWith | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/shopwith.co?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Haiku | Inactive | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: error page: Your connection is not private (net::ERR_CERT_DATE_INVALID) | https://www.haikuforteams.com/ |
| Assorted Bits | Inactive | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: no content | http://youthere.com |
| Capture | Inactive | site says it has shut down / been discontinued | https://www.capture.so/ |
| Yumbin | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/yumbin.com?utm_source=TDFS_BINNS&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-binns_base&traffic_type=TDFS_BINNS&traffic_id=binns& |
| Hipset | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/tracksby.com?utm_source=TDFS_BINNS2&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-binns2_base&traffic_type=TDFS_BINNS2&traffic_id=binns2& |
| Elpha | Inactive | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: error page: et::ERR_CERT_DATE_INVALID | https://elpha.com |
| Path | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/path.me?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| VOIQ | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/voiq.com?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Zergo | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/zergo.com?utm_source=TDFS_BINNS2&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-binns2_base&traffic_type=TDFS_BINNS2&traffic_id=binns2& |
| Looklive | Inactive | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: error page: Attackers might be trying to steal your information from www | https://www.looklive.com/ |
| RideAlong | Inactive | domain is parked / for sale | https://www.getridealong.com/ |
| Sublime Black | Inactive | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: This domain isn't connected to a site | http://sublimeblack.com |
| Mindori | Inactive | site says it has shut down / been discontinued | http://mindori.com/ |
| Rally Tennis | Inactive | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: did not load: ERR_SSL_PROTOCOL_ERROR | https://www.rallytennis.com/ |
| Adventurous Co | Inactive | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: did not load: ERR_SSL_VERSION_OR_CIPHER_MISMATCH | http://adventurous.co |
| Kenota (formerly ExVivo Labs) | Inactive | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: did not load: ERR_CONNECTION_CLOSED | https://kenota.com/ |
| Brace | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/brace.io?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Glider | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/glider.io?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Sunu | Inactive | domain is parked / for sale | https://www.atom.com/name/SUNU |
| Mipos.dev | Inactive | domain is parked / for sale | https://www.mipos.dev/ |
| Coco Controller | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/milkshakelabs.com?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Avalanche | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/useavalanche.com?utm_source=TDFS_BINNS2&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-binns2_base&traffic_type=TDFS_BINNS2&traffic_id=binns2& |
| Envyl | Inactive | domain is parked / for sale | https://www.fruits.co/en/buy/envyl.com |
| Warpdrive by Synthetic Minds | Inactive | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: error page: ERR_SSL_PROTOCOL_ERROR | http://warpdrive.co |
| Anasen | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/anasen.com?utm_source=TDFS_BINNS&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-binns_base&traffic_type=TDFS_BINNS&traffic_id=binns& |
| Booktrope | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/booktrope.com?utm_source=TDFS_BINNS2&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-binns2_base&traffic_type=TDFS_BINNS2&traffic_id=binns2& |
| Move Loot | Inactive | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: 404 There isn't a GitHub Pages site here. | http://moveloot.com |
| Modular Science | Inactive | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: did not load: www.modularscience.com didn’t send any data. ERR_EMPTY_RES | https://www.modularscience.com/ |
| Airmada | Inactive | domain is parked / for sale | https://www.atom.com/name/Airmada |
| Lumineye | Inactive | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: Website Expired. This account has expired. If you are the site o | https://www.lumineye.com |
| VetPronto | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/vetpronto.com?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Aalo | Inactive | domain is parked / for sale | https://www.aalo.co/ |
| Metapacket | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/metapacket.com?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| OSIMple | Inactive | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: 404. That’s an error. The requested URL / was not found on this  | http://osimple.co |
| Bistrobot | Inactive | domain is parked / for sale | https://forsale.godaddy.com/forsale/bistrobot.com?utm_source=TDFS_BINNS2&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-binns2_base&traffic_type=TDFS_BINNS2&traffic_id=binns2& |
| Goodybag | Acquired | domain is parked / for sale | https://forsale.godaddy.com/forsale/goodybag.com?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Dharma Labs | Acquired | domain is parked / for sale | https://forsale.godaddy.com/forsale/dharma.io?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Penny | Acquired | site says it has shut down / been discontinued | https://www.pennyapp.io |
| Wingman | Acquired | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: did not load: ERR_SSL_PROTOCOL_ERROR | https://www.trywingman.com |
| Playment | Acquired | redirects to unrelated telusdigital.com; acquired/merged wording at https://inc42.com/buzz/indian-data-annotation-startup-playment-acquired-by-telus-internation | https://inc42.com/buzz/indian-data-annotation-startup-playment-acquired-by-telus-international/ |
| Wavy | Acquired | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: 404 There isn't a GitHub Pages site here. | http://downloadwavy.com |
| Ribbon Health | Acquired | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: 404 Not Found | http://www.ribbonhealth.com |
| Rocketrip | Acquired | redirects to unrelated tabhi.ai; acquired/merged wording at https://www.businesstravelnewseurope.com/Technology/Rocketrip-acquired-by-Mondee: Rocketrip acquired | https://www.businesstravelnewseurope.com/Technology/Rocketrip-acquired-by-Mondee |
| Kip Health | Acquired | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: did not load: www.hellokip.com sent an invalid response. ERR_SSL_PROTOCO | https://www.hellokip.com/ |
| Fat Llama | Acquired | redirects to unrelated hygglo.com; acquired/merged wording at https://app.dealroom.co/news/note/fat-llama-acquired-by-hygglo-for-41-5m: Fat Llama Acquired by Hy | https://app.dealroom.co/news/note/fat-llama-acquired-by-hygglo-for-41-5m |
| Guilded | Acquired | site says it has shut down / been discontinued | https://www.guilded.gg/ |
| Bitaccess | Acquired | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: There's nothing here, yet. | http://bitaccess.com |
| Actiondesk | Acquired | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: did not load: www.actiondesk.io sent an invalid response. ERR_SSL_PROTOC | https://www.actiondesk.io/ |
| Cloudstitch | Acquired | domain is parked / for sale | https://forsale.godaddy.com/forsale/cloudstitch.com?utm_source=TDFS_DASLNC&utm_medium=parkedpages&utm_campaign=x_corp_tdfs-daslnc_base&traffic_type=TDFS_DASLNC&traffic_id=daslnc& |
| Flinto | Acquired | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: did not load: ERR_SSL_PROTOCOL_ERROR | http://flinto.app |
| ClearBrain | Acquired | domain is parked / for sale | https://www.atom.com/name/ClearBrain |
| URX | Acquired | domain is parked / for sale | https://www.atom.com/name/URX |
| WorkClout | Acquired | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: did not load: This site can’t provide a secure connection. www.workclout | https://www.workclout.com |
| Spire Health | Acquired | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: did not load: This site can’t provide a secure connection. spirehealth.c | https://spirehealth.com/ |
| Searchlight | Acquired | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: did not load: www.searchlight.ai sent an invalid response. ERR_SSL_PROTO | https://www.searchlight.ai/ |
| Bouncer | Acquired | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: did not load: ERR_CONNECTION_CLOSED | https://www.getbouncer.com/ |
| Juno College of Technology | Active | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: Site not found. Well, this is awkward. The site you are looking  | http://junocollege.com |
| Gamebytes | Active | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: Your connection is not private; net::ERR_CERT_DATE_INVALID | http://www.gamebytes.io |
| Tall Poppy | Active | Fetch API could not load the site (fetch_target_unreachable) and a browser also failed: error page: tallpoppy.com sent an invalid response. ERR_SSL_PROTOCOL_ERR | https://tallpoppy.com |
| Helicarrier (prev Buycoins) | Active | Fetch API could not load the site (fetch_page_not_found) and a browser also failed: error page: Page not found. Looks like you’ve followed a broken link or ente | https://helicarrier.studio |

## Notes

- YC's status is a label, not a live check: an `Inactive` company may still have a working website, and an `Active` one may be dormant. Disagreement is not always a tool error.
- Confidence of every row is in `yc/o.csv` (`zc_confidence`).
