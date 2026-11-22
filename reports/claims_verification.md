# Claims verification

Run 2026-11-15T13:26:32.149142+00:00: 874 passed, 258 failed.

| check | result | detail |
|---|---|---|
| weather evaluation flagged retrospective | PASS | RETROSPECTIVE: Open-Meteo Historical Forecast API (stitched short-lead forecasts), 2019+ |
| weather not promoted | PASS | not promoted (rule not met) |
| backtest report states untimed historical lines | PASS |  |
| site performance page labels retrospective benchmark + untimed lines + actual-starter proxy | PASS |  |
| site performance page shows weather inputs as RETROSPECTIVE | PASS |  |
| methodology page documents approximations | PASS |  |
| API key absent from repository, logs, site, snapshots and backup | PASS | 13195 files checked |
| The Odds API snapshots contain point values only (no prices) | PASS | 200 snapshots |
| The Odds API lines retrieved and provider-updated before kickoff and before the forecast cutoff | PASS | 3046 game forecasts |
| stored pick labels match the published rule | PASS | 4487 stored picks |
| model pick = version chosen by the rule in force (24 h before kickoff from 21 Oct 2026, from the stats-only line; original-pick from 1 Oct, final-pregame before), with that version's own labels, line and stats-only numbers | PASS | 118 locked picks |
| publication labels of the projected-winner and model-pick versions match the evidence | PASS |  |
| graded: winner and margin error from the final pregame version, model pick from the locked version (both recomputed from the release files) | PASS | 105 graded |
| picks without a stored label are flagged retrospectively derived | PASS |  |
| weekly results tables equal the summary recomputed from their games, and records add up | PASS |  |
| live head-to-head (Performance page) equals the comparison recomputed from each week's games | PASS | 8 weeks |
| game pages show no internal codes or player IDs | PASS | 272 pages clean |
| GitHub push time matches API: rel_20260924T232247Z.json | PASS | 2026-09-25T00:31:03Z a28b4275ad |
| publication not before generation: rel_20260924T232247Z.json | PASS |  |
| GitHub push time matches API: rel_20260924T235129Z.json | PASS | 2026-09-25T00:31:03Z a28b4275ad |
| publication not before generation: rel_20260924T235129Z.json | PASS |  |
| GitHub push time matches API: rel_20260925T000247Z.json | PASS | 2026-09-25T00:31:03Z a28b4275ad |
| publication not before generation: rel_20260925T000247Z.json | PASS |  |
| GitHub push time matches API: rel_20260925T011000Z.json | PASS | 2026-09-25T01:12:19Z 612594caa6 |
| publication not before generation: rel_20260925T011000Z.json | PASS |  |
| GitHub push time matches API: rel_20260925T015111Z.json | PASS | 2026-09-25T01:55:20Z fa27e56aaa |
| publication not before generation: rel_20260925T015111Z.json | PASS |  |
| GitHub push time matches API: rel_20260925T015951Z.json | PASS | 2026-09-25T01:59:59Z 15919f6d9f |
| publication not before generation: rel_20260925T015951Z.json | PASS |  |
| GitHub push time matches API: rel_20260925T021501Z.json | PASS | 2026-09-25T02:15:09Z bf11622430 |
| publication not before generation: rel_20260925T021501Z.json | PASS |  |
| GitHub push time matches API: rel_20260925T051555Z.json | PASS | 2026-09-25T05:16:02Z 6cc2b8d89e |
| publication not before generation: rel_20260925T051555Z.json | PASS |  |
| GitHub push time matches API: rel_20260925T061553Z.json | PASS | 2026-09-25T06:16:01Z 6ba7b55869 |
| publication not before generation: rel_20260925T061553Z.json | PASS |  |
| GitHub push time matches API: rel_20260925T121558Z.json | PASS | 2026-09-25T12:16:07Z c9a7f56dea |
| publication not before generation: rel_20260925T121558Z.json | PASS |  |
| GitHub push time matches API: rel_20260925T131600Z.json | PASS | 2026-09-25T13:16:10Z 1d4c50244a |
| publication not before generation: rel_20260925T131600Z.json | PASS |  |
| GitHub push time matches API: rel_20260925T132351Z.json | PASS | 2026-09-25T13:24:01Z a5693dbf7c |
| publication not before generation: rel_20260925T132351Z.json | PASS |  |
| GitHub push time matches API: rel_20260925T194611Z.json | PASS | 2026-09-25T19:46:21Z 38149aefe1 |
| publication not before generation: rel_20260925T194611Z.json | PASS |  |
| GitHub push time matches API: rel_20260926T103448Z.json | PASS | 2026-09-26T10:35:01Z a8a9723886 |
| publication not before generation: rel_20260926T103448Z.json | PASS |  |
| GitHub push time matches API: rel_20260926T164605Z.json | PASS | 2026-09-26T16:46:13Z c455f9643c |
| publication not before generation: rel_20260926T164605Z.json | PASS |  |
| GitHub push time matches API: rel_20260926T224614Z.json | PASS | 2026-09-26T22:46:23Z aa9e2cc196 |
| publication not before generation: rel_20260926T224614Z.json | PASS |  |
| GitHub push time matches API: rel_20260927T051547Z.json | PASS | 2026-09-27T05:15:53Z 8cc74b7e75 |
| publication not before generation: rel_20260927T051547Z.json | PASS |  |
| GitHub push time matches API: rel_20260927T061550Z.json | PASS | 2026-09-27T06:15:56Z b37692fef4 |
| publication not before generation: rel_20260927T061550Z.json | PASS |  |
| GitHub push time matches API: rel_20260927T114559Z.json | PASS | 2026-09-27T11:46:07Z 3e21e8a1c2 |
| publication not before generation: rel_20260927T114559Z.json | PASS |  |
| GitHub push time matches API: rel_20260927T154559Z.json | PASS | 2026-09-27T15:46:08Z b476655c2c |
| publication not before generation: rel_20260927T154559Z.json | PASS |  |
| GitHub push time matches API: rel_20260927T161549Z.json | PASS | 2026-09-27T16:15:56Z 6a62a4c95d |
| publication not before generation: rel_20260927T161549Z.json | PASS |  |
| GitHub push time matches API: rel_20260927T164557Z.json | PASS | 2026-09-27T16:46:05Z 0f1265c901 |
| publication not before generation: rel_20260927T164557Z.json | PASS |  |
| GitHub push time matches API: rel_20260927T184611Z.json | PASS | 2026-09-27T18:46:20Z b6ecfbf1df |
| publication not before generation: rel_20260927T184611Z.json | PASS |  |
| GitHub push time matches API: rel_20260927T191559Z.json | PASS | 2026-09-27T19:16:08Z c9ae4855f8 |
| publication not before generation: rel_20260927T191559Z.json | PASS |  |
| GitHub push time matches API: rel_20260927T194601Z.json | PASS | 2026-09-27T19:46:10Z 540cd15091 |
| publication not before generation: rel_20260927T194601Z.json | PASS |  |
| GitHub push time matches API: rel_20260927T224554Z.json | PASS | 2026-09-27T22:46:01Z bebbe42191 |
| publication not before generation: rel_20260927T224554Z.json | PASS |  |
| GitHub push time matches API: rel_20260927T234556Z.json | PASS | 2026-09-27T23:46:04Z e2a7de4ab4 |
| publication not before generation: rel_20260927T234556Z.json | PASS |  |
| GitHub push time matches API: rel_20260928T051551Z.json | PASS | 2026-09-28T05:15:59Z df06b2fa8c |
| publication not before generation: rel_20260928T051551Z.json | PASS |  |
| GitHub push time matches API: rel_20260928T061549Z.json | PASS | 2026-09-28T06:15:57Z 0def1d7cea |
| publication not before generation: rel_20260928T061549Z.json | PASS |  |
| GitHub push time matches API: rel_20260928T081553Z.json | PASS | 2026-09-28T08:16:01Z 84b63a3d3c |
| publication not before generation: rel_20260928T081553Z.json | PASS |  |
| GitHub push time matches API: rel_20260928T084549Z.json | PASS | 2026-09-28T08:45:57Z bec9dba80b |
| publication not before generation: rel_20260928T084549Z.json | PASS |  |
| GitHub push time matches API: rel_20260928T124550Z.json | PASS | 2026-09-28T12:45:59Z facebd7aa4 |
| publication not before generation: rel_20260928T124550Z.json | PASS |  |
| GitHub push time matches API: rel_20260928T181556Z.json | PASS | 2026-09-28T18:16:04Z d28edfbaaa |
| publication not before generation: rel_20260928T181556Z.json | PASS |  |
| GitHub push time matches API: rel_20260928T224603Z.json | PASS | 2026-09-28T22:46:12Z a9789e2c98 |
| publication not before generation: rel_20260928T224603Z.json | PASS |  |
| GitHub push time matches API: rel_20260928T231615Z.json | PASS | 2026-09-28T23:16:22Z ff4af4c085 |
| publication not before generation: rel_20260928T231615Z.json | PASS |  |
| GitHub push time matches API: rel_20260928T233941Z.json | PASS | 2026-09-28T23:39:49Z 49a03a6dac |
| publication not before generation: rel_20260928T233941Z.json | PASS |  |
| GitHub push time matches API: rel_20260929T001605Z.json | PASS | 2026-09-29T00:16:13Z 79f4da0891 |
| publication not before generation: rel_20260929T001605Z.json | PASS |  |
| GitHub push time matches API: rel_20260929T034601Z.json | PASS | 2026-09-29T03:46:09Z 1f0f4bd817 |
| publication not before generation: rel_20260929T034601Z.json | PASS |  |
| GitHub push time matches API: rel_20260929T044550Z.json | PASS | 2026-09-29T04:45:59Z 97aa9a5d52 |
| publication not before generation: rel_20260929T044550Z.json | PASS |  |
| GitHub push time matches API: rel_20260929T054551Z.json | PASS | 2026-09-29T05:45:58Z af349041c5 |
| publication not before generation: rel_20260929T054551Z.json | PASS |  |
| GitHub push time matches API: rel_20260929T061550Z.json | PASS | 2026-09-29T06:15:58Z 96c81e191a |
| publication not before generation: rel_20260929T061550Z.json | PASS |  |
| GitHub push time matches API: rel_20260929T121551Z.json | PASS | 2026-09-29T12:16:00Z 52e07f9f8a |
| publication not before generation: rel_20260929T121551Z.json | PASS |  |
| GitHub push time matches API: rel_20260929T141558Z.json | PASS | 2026-09-29T14:16:06Z 9dd37e02b6 |
| publication not before generation: rel_20260929T141558Z.json | PASS |  |
| GitHub push time matches API: rel_20260929T181556Z.json | PASS | 2026-09-29T18:16:05Z cec75ba654 |
| publication not before generation: rel_20260929T181556Z.json | PASS |  |
| GitHub push time matches API: rel_20260930T001556Z.json | PASS | 2026-09-30T00:16:06Z 5026eb7e8a |
| publication not before generation: rel_20260930T001556Z.json | PASS |  |
| GitHub push time matches API: rel_20260930T134704Z.json | PASS | 2026-09-30T13:47:19Z 1aaf1386fe |
| publication not before generation: rel_20260930T134704Z.json | PASS |  |
| GitHub push time matches API: rel_20260930T201609Z.json | PASS | 2026-09-30T20:16:22Z 2187216dda |
| publication not before generation: rel_20260930T201609Z.json | PASS |  |
| GitHub push time matches API: rel_20261001T021611Z.json | PASS | 2026-10-01T02:16:22Z fed90153d0 |
| publication not before generation: rel_20261001T021611Z.json | PASS |  |
| GitHub push time matches API: rel_20261001T125953Z.json | PASS | 2026-10-01T13:00:05Z 6ec4699a78 |
| publication not before generation: rel_20261001T125953Z.json | PASS |  |
| GitHub push time matches API: rel_20261001T134555Z.json | PASS | 2026-10-01T13:46:05Z a6dec7d15b |
| publication not before generation: rel_20261001T134555Z.json | PASS |  |
| GitHub push time matches API: rel_20261001T144623Z.json | PASS | 2026-10-01T14:46:35Z ea596718ad |
| publication not before generation: rel_20261001T144623Z.json | PASS |  |
| GitHub push time matches API: rel_20261001T171604Z.json | PASS | 2026-10-01T17:16:15Z 8ef87ae7d9 |
| publication not before generation: rel_20261001T171604Z.json | PASS |  |
| GitHub push time matches API: rel_20261001T191750Z.json | PASS | 2026-10-01T19:18:10Z 543d13e6a1 |
| publication not before generation: rel_20261001T191750Z.json | PASS |  |
| GitHub push time matches API: rel_20261001T201658Z.json | PASS | 2026-10-01T20:17:17Z 90a5b0252b |
| publication not before generation: rel_20261001T201658Z.json | PASS |  |
| GitHub push time matches API: rel_20261001T204602Z.json | PASS | 2026-10-01T20:46:13Z 8da2924fab |
| publication not before generation: rel_20261001T204602Z.json | PASS |  |
| GitHub push time matches API: rel_20261001T224758Z.json | PASS | 2026-10-01T22:48:10Z 359e3e697f |
| publication not before generation: rel_20261001T224758Z.json | PASS |  |
| GitHub push time matches API: rel_20261001T231600Z.json | PASS | 2026-10-01T23:16:10Z 35ded03065 |
| publication not before generation: rel_20261001T231600Z.json | PASS |  |
| GitHub push time matches API: rel_20261001T234558Z.json | PASS | 2026-10-01T23:46:08Z 8848c5e4c2 |
| publication not before generation: rel_20261001T234558Z.json | PASS |  |
| GitHub push time matches API: rel_20261002T013537Z.json | PASS | 2026-10-02T01:35:47Z bc077533c2 |
| publication not before generation: rel_20261002T013537Z.json | PASS |  |
| GitHub push time matches API: rel_20261002T061555Z.json | PASS | 2026-10-02T06:16:04Z 2e00df2c8b |
| publication not before generation: rel_20261002T061555Z.json | PASS |  |
| GitHub push time matches API: rel_20261002T121553Z.json | PASS | 2026-10-02T12:16:03Z 8095b92803 |
| publication not before generation: rel_20261002T121553Z.json | PASS |  |
| GitHub push time matches API: rel_20261002T184600Z.json | PASS | 2026-10-02T18:46:11Z abd640326f |
| publication not before generation: rel_20261002T184600Z.json | PASS |  |
| GitHub push time matches API: rel_20261003T131647Z.json | PASS | 2026-10-03T13:17:04Z b88289c189 |
| publication not before generation: rel_20261003T131647Z.json | PASS |  |
| GitHub push time matches API: rel_20261003T191642Z.json | PASS | 2026-10-03T19:16:59Z 15afe69da3 |
| publication not before generation: rel_20261003T191642Z.json | PASS |  |
| GitHub push time matches API: rel_20261004T014555Z.json | PASS | 2026-10-04T01:46:05Z 712dcced38 |
| publication not before generation: rel_20261004T014555Z.json | PASS |  |
| GitHub push time matches API: rel_20261004T122417Z.json | PASS | 2026-10-04T12:24:32Z a2877a856f |
| publication not before generation: rel_20261004T122417Z.json | PASS |  |
| GitHub push time matches API: rel_20261004T124623Z.json | PASS | 2026-10-04T12:46:34Z 561e851b1c |
| publication not before generation: rel_20261004T124623Z.json | PASS |  |
| GitHub push time matches API: rel_20261004T131557Z.json | PASS | 2026-10-04T13:16:07Z f9919bbbf8 |
| publication not before generation: rel_20261004T131557Z.json | PASS |  |
| GitHub push time matches API: rel_20261004T154608Z.json | PASS | 2026-10-04T15:46:19Z d54c6ff5cc |
| publication not before generation: rel_20261004T154608Z.json | PASS |  |
| GitHub push time matches API: rel_20261004T161557Z.json | PASS | 2026-10-04T16:16:07Z 2bf4ee6b8c |
| publication not before generation: rel_20261004T161557Z.json | PASS |  |
| GitHub push time matches API: rel_20261004T164554Z.json | PASS | 2026-10-04T16:46:03Z 0ab7a6c0c7 |
| publication not before generation: rel_20261004T164554Z.json | PASS |  |
| GitHub push time matches API: rel_20261004T191617Z.json | PASS | 2026-10-04T19:16:29Z b517e00225 |
| publication not before generation: rel_20261004T191617Z.json | PASS |  |
| GitHub push time matches API: rel_20261004T194555Z.json | PASS | 2026-10-04T19:46:03Z 0e9943d604 |
| publication not before generation: rel_20261004T194555Z.json | PASS |  |
| GitHub push time matches API: rel_20261004T224614Z.json | PASS | 2026-10-04T22:46:26Z e470bb326e |
| publication not before generation: rel_20261004T224614Z.json | PASS |  |
| GitHub push time matches API: rel_20261004T234600Z.json | PASS | 2026-10-04T23:46:12Z 9d01835ee2 |
| publication not before generation: rel_20261004T234600Z.json | PASS |  |
| GitHub push time matches API: rel_20261005T101630Z.json | PASS | 2026-10-05T10:16:41Z 7f197e4806 |
| publication not before generation: rel_20261005T101630Z.json | PASS |  |
| GitHub push time matches API: rel_20261005T124556Z.json | PASS | 2026-10-05T12:46:05Z 9036392732 |
| publication not before generation: rel_20261005T124556Z.json | PASS |  |
| GitHub push time matches API: rel_20261005T224631Z.json | PASS | 2026-10-05T22:46:43Z 3b0a2b9088 |
| publication not before generation: rel_20261005T224631Z.json | PASS |  |
| GitHub push time matches API: rel_20261005T231609Z.json | PASS | 2026-10-05T23:16:18Z f3825afbda |
| publication not before generation: rel_20261005T231609Z.json | PASS |  |
| GitHub push time matches API: rel_20261006T204330Z.json | PASS | 2026-10-06T20:43:40Z 6237fd9e0c |
| publication not before generation: rel_20261006T204330Z.json | PASS |  |
| GitHub push time matches API: rel_20261007T004623Z.json | PASS | 2026-10-07T00:46:38Z dc905f6f8b |
| publication not before generation: rel_20261007T004623Z.json | PASS |  |
| GitHub push time matches API: rel_20261007T122817Z.json | PASS | 2026-10-07T12:28:31Z e1ba47bd04 |
| publication not before generation: rel_20261007T122817Z.json | PASS |  |
| GitHub push time matches API: rel_20261007T184603Z.json | PASS | 2026-10-07T18:46:14Z 6b5d5a6397 |
| publication not before generation: rel_20261007T184603Z.json | PASS |  |
| GitHub push time matches API: rel_20261008T004618Z.json | PASS | 2026-10-08T00:46:29Z b08cdc4d27 |
| publication not before generation: rel_20261008T004618Z.json | PASS |  |
| GitHub push time matches API: rel_20261008T061608Z.json | PASS | 2026-10-08T06:16:19Z ca06699783 |
| publication not before generation: rel_20261008T061608Z.json | PASS |  |
| GitHub push time matches API: rel_20261008T064615Z.json | PASS | 2026-10-08T06:46:26Z 49f79169a0 |
| publication not before generation: rel_20261008T064615Z.json | PASS |  |
| GitHub push time matches API: rel_20261008T124712Z.json | PASS | 2026-10-08T12:47:31Z 24164bd7ce |
| publication not before generation: rel_20261008T124712Z.json | PASS |  |
| GitHub push time matches API: rel_20261008T134559Z.json | PASS | 2026-10-08T13:46:11Z 01f40cb224 |
| publication not before generation: rel_20261008T134559Z.json | PASS |  |
| GitHub push time matches API: rel_20261008T171703Z.json | PASS | 2026-10-08T17:17:21Z 0bb5721f32 |
| publication not before generation: rel_20261008T171703Z.json | PASS |  |
| GitHub push time matches API: rel_20261008T191602Z.json | PASS | 2026-10-08T19:16:15Z c3b7c0cbb6 |
| publication not before generation: rel_20261008T191602Z.json | PASS |  |
| GitHub push time matches API: rel_20261008T201601Z.json | PASS | 2026-10-08T20:16:14Z 3cbb47e87b |
| publication not before generation: rel_20261008T201601Z.json | PASS |  |
| GitHub push time matches API: rel_20261008T204618Z.json | PASS | 2026-10-08T20:46:33Z 15d81808fe |
| publication not before generation: rel_20261008T204618Z.json | PASS |  |
| GitHub push time matches API: rel_20261008T224607Z.json | PASS | 2026-10-08T22:46:21Z 3ceefc89ee |
| publication not before generation: rel_20261008T224607Z.json | PASS |  |
| GitHub push time matches API: rel_20261008T231658Z.json | PASS | 2026-10-08T23:17:20Z b1ac583021 |
| publication not before generation: rel_20261008T231658Z.json | PASS |  |
| GitHub push time matches API: rel_20261008T234642Z.json | PASS | 2026-10-08T23:48:59Z 0259a75355 |
| publication not before generation: rel_20261008T234642Z.json | PASS |  |
| GitHub push time matches API: rel_20261009T004652Z.json | PASS | 2026-10-09T00:47:09Z 3c06544464 |
| publication not before generation: rel_20261009T004652Z.json | PASS |  |
| GitHub push time matches API: rel_20261009T124551Z.json | PASS | 2026-10-09T12:46:05Z f73c464b4a |
| publication not before generation: rel_20261009T124551Z.json | PASS |  |
| GitHub push time matches API: rel_20261009T184623Z.json | PASS | 2026-10-09T18:46:39Z 7d937b4911 |
| publication not before generation: rel_20261009T184623Z.json | PASS |  |
| GitHub push time matches API: rel_20261010T001609Z.json | PASS | 2026-10-10T00:16:22Z 1c1d0e98fa |
| publication not before generation: rel_20261010T001609Z.json | PASS |  |
| GitHub push time matches API: rel_20261010T004631Z.json | PASS | 2026-10-10T00:46:45Z 244f44a795 |
| publication not before generation: rel_20261010T004631Z.json | PASS |  |
| GitHub push time matches API: rel_20261010T061555Z.json | PASS | 2026-10-10T06:16:05Z a518a87886 |
| publication not before generation: rel_20261010T061555Z.json | PASS |  |
| GitHub push time matches API: rel_20261010T071555Z.json | PASS | 2026-10-10T07:16:05Z 216c9d7793 |
| publication not before generation: rel_20261010T071555Z.json | PASS |  |
| GitHub push time matches API: rel_20261010T131625Z.json | PASS | 2026-10-10T13:16:38Z 7d559b8909 |
| publication not before generation: rel_20261010T131625Z.json | PASS |  |
| GitHub push time matches API: rel_20261010T194716Z.json | PASS | 2026-10-10T19:47:35Z 4a376ca910 |
| publication not before generation: rel_20261010T194716Z.json | PASS |  |
| GitHub push time matches API: rel_20261011T021619Z.json | PASS | 2026-10-11T02:16:33Z dae726efb6 |
| publication not before generation: rel_20261011T021619Z.json | PASS |  |
| GitHub push time matches API: rel_20261011T124515Z.json | PASS | 2026-10-11T12:45:29Z df25cc2df1 |
| publication not before generation: rel_20261011T124515Z.json | PASS |  |
| GitHub push time matches API: rel_20261011T154620Z.json | PASS | 2026-10-11T15:46:34Z b026c07b95 |
| publication not before generation: rel_20261011T154620Z.json | PASS |  |
| GitHub push time matches API: rel_20261011T161559Z.json | PASS | 2026-10-11T16:16:12Z 5719d6aab8 |
| publication not before generation: rel_20261011T161559Z.json | PASS |  |
| GitHub push time matches API: rel_20261011T164559Z.json | PASS | 2026-10-11T16:46:12Z eb3a045039 |
| publication not before generation: rel_20261011T164559Z.json | PASS |  |
| GitHub push time matches API: rel_20261012T085723Z.json | PASS | 2026-10-12T08:57:37Z ce5e3e385e |
| publication not before generation: rel_20261012T085723Z.json | PASS |  |
| GitHub push time matches API: rel_20261012T124559Z.json | PASS | 2026-10-12T12:46:11Z a6f38aeb96 |
| publication not before generation: rel_20261012T124559Z.json | PASS |  |
| GitHub push time matches API: rel_20261012T233818Z.json | PASS | 2026-10-12T23:38:30Z 648bfe7bc1 |
| publication not before generation: rel_20261012T233818Z.json | PASS |  |
| GitHub push time matches API: rel_20261013T170040Z.json | PASS | 2026-10-13T17:00:53Z da0203ce55 |
| publication not before generation: rel_20261013T170040Z.json | PASS |  |
| GitHub push time matches API: rel_20261013T181602Z.json | PASS | 2026-10-13T18:16:14Z bafb8fbf69 |
| publication not before generation: rel_20261013T181602Z.json | PASS |  |
| GitHub push time matches API: rel_20261014T004602Z.json | PASS | 2026-10-14T00:46:15Z cc6e131097 |
| publication not before generation: rel_20261014T004602Z.json | PASS |  |
| GitHub push time matches API: rel_20261014T061628Z.json | PASS | 2026-10-14T06:16:42Z 645bc9ae23 |
| publication not before generation: rel_20261014T061628Z.json | PASS |  |
| GitHub push time matches API: rel_20261014T071558Z.json | PASS | 2026-10-14T07:16:11Z a755335084 |
| publication not before generation: rel_20261014T071558Z.json | PASS |  |
| GitHub push time matches API: rel_20261014T144718Z.json | PASS | 2026-10-14T14:47:37Z b5e3d883c2 |
| publication not before generation: rel_20261014T144718Z.json | PASS |  |
| GitHub push time matches API: rel_20261014T211613Z.json | PASS | 2026-10-14T21:16:29Z 1802073127 |
| publication not before generation: rel_20261014T211613Z.json | PASS |  |
| GitHub push time matches API: rel_20261015T150557Z.json | PASS | 2026-10-15T15:06:13Z 10fa9eacd2 |
| publication not before generation: rel_20261015T150557Z.json | PASS |  |
| GitHub push time matches API: rel_20261015T171615Z.json | PASS | 2026-10-15T17:16:32Z 4d3a9d65f4 |
| publication not before generation: rel_20261015T171615Z.json | PASS |  |
| GitHub push time matches API: rel_20261015T201620Z.json | PASS | 2026-10-15T20:16:38Z b6885a4ae2 |
| publication not before generation: rel_20261015T201620Z.json | PASS |  |
| GitHub push time matches API: rel_20261015T204633Z.json | PASS | 2026-10-15T20:46:50Z a588bfb782 |
| publication not before generation: rel_20261015T204633Z.json | PASS |  |
| GitHub push time matches API: rel_20261015T211623Z.json | PASS | 2026-10-15T21:16:41Z a0be09d01c |
| publication not before generation: rel_20261015T211623Z.json | PASS |  |
| GitHub push time matches API: rel_20261015T231654Z.json | PASS | 2026-10-15T23:17:13Z 9de6b859e3 |
| publication not before generation: rel_20261015T231654Z.json | PASS |  |
| GitHub push time matches API: rel_20261016T004656Z.json | PASS | 2026-10-16T00:47:13Z b23cdf860d |
| publication not before generation: rel_20261016T004656Z.json | PASS |  |
| GitHub push time matches API: rel_20261016T160625Z.json | PASS | 2026-10-16T16:06:39Z 76cdb9e352 |
| publication not before generation: rel_20261016T160625Z.json | PASS |  |
| GitHub push time matches API: rel_20261016T221640Z.json | PASS | 2026-10-16T22:16:55Z aceb43501b |
| publication not before generation: rel_20261016T221640Z.json | PASS |  |
| GitHub push time matches API: rel_20261017T001700Z.json | PASS | 2026-10-17T00:17:18Z 9227f20c81 |
| publication not before generation: rel_20261017T001700Z.json | PASS |  |
| GitHub push time matches API: rel_20261017T044625Z.json | PASS | 2026-10-17T04:46:38Z 559a7f82d7 |
| publication not before generation: rel_20261017T044625Z.json | PASS |  |
| GitHub push time matches API: rel_20261017T061658Z.json | PASS | 2026-10-17T06:17:15Z 1223487475 |
| publication not before generation: rel_20261017T061658Z.json | PASS |  |
| GitHub push time matches API: rel_20261017T171645Z.json | PASS | 2026-10-17T17:17:00Z de07fa7f3a |
| publication not before generation: rel_20261017T171645Z.json | PASS |  |
| GitHub push time matches API: rel_20261017T231726Z.json | PASS | 2026-10-17T23:17:43Z c22de7cf29 |
| publication not before generation: rel_20261017T231726Z.json | PASS |  |
| GitHub push time matches API: rel_20261018T054611Z.json | PASS | 2026-10-18T05:46:23Z 8a012e6d47 |
| publication not before generation: rel_20261018T054611Z.json | PASS |  |
| GitHub push time matches API: rel_20261018T061600Z.json | PASS | 2026-10-18T06:16:13Z bbca796fc6 |
| publication not before generation: rel_20261018T061600Z.json | PASS |  |
| GitHub push time matches API: rel_20261018T114641Z.json | PASS | 2026-10-18T11:46:54Z 98d910b263 |
| publication not before generation: rel_20261018T114641Z.json | PASS |  |
| GitHub push time matches API: rel_20261018T124607Z.json | PASS | 2026-10-18T12:46:20Z 63f203a56e |
| publication not before generation: rel_20261018T124607Z.json | PASS |  |
| GitHub push time matches API: rel_20261018T154628Z.json | PASS | 2026-10-18T15:47:05Z 9468e09fdd |
| publication not before generation: rel_20261018T154628Z.json | PASS |  |
| GitHub push time matches API: rel_20261018T161720Z.json | PASS | 2026-10-18T16:17:39Z 1e7c3c3a82 |
| publication not before generation: rel_20261018T161720Z.json | PASS |  |
| GitHub push time matches API: rel_20261018T164705Z.json | PASS | 2026-10-18T16:47:20Z def8a56310 |
| publication not before generation: rel_20261018T164705Z.json | PASS |  |
| GitHub push time matches API: rel_20261018T184614Z.json | PASS | 2026-10-18T18:46:28Z f5db9699fd |
| publication not before generation: rel_20261018T184614Z.json | PASS |  |
| GitHub push time matches API: rel_20261018T191608Z.json | PASS | 2026-10-18T19:16:23Z d8c16e35a7 |
| publication not before generation: rel_20261018T191608Z.json | PASS |  |
| GitHub push time matches API: rel_20261018T194614Z.json | PASS | 2026-10-18T19:46:29Z 428e32a024 |
| publication not before generation: rel_20261018T194614Z.json | PASS |  |
| GitHub push time matches API: rel_20261018T224605Z.json | PASS | 2026-10-18T22:46:20Z bb82e81bf5 |
| publication not before generation: rel_20261018T224605Z.json | PASS |  |
| GitHub push time matches API: rel_20261018T234602Z.json | PASS | 2026-10-18T23:46:14Z 18b7bff66c |
| publication not before generation: rel_20261018T234602Z.json | PASS |  |
| GitHub push time matches API: rel_20261019T164729Z.json | PASS | 2026-10-19T16:47:44Z 222b861df3 |
| publication not before generation: rel_20261019T164729Z.json | PASS |  |
| GitHub push time matches API: rel_20261019T231606Z.json | PASS | 2026-10-19T23:16:20Z 14dad4ac4a |
| publication not before generation: rel_20261019T231606Z.json | PASS |  |
| GitHub push time matches API: rel_20261019T234612Z.json | PASS | 2026-10-19T23:46:27Z 959e7d39cb |
| publication not before generation: rel_20261019T234612Z.json | PASS |  |
| GitHub push time matches API: rel_20261020T171605Z.json | PASS | 2026-10-20T17:16:20Z fec937a959 |
| publication not before generation: rel_20261020T171605Z.json | PASS |  |
| GitHub push time matches API: rel_20261020T181617Z.json | PASS | 2026-10-20T18:16:45Z 066d2f54cf |
| publication not before generation: rel_20261020T181617Z.json | PASS |  |
| GitHub push time matches API: rel_20261021T052652Z.json | PASS | 2026-10-21T05:27:10Z 0ac92d1551 |
| publication not before generation: rel_20261021T052652Z.json | PASS |  |
| GitHub push time matches API: rel_20261021T061607Z.json | PASS | 2026-10-21T06:16:25Z 1a65734f3f |
| publication not before generation: rel_20261021T061607Z.json | PASS |  |
| GitHub push time matches API: rel_20261021T114649Z.json | PASS | 2026-10-21T11:47:06Z cead336293 |
| publication not before generation: rel_20261021T114649Z.json | PASS |  |
| GitHub push time matches API: rel_20261021T174705Z.json | PASS | 2026-10-21T17:47:28Z ca3c262e64 |
| publication not before generation: rel_20261021T174705Z.json | PASS |  |
| GitHub push time matches API: rel_20261022T001623Z.json | PASS | 2026-10-22T00:16:39Z d76469ab37 |
| publication not before generation: rel_20261022T001623Z.json | PASS |  |
| GitHub push time matches API: rel_20261022T080259Z.json | PASS | 2026-10-22T08:03:15Z 6918b31ac5 |
| publication not before generation: rel_20261022T080259Z.json | PASS |  |
| GitHub push time matches API: rel_20261022T134715Z.json | PASS | 2026-10-22T13:47:36Z 98124c5293 |
| publication not before generation: rel_20261022T134715Z.json | PASS |  |
| GitHub push time matches API: rel_20261022T141726Z.json | PASS | 2026-10-22T14:17:48Z cb9f734165 |
| publication not before generation: rel_20261022T141726Z.json | PASS |  |
| GitHub push time matches API: rel_20261022T171656Z.json | PASS | 2026-10-22T17:17:17Z f9ec211999 |
| publication not before generation: rel_20261022T171656Z.json | PASS |  |
| GitHub push time matches API: rel_20261022T201618Z.json | PASS | 2026-10-22T20:16:35Z 93b59c0028 |
| publication not before generation: rel_20261022T201618Z.json | PASS |  |
| GitHub push time matches API: rel_20261022T204608Z.json | PASS | 2026-10-22T20:46:24Z 60f47f6147 |
| publication not before generation: rel_20261022T204608Z.json | PASS |  |
| GitHub push time matches API: rel_20261022T224644Z.json | PASS | 2026-10-22T22:47:01Z 2503186ed2 |
| publication not before generation: rel_20261022T224644Z.json | PASS |  |
| GitHub push time matches API: rel_20261022T231606Z.json | PASS | 2026-10-22T23:16:20Z 79413c3fa2 |
| publication not before generation: rel_20261022T231606Z.json | PASS |  |
| GitHub push time matches API: rel_20261023T004633Z.json | PASS | 2026-10-23T00:46:49Z d0603ec062 |
| publication not before generation: rel_20261023T004633Z.json | PASS |  |
| GitHub push time matches API: rel_20261023T172430Z.json | PASS | 2026-10-23T17:24:53Z 142af63472 |
| publication not before generation: rel_20261023T172430Z.json | PASS |  |
| GitHub push time matches API: rel_20261023T234702Z.json | PASS | 2026-10-23T23:47:19Z 0b6141cbf0 |
| publication not before generation: rel_20261023T234702Z.json | PASS |  |
| GitHub push time matches API: rel_20261024T001607Z.json | PASS | 2026-10-24T00:16:24Z d098632a41 |
| publication not before generation: rel_20261024T001607Z.json | PASS |  |
| GitHub push time matches API: rel_20261024T151746Z.json | PASS | 2026-10-24T15:18:11Z 4716da1812 |
| publication not before generation: rel_20261024T151746Z.json | PASS |  |
| GitHub push time matches API: rel_20261024T214614Z.json | PASS | 2026-10-24T21:46:34Z 7169d5aa82 |
| publication not before generation: rel_20261024T214614Z.json | PASS |  |
| GitHub push time matches API: rel_20261025T034709Z.json | PASS | 2026-10-25T03:47:30Z f40855ef9c |
| publication not before generation: rel_20261025T034709Z.json | PASS |  |
| GitHub push time matches API: rel_20261025T061649Z.json | PASS | 2026-10-25T06:17:08Z 251b8d4f0a |
| publication not before generation: rel_20261025T061649Z.json | PASS |  |
| GitHub push time matches API: rel_20261025T101605Z.json | PASS | 2026-10-25T10:16:22Z cc01632b08 |
| publication not before generation: rel_20261025T101605Z.json | PASS |  |
| GitHub push time matches API: rel_20261025T121627Z.json | PASS | 2026-10-25T12:16:46Z f4c80b995e |
| publication not before generation: rel_20261025T121627Z.json | PASS |  |
| GitHub push time matches API: rel_20261025T124612Z.json | PASS | 2026-10-25T12:46:29Z 2d041a7946 |
| publication not before generation: rel_20261025T124612Z.json | PASS |  |
| GitHub push time matches API: rel_20261025T131632Z.json | PASS | 2026-10-25T13:16:52Z 129a654092 |
| publication not before generation: rel_20261025T131632Z.json | PASS |  |
| GitHub push time matches API: rel_20261025T154730Z.json | PASS | 2026-10-25T15:47:52Z 31fcdb64de |
| publication not before generation: rel_20261025T154730Z.json | PASS |  |
| GitHub push time matches API: rel_20261025T161650Z.json | PASS | 2026-10-25T16:17:11Z 97a8a249cb |
| publication not before generation: rel_20261025T161650Z.json | PASS |  |
| GitHub push time matches API: rel_20261025T164626Z.json | PASS | 2026-10-25T16:46:43Z fddfac6be5 |
| publication not before generation: rel_20261025T164626Z.json | PASS |  |
| GitHub push time matches API: rel_20261025T184728Z.json | PASS | 2026-10-25T18:47:53Z 8ee8d4d0ae |
| publication not before generation: rel_20261025T184728Z.json | PASS |  |
| GitHub push time matches API: rel_20261025T191719Z.json | PASS | 2026-10-25T19:17:42Z 6c192384de |
| publication not before generation: rel_20261025T191719Z.json | PASS |  |
| GitHub push time matches API: rel_20261025T194730Z.json | PASS | 2026-10-25T19:47:59Z 680df3478d |
| publication not before generation: rel_20261025T194730Z.json | PASS |  |
| GitHub push time matches API: rel_20261025T224808Z.json | PASS | 2026-10-25T22:48:45Z faa63cac4a |
| publication not before generation: rel_20261025T224808Z.json | PASS |  |
| GitHub push time matches API: rel_20261025T234725Z.json | PASS | 2026-10-25T23:47:49Z c8ca56864a |
| publication not before generation: rel_20261025T234725Z.json | PASS |  |
| GitHub push time matches API: rel_20261026T014623Z.json | PASS | 2026-10-26T01:46:46Z 73d233d77a |
| publication not before generation: rel_20261026T014623Z.json | PASS |  |
| GitHub push time matches API: rel_20261026T051632Z.json | PASS | 2026-10-26T05:16:51Z 3a2160cd9f |
| publication not before generation: rel_20261026T051632Z.json | PASS |  |
| GitHub push time matches API: rel_20261026T081635Z.json | PASS | 2026-10-26T08:16:51Z 25565dc884 |
| publication not before generation: rel_20261026T081635Z.json | PASS |  |
| GitHub push time matches API: rel_20261026T084641Z.json | PASS | 2026-10-26T08:46:57Z 8ea0830d1c |
| publication not before generation: rel_20261026T084641Z.json | PASS |  |
| GitHub push time matches API: rel_20261026T124646Z.json | PASS | 2026-10-26T12:47:03Z b14b0a5b3b |
| publication not before generation: rel_20261026T124646Z.json | PASS |  |
| GitHub push time matches API: rel_20261026T184612Z.json | PASS | 2026-10-26T18:46:29Z eb5275e081 |
| publication not before generation: rel_20261026T184612Z.json | PASS |  |
| GitHub push time matches API: rel_20261026T224615Z.json | PASS | 2026-10-26T22:46:36Z fc5ff64b63 |
| publication not before generation: rel_20261026T224615Z.json | PASS |  |
| GitHub push time matches API: rel_20261026T231712Z.json | PASS | 2026-10-26T23:17:32Z 4ef194703e |
| publication not before generation: rel_20261026T231712Z.json | PASS |  |
| GitHub push time matches API: rel_20261027T181619Z.json | PASS | 2026-10-27T18:16:41Z 70f7ae59b7 |
| publication not before generation: rel_20261027T181619Z.json | PASS |  |
| GitHub push time matches API: rel_20261028T004611Z.json | PASS | 2026-10-28T00:46:31Z 1d416b0f06 |
| publication not before generation: rel_20261028T004611Z.json | PASS |  |
| GitHub push time matches API: rel_20261028T160617Z.json | PASS | 2026-10-28T16:06:42Z 8cf5d74c71 |
| publication not before generation: rel_20261028T160617Z.json | PASS |  |
| GitHub push time matches API: rel_20261028T221638Z.json | PASS | 2026-10-28T22:17:03Z b955a29613 |
| publication not before generation: rel_20261028T221638Z.json | PASS |  |
| GitHub push time matches API: rel_20261029T041843Z.json | PASS | 2026-10-29T04:19:34Z 0f9efcd835 |
| publication not before generation: rel_20261029T041843Z.json | PASS |  |
| GitHub push time matches API: rel_20261029T171012Z.json | PASS | 2026-10-29T17:10:49Z 0d25aea177 |
| publication not before generation: rel_20261029T171012Z.json | PASS |  |
| GitHub push time matches API: rel_20261029T181614Z.json | PASS | 2026-10-29T18:16:50Z ab9d8317c1 |
| publication not before generation: rel_20261029T181614Z.json | PASS |  |
| GitHub push time matches API: rel_20261029T211701Z.json | PASS | 2026-10-29T21:17:34Z f5e1ab1fef |
| publication not before generation: rel_20261029T211701Z.json | PASS |  |
| GitHub push time matches API: rel_20261029T214725Z.json | PASS | 2026-10-29T21:48:03Z 0a4c3b9001 |
| publication not before generation: rel_20261029T214725Z.json | PASS |  |
| GitHub push time matches API: rel_20261029T224735Z.json | PASS | 2026-10-29T22:48:15Z ccc082ff15 |
| publication not before generation: rel_20261029T224735Z.json | PASS |  |
| GitHub push time matches API: rel_20261029T231801Z.json | PASS | 2026-10-29T23:18:39Z bddc49af51 |
| publication not before generation: rel_20261029T231801Z.json | PASS |  |
| GitHub push time matches API: rel_20261030T014622Z.json | PASS | 2026-10-30T01:47:00Z 1ec763d7ef |
| publication not before generation: rel_20261030T014622Z.json | PASS |  |
| GitHub push time matches API: rel_20261030T165902Z.json | PASS | 2026-10-30T16:59:36Z 0b83178e30 |
| publication not before generation: rel_20261030T165902Z.json | PASS |  |
| GitHub push time matches API: rel_20261030T231726Z.json | PASS | 2026-10-30T23:18:05Z f616ff7114 |
| publication not before generation: rel_20261030T231726Z.json | PASS |  |
| GitHub push time matches API: rel_20261031T011620Z.json | PASS | 2026-10-31T01:16:55Z 4b1fc1d16a |
| publication not before generation: rel_20261031T011620Z.json | PASS |  |
| GitHub push time matches API: rel_20261031T141234Z.json | PASS | 2026-10-31T14:13:07Z 18693e0f53 |
| publication not before generation: rel_20261031T141234Z.json | PASS |  |
| GitHub push time matches API: rel_20261031T201643Z.json | PASS | 2026-10-31T20:17:29Z 39b7b76826 |
| publication not before generation: rel_20261031T201643Z.json | PASS |  |
| GitHub push time matches API: rel_20261101T021702Z.json | PASS | 2026-11-01T02:18:20Z ac715c979b |
| publication not before generation: rel_20261101T021702Z.json | PASS |  |
| GitHub push time matches API: rel_20261101T131800Z.json | PASS | 2026-11-01T13:18:34Z b192bba781 |
| publication not before generation: rel_20261101T131800Z.json | PASS |  |
| GitHub push time matches API: rel_20261101T164625Z.json | PASS | 2026-11-01T16:47:01Z 2fcbd3b70a |
| publication not before generation: rel_20261101T164625Z.json | PASS |  |
| GitHub push time matches API: rel_20261101T171613Z.json | PASS | 2026-11-01T17:16:47Z 7e0898cc85 |
| publication not before generation: rel_20261101T171613Z.json | PASS |  |
| GitHub push time matches API: rel_20261101T174616Z.json | PASS | 2026-11-01T17:46:50Z dce715099b |
| publication not before generation: rel_20261101T174616Z.json | PASS |  |
| GitHub push time matches API: rel_20261101T194614Z.json | PASS | 2026-11-01T19:46:47Z 0d8671e353 |
| publication not before generation: rel_20261101T194614Z.json | PASS |  |
| GitHub push time matches API: rel_20261101T201634Z.json | PASS | 2026-11-01T20:17:13Z 435836a86b |
| publication not before generation: rel_20261101T201634Z.json | PASS |  |
| GitHub push time matches API: rel_20261101T204627Z.json | PASS | 2026-11-01T20:47:09Z 169d52e061 |
| publication not before generation: rel_20261101T204627Z.json | PASS |  |
| GitHub push time matches API: rel_20261102T004741Z.json | PASS | 2026-11-02T00:48:24Z 77fbe55014 |
| publication not before generation: rel_20261102T004741Z.json | PASS |  |
| GitHub push time matches API: rel_20261102T164757Z.json | PASS | 2026-11-02T16:48:33Z cf25f88fb1 |
| publication not before generation: rel_20261102T164757Z.json | PASS |  |
| GitHub push time matches API: rel_20261103T001618Z.json | PASS | 2026-11-03T00:16:53Z 217593b0d9 |
| publication not before generation: rel_20261103T001618Z.json | PASS |  |
| GitHub push time matches API: rel_20261103T181615Z.json | PASS | 2026-11-03T18:16:51Z 971d4ada93 |
| publication not before generation: rel_20261103T181615Z.json | PASS |  |
| GitHub push time matches API: rel_20261103T194643Z.json | PASS | 2026-11-03T19:47:20Z 22c4d6e3c8 |
| publication not before generation: rel_20261103T194643Z.json | PASS |  |
| GitHub push time matches API: rel_20261104T014726Z.json | PASS | 2026-11-04T01:47:58Z 4072ec0c18 |
| publication not before generation: rel_20261104T014726Z.json | PASS |  |
| GitHub push time matches API: rel_20261104T094628Z.json | PASS | 2026-11-04T09:47:21Z 87f49b4264 |
| publication not before generation: rel_20261104T094628Z.json | PASS |  |
| GitHub push time matches API: rel_20261104T154621Z.json | PASS | 2026-11-04T15:46:48Z f28820f154 |
| publication not before generation: rel_20261104T154621Z.json | PASS |  |
| GitHub push time matches API: rel_20261104T204614Z.json | PASS | 2026-11-04T20:46:42Z c3362d4c7a |
| publication not before generation: rel_20261104T204614Z.json | PASS |  |
| GitHub push time matches API: rel_20261104T214636Z.json | PASS | 2026-11-04T21:47:04Z dfca373521 |
| publication not before generation: rel_20261104T214636Z.json | PASS |  |
| GitHub push time matches API: rel_20261105T165227Z.json | PASS | 2026-11-05T16:52:58Z 4d8c471de0 |
| publication not before generation: rel_20261105T165227Z.json | PASS |  |
| GitHub push time matches API: rel_20261105T181616Z.json | PASS | 2026-11-05T18:16:46Z 639a6ad6e9 |
| publication not before generation: rel_20261105T181616Z.json | PASS |  |
| GitHub push time matches API: rel_20261105T211714Z.json | PASS | 2026-11-05T21:17:47Z ffd72aa217 |
| publication not before generation: rel_20261105T211714Z.json | PASS |  |
| GitHub push time matches API: rel_20261105T214712Z.json | PASS | 2026-11-05T21:47:42Z 424516139d |
| publication not before generation: rel_20261105T214712Z.json | PASS |  |
| GitHub push time matches API: rel_20261105T231640Z.json | PASS | 2026-11-05T23:17:07Z 888ea3bf17 |
| publication not before generation: rel_20261105T231640Z.json | PASS |  |
| GitHub push time matches API: rel_20261106T001644Z.json | PASS | 2026-11-06T00:17:15Z 9fb0c3bdbd |
| publication not before generation: rel_20261106T001644Z.json | PASS |  |
| GitHub push time matches API: rel_20261106T014705Z.json | PASS | 2026-11-06T01:47:34Z 4a835e3a44 |
| publication not before generation: rel_20261106T014705Z.json | PASS |  |
| GitHub push time matches API: rel_20261106T085844Z.json | PASS | 2026-11-06T08:59:14Z d15af5dedd |
| publication not before generation: rel_20261106T085844Z.json | PASS |  |
| GitHub push time matches API: rel_20261106T131616Z.json | PASS | 2026-11-06T13:16:45Z 0182495914 |
| publication not before generation: rel_20261106T131616Z.json | PASS |  |
| GitHub push time matches API: rel_20261106T151626Z.json | PASS | 2026-11-06T15:16:55Z bafe24d819 |
| publication not before generation: rel_20261106T151626Z.json | PASS |  |
| GitHub push time matches API: rel_20261106T211717Z.json | PASS | 2026-11-06T21:17:55Z 9cb6fcdafe |
| publication not before generation: rel_20261106T211717Z.json | PASS |  |
| GitHub push time matches API: rel_20261107T011642Z.json | PASS | 2026-11-07T01:17:21Z 9237299db6 |
| publication not before generation: rel_20261107T011642Z.json | PASS |  |
| GitHub push time matches API: rel_20261107T114800Z.json | PASS | 2026-11-07T11:48:40Z 7a717f08e3 |
| publication not before generation: rel_20261107T114800Z.json | PASS |  |
| GitHub push time matches API: rel_20261107T181629Z.json | PASS | 2026-11-07T18:17:02Z a39086f69c |
| publication not before generation: rel_20261107T181629Z.json | PASS |  |
| GitHub push time matches API: rel_20261108T001809Z.json | PASS | 2026-11-08T00:18:44Z 6fa73dbb2a |
| publication not before generation: rel_20261108T001809Z.json | PASS |  |
| GitHub push time matches API: rel_20261108T122418Z.json | PASS | 2026-11-08T12:24:50Z 2c154dcb02 |
| publication not before generation: rel_20261108T122418Z.json | PASS |  |
| GitHub push time matches API: rel_20261108T131612Z.json | PASS | 2026-11-08T13:16:42Z 8749c74b05 |
| publication not before generation: rel_20261108T131612Z.json | PASS |  |
| GitHub push time matches API: rel_20261108T134618Z.json | PASS | 2026-11-08T13:46:48Z 4cc2c08dff |
| publication not before generation: rel_20261108T134618Z.json | PASS |  |
| GitHub push time matches API: rel_20261108T141616Z.json | PASS | 2026-11-08T14:16:47Z 20e758fbc1 |
| publication not before generation: rel_20261108T141616Z.json | PASS |  |
| GitHub push time matches API: rel_20261108T164613Z.json | PASS | 2026-11-08T16:46:42Z b78f581726 |
| publication not before generation: rel_20261108T164613Z.json | PASS |  |
| GitHub push time matches API: rel_20261108T171612Z.json | PASS | 2026-11-08T17:16:41Z 2317e05f35 |
| publication not before generation: rel_20261108T171612Z.json | PASS |  |
| GitHub push time matches API: rel_20261108T174613Z.json | PASS | 2026-11-08T17:46:43Z 4f5bf6bfd5 |
| publication not before generation: rel_20261108T174613Z.json | PASS |  |
| GitHub push time matches API: rel_20261108T201612Z.json | PASS | 2026-11-08T20:16:42Z b2d2f53f28 |
| publication not before generation: rel_20261108T201612Z.json | PASS |  |
| GitHub push time matches API: rel_20261108T204614Z.json | PASS | 2026-11-08T20:46:45Z 275e0ccdcb |
| publication not before generation: rel_20261108T204614Z.json | PASS |  |
| GitHub push time matches API: rel_20261109T004716Z.json | PASS | 2026-11-09T00:47:48Z 839f22e7a4 |
| publication not before generation: rel_20261109T004716Z.json | PASS |  |
| GitHub push time matches API: rel_20261109T090517Z.json | PASS | 2026-11-09T09:06:05Z b454993afc |
| publication not before generation: rel_20261109T090517Z.json | PASS |  |
| GitHub push time matches API: rel_20261109T094617Z.json | PASS | 2026-11-09T09:46:52Z 76b82ccab9 |
| publication not before generation: rel_20261109T094617Z.json | PASS |  |
| GitHub push time matches API: rel_20261109T134617Z.json | PASS | 2026-11-09T13:46:48Z 18722b9861 |
| publication not before generation: rel_20261109T134617Z.json | PASS |  |
| GitHub push time matches API: rel_20261109T151630Z.json | PASS | 2026-11-09T15:17:04Z 8bb2aaf888 |
| publication not before generation: rel_20261109T151630Z.json | PASS |  |
| GitHub push time matches API: rel_20261109T211718Z.json | PASS | 2026-11-09T21:17:47Z 1d4a1c415f |
| publication not before generation: rel_20261109T211718Z.json | PASS |  |
| GitHub push time matches API: rel_20261109T234730Z.json | PASS | 2026-11-09T23:48:03Z d51086818c |
| publication not before generation: rel_20261109T234730Z.json | PASS |  |
| GitHub push time matches API: rel_20261110T001732Z.json | PASS | 2026-11-10T00:18:04Z 625fc09fcb |
| publication not before generation: rel_20261110T001732Z.json | PASS |  |
| GitHub push time matches API: rel_20261110T181619Z.json | PASS | 2026-11-10T18:16:55Z 9c6e91ebda |
| publication not before generation: rel_20261110T181619Z.json | PASS |  |
| GitHub push time matches API: rel_20261110T191616Z.json | PASS | 2026-11-10T19:16:52Z 04beede8b3 |
| publication not before generation: rel_20261110T191616Z.json | PASS |  |
| GitHub push time matches API: rel_20261110T234728Z.json | PASS | 2026-11-10T23:48:05Z 71e0f4d4bd |
| publication not before generation: rel_20261110T234728Z.json | PASS |  |
| GitHub push time matches API: rel_20261111T093342Z.json | PASS | 2026-11-11T09:34:24Z d7f2e00156 |
| publication not before generation: rel_20261111T093342Z.json | PASS |  |
| GitHub push time matches API: rel_20261111T154628Z.json | PASS | 2026-11-11T15:47:03Z 817cf163cc |
| publication not before generation: rel_20261111T154628Z.json | PASS |  |
| GitHub push time matches API: rel_20261111T214741Z.json | PASS | 2026-11-11T21:48:19Z 381dc6af72 |
| publication not before generation: rel_20261111T214741Z.json | PASS |  |
| GitHub push time matches API: rel_20261112T061845Z.json | PASS | 2026-11-12T06:19:35Z 73d509a026 |
| publication not before generation: rel_20261112T061845Z.json | PASS |  |
| GitHub push time matches API: rel_20261112T071720Z.json | PASS | 2026-11-12T07:17:57Z 83ccc3d55c |
| publication not before generation: rel_20261112T071720Z.json | PASS |  |
| GitHub push time matches API: rel_20261112T124807Z.json | PASS | 2026-11-12T12:49:04Z 3206c76032 |
| publication not before generation: rel_20261112T124807Z.json | PASS |  |
| GitHub push time matches API: rel_20261112T144618Z.json | PASS | 2026-11-12T14:46:53Z 16b35aa498 |
| publication not before generation: rel_20261112T144618Z.json | PASS |  |
| GitHub push time matches API: rel_20261112T161629Z.json | PASS | 2026-11-12T16:17:03Z 331b6fe7d3 |
| publication not before generation: rel_20261112T161629Z.json | PASS |  |
| GitHub push time matches API: rel_20261112T181649Z.json | PASS | 2026-11-12T18:17:34Z a68c52be9e |
| publication not before generation: rel_20261112T181649Z.json | PASS |  |
| GitHub push time matches API: rel_20261113T080435Z.json | PASS | 2026-11-13T08:05:11Z a0bebea55a |
| publication not before generation: rel_20261113T080435Z.json | PASS |  |
| GitHub push time matches API: rel_20261113T131709Z.json | PASS | 2026-11-13T13:17:43Z 661198fc68 |
| publication not before generation: rel_20261113T131709Z.json | PASS |  |
| GitHub push time matches API: rel_20261113T141619Z.json | PASS | 2026-11-13T14:16:53Z d9415e9047 |
| publication not before generation: rel_20261113T141619Z.json | PASS |  |
| GitHub push time matches API: rel_20261113T154705Z.json | PASS | 2026-11-13T15:47:41Z 54117eba7a |
| publication not before generation: rel_20261113T154705Z.json | PASS |  |
| GitHub push time matches API: rel_20261113T201741Z.json | PASS | 2026-11-13T20:18:24Z e4a16c7a13 |
| publication not before generation: rel_20261113T201741Z.json | PASS |  |
| GitHub push time matches API: rel_20261114T100214Z.json | PASS | 2026-11-14T10:02:50Z 7574655a9c |
| publication not before generation: rel_20261114T100214Z.json | PASS |  |
| GitHub push time matches API: rel_20261115T095847Z.json | PASS | 2026-11-15T09:59:26Z 5e13906f22 |
| publication not before generation: rel_20261115T095847Z.json | PASS |  |
| GitHub push time matches API: rel_20261115T131808Z.json | PASS | 2026-11-15T13:18:54Z 72e4780817 |
| publication not before generation: rel_20261115T131808Z.json | PASS |  |
| exported verification labels match evidence (3198 versions) | PASS |  |
| every late publication has a correction | PASS |  |
| every release matches its write-once manifest | PASS |  |
| RFC 3161 token verifies against rel_20260924T232247Z.json | PASS | Sep 25 01:39:14 2026 GMT |
| Web Archive copy matches rel_20260924T232247Z.json | PASS | 2026-09-25T01:39:51+00:00 |
| RFC 3161 token verifies against rel_20260924T235129Z.json | PASS | Sep 25 01:39:16 2026 GMT |
| Web Archive copy matches rel_20260924T235129Z.json | PASS | 2026-09-25T01:39:57+00:00 |
| RFC 3161 token verifies against rel_20260925T000247Z.json | PASS | Sep 25 01:39:17 2026 GMT |
| Web Archive copy matches rel_20260925T000247Z.json | PASS | 2026-09-25T01:40:05+00:00 |
| RFC 3161 token verifies against rel_20260925T011000Z.json | PASS | Sep 25 01:39:18 2026 GMT |
| Web Archive copy matches rel_20260925T011000Z.json | PASS | 2026-09-25T01:37:46+00:00 |
| RFC 3161 token verifies against rel_20260925T015111Z.json | PASS | Sep 25 01:51:15 2026 GMT |
| Web Archive copy matches rel_20260925T015111Z.json | PASS | 2026-09-25T01:57:42+00:00 |
| RFC 3161 token verifies against rel_20260925T015951Z.json | PASS | Sep 25 01:59:54 2026 GMT |
| Web Archive copy matches rel_20260925T015951Z.json | PASS | 2026-09-25T02:00:09+00:00 |
| RFC 3161 token verifies against rel_20260925T021501Z.json | PASS | Sep 25 02:15:03 2026 GMT |
| Web Archive copy matches rel_20260925T021501Z.json | PASS | 2026-09-25T02:15:20+00:00 |
| RFC 3161 token verifies against rel_20260925T051555Z.json | PASS | Sep 25 05:15:57 2026 GMT |
| Web Archive copy matches rel_20260925T051555Z.json | PASS | 2026-09-25T05:16:26+00:00 |
| RFC 3161 token verifies against rel_20260925T061553Z.json | PASS | Sep 25 06:15:56 2026 GMT |
| Web Archive copy matches rel_20260925T061553Z.json | PASS | 2026-09-25T06:16:19+00:00 |
| RFC 3161 token verifies against rel_20260925T121558Z.json | PASS | Sep 25 12:16:01 2026 GMT |
| Web Archive copy matches rel_20260925T121558Z.json | PASS | 2026-09-25T12:16:18+00:00 |
| RFC 3161 token verifies against rel_20260925T131600Z.json | PASS | Sep 25 13:16:04 2026 GMT |
| Web Archive copy matches rel_20260925T131600Z.json | PASS | 2026-09-25T13:16:22+00:00 |
| RFC 3161 token verifies against rel_20260925T132351Z.json | PASS | Sep 25 13:23:55 2026 GMT |
| Web Archive copy matches rel_20260925T132351Z.json | PASS | 2026-09-25T13:24:13+00:00 |
| RFC 3161 token verifies against rel_20260925T194611Z.json | PASS | Sep 25 19:46:14 2026 GMT |
| Web Archive copy matches rel_20260925T194611Z.json | PASS | 2026-09-25T19:46:33+00:00 |
| RFC 3161 token verifies against rel_20260926T103448Z.json | PASS | Sep 26 10:34:52 2026 GMT |
| Web Archive copy matches rel_20260926T103448Z.json | PASS | 2026-09-26T10:35:35+00:00 |
| RFC 3161 token verifies against rel_20260926T164605Z.json | PASS | Sep 26 16:46:08 2026 GMT |
| Web Archive copy matches rel_20260926T164605Z.json | PASS | 2026-09-26T16:46:25+00:00 |
| RFC 3161 token verifies against rel_20260926T224614Z.json | PASS | Sep 26 22:46:18 2026 GMT |
| Web Archive copy matches rel_20260926T224614Z.json | PASS | 2026-09-26T23:15:58+00:00 |
| RFC 3161 token verifies against rel_20260927T051547Z.json | PASS | Sep 27 05:15:49 2026 GMT |
| Web Archive copy matches rel_20260927T051547Z.json | PASS | 2026-09-27T05:16:05+00:00 |
| RFC 3161 token verifies against rel_20260927T061550Z.json | PASS | Sep 27 06:15:52 2026 GMT |
| Web Archive copy matches rel_20260927T061550Z.json | PASS | 2026-09-27T06:45:49+00:00 |
| RFC 3161 token verifies against rel_20260927T114559Z.json | PASS | Sep 27 11:46:02 2026 GMT |
| Web Archive copy matches rel_20260927T114559Z.json | PASS | 2026-09-27T11:46:18+00:00 |
| RFC 3161 token verifies against rel_20260927T154559Z.json | PASS | Sep 27 15:46:03 2026 GMT |
| Web Archive copy matches rel_20260927T154559Z.json | PASS | 2026-09-27T18:16:22+00:00 |
| RFC 3161 token verifies against rel_20260927T161549Z.json | PASS | Sep 27 16:15:52 2026 GMT |
| Web Archive copy matches rel_20260927T161549Z.json | FAIL | could not re-download now (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260927T164557Z.json | PASS | Sep 27 16:46:00 2026 GMT |
| Web Archive copy matches rel_20260927T164557Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260927T184611Z.json | PASS | Sep 27 18:46:14 2026 GMT |
| Web Archive copy matches rel_20260927T184611Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260927T191559Z.json | PASS | Sep 27 19:16:03 2026 GMT |
| Web Archive copy matches rel_20260927T191559Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260927T194601Z.json | PASS | Sep 27 19:46:05 2026 GMT |
| Web Archive copy matches rel_20260927T194601Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260927T224554Z.json | PASS | Sep 27 22:45:57 2026 GMT |
| Web Archive copy matches rel_20260927T224554Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260927T234556Z.json | PASS | Sep 27 23:45:59 2026 GMT |
| Web Archive copy matches rel_20260927T234556Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260928T051551Z.json | PASS | Sep 28 05:15:55 2026 GMT |
| Web Archive copy matches rel_20260928T051551Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260928T061549Z.json | PASS | Sep 28 06:15:53 2026 GMT |
| Web Archive copy matches rel_20260928T061549Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260928T081553Z.json | PASS | Sep 28 08:15:56 2026 GMT |
| Web Archive copy matches rel_20260928T081553Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260928T084549Z.json | PASS | Sep 28 08:45:52 2026 GMT |
| Web Archive copy matches rel_20260928T084549Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260928T124550Z.json | PASS | Sep 28 12:45:54 2026 GMT |
| Web Archive copy matches rel_20260928T124550Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260928T181556Z.json | PASS | Sep 28 18:15:59 2026 GMT |
| Web Archive copy matches rel_20260928T181556Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260928T224603Z.json | PASS | Sep 28 22:46:06 2026 GMT |
| Web Archive copy matches rel_20260928T224603Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260928T231615Z.json | PASS | Sep 28 23:16:18 2026 GMT |
| Web Archive copy matches rel_20260928T231615Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260928T233941Z.json | PASS | Sep 28 23:39:44 2026 GMT |
| Web Archive copy matches rel_20260928T233941Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260929T001605Z.json | PASS | Sep 29 00:16:08 2026 GMT |
| Web Archive copy matches rel_20260929T001605Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260929T034601Z.json | PASS | Sep 29 03:46:04 2026 GMT |
| Web Archive copy matches rel_20260929T034601Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260929T044550Z.json | PASS | Sep 29 04:45:53 2026 GMT |
| Web Archive copy matches rel_20260929T044550Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260929T054551Z.json | PASS | Sep 29 05:45:54 2026 GMT |
| Web Archive copy matches rel_20260929T054551Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260929T061550Z.json | PASS | Sep 29 06:15:54 2026 GMT |
| Web Archive copy matches rel_20260929T061550Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260929T121551Z.json | PASS | Sep 29 12:15:55 2026 GMT |
| Web Archive copy matches rel_20260929T121551Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260929T141558Z.json | PASS | Sep 29 14:16:01 2026 GMT |
| Web Archive copy matches rel_20260929T141558Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260929T181556Z.json | PASS | Sep 29 18:15:59 2026 GMT |
| Web Archive copy matches rel_20260929T181556Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260930T001556Z.json | PASS | Sep 30 00:16:00 2026 GMT |
| Web Archive copy matches rel_20260930T001556Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260930T134704Z.json | PASS | Sep 30 13:47:12 2026 GMT |
| Web Archive copy matches rel_20260930T134704Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20260930T201609Z.json | PASS | Sep 30 20:16:15 2026 GMT |
| Web Archive copy matches rel_20260930T201609Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261001T021611Z.json | PASS | Oct  1 02:16:16 2026 GMT |
| Web Archive copy matches rel_20261001T021611Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261001T125953Z.json | PASS | Oct  1 12:59:58 2026 GMT |
| Web Archive copy matches rel_20261001T125953Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261001T134555Z.json | PASS | Oct  1 13:45:59 2026 GMT |
| Web Archive copy matches rel_20261001T134555Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261001T144623Z.json | PASS | Oct  1 14:46:29 2026 GMT |
| Web Archive copy matches rel_20261001T144623Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261001T171604Z.json | PASS | Oct  1 17:16:09 2026 GMT |
| Web Archive copy matches rel_20261001T171604Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261001T191750Z.json | PASS | Oct  1 19:17:59 2026 GMT |
| Web Archive copy matches rel_20261001T191750Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261001T201658Z.json | PASS | Oct  1 20:17:06 2026 GMT |
| Web Archive copy matches rel_20261001T201658Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261001T204602Z.json | PASS | Oct  1 20:46:07 2026 GMT |
| Web Archive copy matches rel_20261001T204602Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261001T224758Z.json | PASS | Oct  1 22:48:03 2026 GMT |
| Web Archive copy matches rel_20261001T224758Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261001T231600Z.json | PASS | Oct  1 23:16:05 2026 GMT |
| Web Archive copy matches rel_20261001T231600Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261001T234558Z.json | PASS | Oct  1 23:46:03 2026 GMT |
| Web Archive copy matches rel_20261001T234558Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261002T013537Z.json | PASS | Oct  2 01:35:42 2026 GMT |
| Web Archive copy matches rel_20261002T013537Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261002T061555Z.json | PASS | Oct  2 06:15:59 2026 GMT |
| Web Archive copy matches rel_20261002T061555Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261002T121553Z.json | PASS | Oct  2 12:15:57 2026 GMT |
| Web Archive copy matches rel_20261002T121553Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261002T184600Z.json | PASS | Oct  2 18:46:04 2026 GMT |
| Web Archive copy matches rel_20261002T184600Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261003T131647Z.json | PASS | Oct  3 13:16:57 2026 GMT |
| Web Archive copy matches rel_20261003T131647Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261003T191642Z.json | PASS | Oct  3 19:16:51 2026 GMT |
| Web Archive copy matches rel_20261003T191642Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261004T014555Z.json | PASS | Oct  4 01:46:00 2026 GMT |
| Web Archive copy matches rel_20261004T014555Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261004T122417Z.json | PASS | Oct  4 12:24:25 2026 GMT |
| Web Archive copy matches rel_20261004T122417Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261004T124623Z.json | PASS | Oct  4 12:46:28 2026 GMT |
| Web Archive copy matches rel_20261004T124623Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261004T131557Z.json | PASS | Oct  4 13:16:02 2026 GMT |
| Web Archive copy matches rel_20261004T131557Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261004T154608Z.json | PASS | Oct  4 15:46:13 2026 GMT |
| Web Archive copy matches rel_20261004T154608Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261004T161557Z.json | PASS | Oct  4 16:16:02 2026 GMT |
| Web Archive copy matches rel_20261004T161557Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261004T164554Z.json | PASS | Oct  4 16:45:58 2026 GMT |
| Web Archive copy matches rel_20261004T164554Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261004T191617Z.json | PASS | Oct  4 19:16:21 2026 GMT |
| Web Archive copy matches rel_20261004T191617Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261004T194555Z.json | PASS | Oct  4 19:45:59 2026 GMT |
| Web Archive copy matches rel_20261004T194555Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261004T224614Z.json | PASS | Oct  4 22:46:19 2026 GMT |
| Web Archive copy matches rel_20261004T224614Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261004T234600Z.json | PASS | Oct  4 23:46:05 2026 GMT |
| Web Archive copy matches rel_20261004T234600Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261005T101630Z.json | PASS | Oct  5 10:16:35 2026 GMT |
| Web Archive copy matches rel_20261005T101630Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261005T124556Z.json | PASS | Oct  5 12:45:59 2026 GMT |
| Web Archive copy matches rel_20261005T124556Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261005T224631Z.json | PASS | Oct  5 22:46:36 2026 GMT |
| Web Archive copy matches rel_20261005T224631Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261005T231609Z.json | PASS | Oct  5 23:16:12 2026 GMT |
| Web Archive copy matches rel_20261005T231609Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261006T204330Z.json | PASS | Oct  6 20:43:34 2026 GMT |
| Web Archive copy matches rel_20261006T204330Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261007T004623Z.json | PASS | Oct  7 00:46:31 2026 GMT |
| Web Archive copy matches rel_20261007T004623Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261007T122817Z.json | PASS | Oct  7 12:28:24 2026 GMT |
| Web Archive copy matches rel_20261007T122817Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261007T184603Z.json | PASS | Oct  7 18:46:08 2026 GMT |
| Web Archive copy matches rel_20261007T184603Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261008T004618Z.json | PASS | Oct  8 00:46:23 2026 GMT |
| Web Archive copy matches rel_20261008T004618Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261008T061608Z.json | PASS | Oct  8 06:16:13 2026 GMT |
| Web Archive copy matches rel_20261008T061608Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261008T064615Z.json | PASS | Oct  8 06:46:20 2026 GMT |
| Web Archive copy matches rel_20261008T064615Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261008T124712Z.json | PASS | Oct  8 12:47:21 2026 GMT |
| Web Archive copy matches rel_20261008T124712Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261008T134559Z.json | PASS | Oct  8 13:46:05 2026 GMT |
| Web Archive copy matches rel_20261008T134559Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261008T171703Z.json | PASS | Oct  8 17:17:13 2026 GMT |
| Web Archive copy matches rel_20261008T171703Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261008T191602Z.json | PASS | Oct  8 19:16:09 2026 GMT |
| Web Archive copy matches rel_20261008T191602Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261008T201601Z.json | PASS | Oct  8 20:16:07 2026 GMT |
| Web Archive copy matches rel_20261008T201601Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261008T204618Z.json | PASS | Oct  8 20:46:26 2026 GMT |
| Web Archive copy matches rel_20261008T204618Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261008T224607Z.json | PASS | Oct  8 22:46:14 2026 GMT |
| Web Archive copy matches rel_20261008T224607Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261008T231658Z.json | PASS | Oct  8 23:17:10 2026 GMT |
| Web Archive copy matches rel_20261008T231658Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261008T234642Z.json | PASS | Oct  8 23:48:51 2026 GMT |
| Web Archive copy matches rel_20261008T234642Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261009T004652Z.json | PASS | Oct  9 00:47:01 2026 GMT |
| Web Archive copy matches rel_20261009T004652Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261009T124551Z.json | PASS | Oct  9 12:45:58 2026 GMT |
| Web Archive copy matches rel_20261009T124551Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261009T184623Z.json | PASS | Oct  9 18:46:32 2026 GMT |
| Web Archive copy matches rel_20261009T184623Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261010T001609Z.json | PASS | Oct 10 00:16:15 2026 GMT |
| Web Archive copy matches rel_20261010T001609Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261010T004631Z.json | PASS | Oct 10 00:46:38 2026 GMT |
| Web Archive copy matches rel_20261010T004631Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261010T061555Z.json | PASS | Oct 10 06:15:59 2026 GMT |
| Web Archive copy matches rel_20261010T061555Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261010T071555Z.json | PASS | Oct 10 07:15:59 2026 GMT |
| Web Archive copy matches rel_20261010T071555Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261010T131625Z.json | PASS | Oct 10 13:16:31 2026 GMT |
| Web Archive copy matches rel_20261010T131625Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261010T194716Z.json | PASS | Oct 10 19:47:28 2026 GMT |
| Web Archive copy matches rel_20261010T194716Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261011T021619Z.json | PASS | Oct 11 02:16:27 2026 GMT |
| Web Archive copy matches rel_20261011T021619Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261011T124515Z.json | PASS | Oct 11 12:45:22 2026 GMT |
| Web Archive copy matches rel_20261011T124515Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261011T154620Z.json | PASS | Oct 11 15:46:28 2026 GMT |
| Web Archive copy matches rel_20261011T154620Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261011T161559Z.json | PASS | Oct 11 16:16:06 2026 GMT |
| Web Archive copy matches rel_20261011T161559Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261011T164559Z.json | PASS | Oct 11 16:46:06 2026 GMT |
| Web Archive copy matches rel_20261011T164559Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261012T085723Z.json | PASS | Oct 12 08:57:31 2026 GMT |
| Web Archive copy matches rel_20261012T085723Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261012T124559Z.json | PASS | Oct 12 12:46:05 2026 GMT |
| Web Archive copy matches rel_20261012T124559Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261012T233818Z.json | PASS | Oct 12 23:38:22 2026 GMT |
| Web Archive copy matches rel_20261012T233818Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261013T170040Z.json | PASS | Oct 13 17:00:47 2026 GMT |
| Web Archive copy matches rel_20261013T170040Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261013T181602Z.json | PASS | Oct 13 18:16:07 2026 GMT |
| Web Archive copy matches rel_20261013T181602Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261014T004602Z.json | PASS | Oct 14 00:46:08 2026 GMT |
| Web Archive copy matches rel_20261014T004602Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261014T061628Z.json | PASS | Oct 14 06:16:35 2026 GMT |
| Web Archive copy matches rel_20261014T061628Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261014T071558Z.json | PASS | Oct 14 07:16:04 2026 GMT |
| Web Archive copy matches rel_20261014T071558Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261014T144718Z.json | PASS | Oct 14 14:47:27 2026 GMT |
| Web Archive copy matches rel_20261014T144718Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261014T211613Z.json | PASS | Oct 14 21:16:21 2026 GMT |
| Web Archive copy matches rel_20261014T211613Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261015T150557Z.json | PASS | Oct 15 15:06:05 2026 GMT |
| Web Archive copy matches rel_20261015T150557Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261015T171615Z.json | PASS | Oct 15 17:16:25 2026 GMT |
| Web Archive copy matches rel_20261015T171615Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261015T201620Z.json | PASS | Oct 15 20:16:30 2026 GMT |
| Web Archive copy matches rel_20261015T201620Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261015T204633Z.json | PASS | Oct 15 20:46:42 2026 GMT |
| Web Archive copy matches rel_20261015T204633Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261015T211623Z.json | PASS | Oct 15 21:16:33 2026 GMT |
| Web Archive copy matches rel_20261015T211623Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261015T231654Z.json | PASS | Oct 15 23:17:05 2026 GMT |
| Web Archive copy matches rel_20261015T231654Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261016T004656Z.json | PASS | Oct 16 00:47:06 2026 GMT |
| Web Archive copy matches rel_20261016T004656Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261016T160625Z.json | PASS | Oct 16 16:06:32 2026 GMT |
| Web Archive copy matches rel_20261016T160625Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261016T221640Z.json | PASS | Oct 16 22:16:48 2026 GMT |
| Web Archive copy matches rel_20261016T221640Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261017T001700Z.json | PASS | Oct 17 00:17:09 2026 GMT |
| Web Archive copy matches rel_20261017T001700Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261017T044625Z.json | PASS | Oct 17 04:46:31 2026 GMT |
| Web Archive copy matches rel_20261017T044625Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261017T061658Z.json | PASS | Oct 17 06:17:07 2026 GMT |
| Web Archive copy matches rel_20261017T061658Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261017T171645Z.json | PASS | Oct 17 17:16:53 2026 GMT |
| Web Archive copy matches rel_20261017T171645Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261017T231726Z.json | PASS | Oct 17 23:17:35 2026 GMT |
| Web Archive copy matches rel_20261017T231726Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261018T054611Z.json | PASS | Oct 18 05:46:17 2026 GMT |
| Web Archive copy matches rel_20261018T054611Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261018T061600Z.json | PASS | Oct 18 06:16:07 2026 GMT |
| Web Archive copy matches rel_20261018T061600Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261018T114641Z.json | PASS | Oct 18 11:46:48 2026 GMT |
| Web Archive copy matches rel_20261018T114641Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261018T124607Z.json | PASS | Oct 18 12:46:14 2026 GMT |
| Web Archive copy matches rel_20261018T124607Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261018T154628Z.json | PASS | Oct 18 15:46:48 2026 GMT |
| Web Archive copy matches rel_20261018T154628Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261018T161720Z.json | PASS | Oct 18 16:17:30 2026 GMT |
| Web Archive copy matches rel_20261018T161720Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261018T164705Z.json | PASS | Oct 18 16:47:12 2026 GMT |
| Web Archive copy matches rel_20261018T164705Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261018T184614Z.json | PASS | Oct 18 18:46:20 2026 GMT |
| Web Archive copy matches rel_20261018T184614Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261018T191608Z.json | PASS | Oct 18 19:16:16 2026 GMT |
| Web Archive copy matches rel_20261018T191608Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261018T194614Z.json | PASS | Oct 18 19:46:22 2026 GMT |
| Web Archive copy matches rel_20261018T194614Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261018T224605Z.json | PASS | Oct 18 22:46:13 2026 GMT |
| Web Archive copy matches rel_20261018T224605Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261018T234602Z.json | PASS | Oct 18 23:46:08 2026 GMT |
| Web Archive copy matches rel_20261018T234602Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261019T164729Z.json | PASS | Oct 19 16:47:36 2026 GMT |
| Web Archive copy matches rel_20261019T164729Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261019T231606Z.json | PASS | Oct 19 23:16:13 2026 GMT |
| Web Archive copy matches rel_20261019T231606Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261019T234612Z.json | PASS | Oct 19 23:46:20 2026 GMT |
| Web Archive copy matches rel_20261019T234612Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261020T171605Z.json | PASS | Oct 20 17:16:12 2026 GMT |
| Web Archive copy matches rel_20261020T171605Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261020T181617Z.json | PASS | Oct 20 18:16:25 2026 GMT |
| Web Archive copy matches rel_20261020T181617Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261021T052652Z.json | PASS | Oct 21 05:27:01 2026 GMT |
| Web Archive copy matches rel_20261021T052652Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261021T061607Z.json | PASS | Oct 21 06:16:15 2026 GMT |
| Web Archive copy matches rel_20261021T061607Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261021T114649Z.json | PASS | Oct 21 11:46:57 2026 GMT |
| Web Archive copy matches rel_20261021T114649Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261021T174705Z.json | PASS | Oct 21 17:47:15 2026 GMT |
| Web Archive copy matches rel_20261021T174705Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261022T001623Z.json | PASS | Oct 22 00:16:31 2026 GMT |
| Web Archive copy matches rel_20261022T001623Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261022T080259Z.json | PASS | Oct 22 08:03:06 2026 GMT |
| Web Archive copy matches rel_20261022T080259Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261022T134715Z.json | PASS | Oct 22 13:47:26 2026 GMT |
| Web Archive copy matches rel_20261022T134715Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261022T141726Z.json | PASS | Oct 22 14:17:36 2026 GMT |
| Web Archive copy matches rel_20261022T141726Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261022T171656Z.json | PASS | Oct 22 17:17:05 2026 GMT |
| Web Archive copy matches rel_20261022T171656Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261022T201618Z.json | PASS | Oct 22 20:16:26 2026 GMT |
| Web Archive copy matches rel_20261022T201618Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261022T204608Z.json | PASS | Oct 22 20:46:15 2026 GMT |
| Web Archive copy matches rel_20261022T204608Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261022T224644Z.json | PASS | Oct 22 22:46:51 2026 GMT |
| Web Archive copy matches rel_20261022T224644Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261022T231606Z.json | PASS | Oct 22 23:16:12 2026 GMT |
| Web Archive copy matches rel_20261022T231606Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261023T004633Z.json | PASS | Oct 23 00:46:40 2026 GMT |
| Web Archive copy matches rel_20261023T004633Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261023T172430Z.json | PASS | Oct 23 17:24:41 2026 GMT |
| Web Archive copy matches rel_20261023T172430Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261023T234702Z.json | PASS | Oct 23 23:47:10 2026 GMT |
| Web Archive copy matches rel_20261023T234702Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261024T001607Z.json | PASS | Oct 24 00:16:15 2026 GMT |
| Web Archive copy matches rel_20261024T001607Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261024T151746Z.json | PASS | Oct 24 15:17:58 2026 GMT |
| Web Archive copy matches rel_20261024T151746Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261024T214614Z.json | PASS | Oct 24 21:46:25 2026 GMT |
| Web Archive copy matches rel_20261024T214614Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261025T034709Z.json | PASS | Oct 25 03:47:19 2026 GMT |
| Web Archive copy matches rel_20261025T034709Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261025T061649Z.json | PASS | Oct 25 06:16:59 2026 GMT |
| Web Archive copy matches rel_20261025T061649Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261025T101605Z.json | PASS | Oct 25 10:16:14 2026 GMT |
| Web Archive copy matches rel_20261025T101605Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261025T121627Z.json | PASS | Oct 25 12:16:37 2026 GMT |
| Web Archive copy matches rel_20261025T121627Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261025T124612Z.json | PASS | Oct 25 12:46:21 2026 GMT |
| Web Archive copy matches rel_20261025T124612Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261025T131632Z.json | PASS | Oct 25 13:16:43 2026 GMT |
| Web Archive copy matches rel_20261025T131632Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261025T154730Z.json | PASS | Oct 25 15:47:41 2026 GMT |
| Web Archive copy matches rel_20261025T154730Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261025T161650Z.json | PASS | Oct 25 16:17:00 2026 GMT |
| Web Archive copy matches rel_20261025T161650Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261025T164626Z.json | PASS | Oct 25 16:46:34 2026 GMT |
| Web Archive copy matches rel_20261025T164626Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261025T184728Z.json | PASS | Oct 25 18:47:40 2026 GMT |
| Web Archive copy matches rel_20261025T184728Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261025T191719Z.json | PASS | Oct 25 19:17:30 2026 GMT |
| Web Archive copy matches rel_20261025T191719Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261025T194730Z.json | PASS | Oct 25 19:47:43 2026 GMT |
| Web Archive copy matches rel_20261025T194730Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261025T224808Z.json | PASS | Oct 25 22:48:29 2026 GMT |
| Web Archive copy matches rel_20261025T224808Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261025T234725Z.json | PASS | Oct 25 23:47:35 2026 GMT |
| Web Archive copy matches rel_20261025T234725Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261026T014623Z.json | PASS | Oct 26 01:46:34 2026 GMT |
| Web Archive copy matches rel_20261026T014623Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261026T051632Z.json | PASS | Oct 26 05:16:41 2026 GMT |
| Web Archive copy matches rel_20261026T051632Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261026T081635Z.json | PASS | Oct 26 08:16:42 2026 GMT |
| Web Archive copy matches rel_20261026T081635Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261026T084641Z.json | PASS | Oct 26 08:46:49 2026 GMT |
| Web Archive copy matches rel_20261026T084641Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261026T124646Z.json | PASS | Oct 26 12:46:54 2026 GMT |
| Web Archive copy matches rel_20261026T124646Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261026T184612Z.json | PASS | Oct 26 18:46:20 2026 GMT |
| Web Archive copy matches rel_20261026T184612Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261026T224615Z.json | PASS | Oct 26 22:46:24 2026 GMT |
| Web Archive copy matches rel_20261026T224615Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261026T231712Z.json | PASS | Oct 26 23:17:21 2026 GMT |
| Web Archive copy matches rel_20261026T231712Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261027T181619Z.json | PASS | Oct 27 18:16:30 2026 GMT |
| Web Archive copy matches rel_20261027T181619Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261028T004611Z.json | PASS | Oct 28 00:46:21 2026 GMT |
| Web Archive copy matches rel_20261028T004611Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261028T160617Z.json | PASS | Oct 28 16:06:30 2026 GMT |
| Web Archive copy matches rel_20261028T160617Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261028T221638Z.json | PASS | Oct 28 22:16:52 2026 GMT |
| Web Archive copy matches rel_20261028T221638Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261029T041843Z.json | PASS | Oct 29 04:19:05 2026 GMT |
| Web Archive copy matches rel_20261029T041843Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261029T171012Z.json | PASS | Oct 29 17:10:28 2026 GMT |
| Web Archive copy matches rel_20261029T171012Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261029T181614Z.json | PASS | Oct 29 18:16:28 2026 GMT |
| Web Archive copy matches rel_20261029T181614Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261029T211701Z.json | PASS | Oct 29 21:17:15 2026 GMT |
| Web Archive copy matches rel_20261029T211701Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261029T214725Z.json | PASS | Oct 29 21:47:40 2026 GMT |
| Web Archive copy matches rel_20261029T214725Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261029T224735Z.json | PASS | Oct 29 22:47:53 2026 GMT |
| Web Archive copy matches rel_20261029T224735Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261029T231801Z.json | PASS | Oct 29 23:18:18 2026 GMT |
| Web Archive copy matches rel_20261029T231801Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261030T014622Z.json | PASS | Oct 30 01:46:38 2026 GMT |
| Web Archive copy matches rel_20261030T014622Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261030T165902Z.json | PASS | Oct 30 16:59:17 2026 GMT |
| Web Archive copy matches rel_20261030T165902Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261030T231726Z.json | PASS | Oct 30 23:17:43 2026 GMT |
| Web Archive copy matches rel_20261030T231726Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261031T011620Z.json | PASS | Oct 31 01:16:35 2026 GMT |
| Web Archive copy matches rel_20261031T011620Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261031T141234Z.json | PASS | Oct 31 14:12:49 2026 GMT |
| Web Archive copy matches rel_20261031T141234Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261031T201643Z.json | PASS | Oct 31 20:17:01 2026 GMT |
| Web Archive copy matches rel_20261031T201643Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261101T021702Z.json | PASS | Nov  1 02:17:30 2026 GMT |
| Web Archive copy matches rel_20261101T021702Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261101T131800Z.json | PASS | Nov  1 13:18:17 2026 GMT |
| Web Archive copy matches rel_20261101T131800Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261101T164625Z.json | PASS | Nov  1 16:46:43 2026 GMT |
| Web Archive copy matches rel_20261101T164625Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261101T171613Z.json | PASS | Nov  1 17:16:30 2026 GMT |
| Web Archive copy matches rel_20261101T171613Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261101T174616Z.json | PASS | Nov  1 17:46:33 2026 GMT |
| Web Archive copy matches rel_20261101T174616Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261101T194614Z.json | PASS | Nov  1 19:46:30 2026 GMT |
| Web Archive copy matches rel_20261101T194614Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261101T201634Z.json | PASS | Nov  1 20:16:53 2026 GMT |
| Web Archive copy matches rel_20261101T201634Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261101T204627Z.json | PASS | Nov  1 20:46:48 2026 GMT |
| Web Archive copy matches rel_20261101T204627Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261102T004741Z.json | PASS | Nov  2 00:48:01 2026 GMT |
| Web Archive copy matches rel_20261102T004741Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261102T164757Z.json | PASS | Nov  2 16:48:14 2026 GMT |
| Web Archive copy matches rel_20261102T164757Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261103T001618Z.json | PASS | Nov  3 00:16:35 2026 GMT |
| Web Archive copy matches rel_20261103T001618Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261103T181615Z.json | PASS | Nov  3 18:16:33 2026 GMT |
| Web Archive copy matches rel_20261103T181615Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261103T194643Z.json | PASS | Nov  3 19:47:01 2026 GMT |
| Web Archive copy matches rel_20261103T194643Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261104T014726Z.json | PASS | Nov  4 01:47:38 2026 GMT |
| Web Archive copy matches rel_20261104T014726Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261104T094628Z.json | PASS | Nov  4 09:46:37 2026 GMT |
| Web Archive copy matches rel_20261104T094628Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261104T154621Z.json | PASS | Nov  4 15:46:30 2026 GMT |
| Web Archive copy matches rel_20261104T154621Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261104T204614Z.json | PASS | Nov  4 20:46:24 2026 GMT |
| Web Archive copy matches rel_20261104T204614Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261104T214636Z.json | PASS | Nov  4 21:46:46 2026 GMT |
| Web Archive copy matches rel_20261104T214636Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261105T165227Z.json | PASS | Nov  5 16:52:38 2026 GMT |
| Web Archive copy matches rel_20261105T165227Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261105T181616Z.json | PASS | Nov  5 18:16:27 2026 GMT |
| Web Archive copy matches rel_20261105T181616Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261105T211714Z.json | PASS | Nov  5 21:17:25 2026 GMT |
| Web Archive copy matches rel_20261105T211714Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261105T214712Z.json | PASS | Nov  5 21:47:23 2026 GMT |
| Web Archive copy matches rel_20261105T214712Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261105T231640Z.json | PASS | Nov  5 23:16:50 2026 GMT |
| Web Archive copy matches rel_20261105T231640Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261106T001644Z.json | PASS | Nov  6 00:16:53 2026 GMT |
| Web Archive copy matches rel_20261106T001644Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261106T014705Z.json | PASS | Nov  6 01:47:16 2026 GMT |
| Web Archive copy matches rel_20261106T014705Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261106T085844Z.json | PASS | Nov  6 08:58:55 2026 GMT |
| Web Archive copy matches rel_20261106T085844Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261106T131616Z.json | PASS | Nov  6 13:16:28 2026 GMT |
| Web Archive copy matches rel_20261106T131616Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261106T151626Z.json | PASS | Nov  6 15:16:37 2026 GMT |
| Web Archive copy matches rel_20261106T151626Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261106T211717Z.json | PASS | Nov  6 21:17:30 2026 GMT |
| Web Archive copy matches rel_20261106T211717Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261107T011642Z.json | PASS | Nov  7 01:16:53 2026 GMT |
| Web Archive copy matches rel_20261107T011642Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261107T114800Z.json | PASS | Nov  7 11:48:16 2026 GMT |
| Web Archive copy matches rel_20261107T114800Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261107T181629Z.json | PASS | Nov  7 18:16:41 2026 GMT |
| Web Archive copy matches rel_20261107T181629Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261108T001809Z.json | PASS | Nov  8 00:18:21 2026 GMT |
| Web Archive copy matches rel_20261108T001809Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261108T122418Z.json | PASS | Nov  8 12:24:30 2026 GMT |
| Web Archive copy matches rel_20261108T122418Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261108T131612Z.json | PASS | Nov  8 13:16:24 2026 GMT |
| Web Archive copy matches rel_20261108T131612Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261108T134618Z.json | PASS | Nov  8 13:46:30 2026 GMT |
| Web Archive copy matches rel_20261108T134618Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261108T141616Z.json | PASS | Nov  8 14:16:27 2026 GMT |
| Web Archive copy matches rel_20261108T141616Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261108T164613Z.json | PASS | Nov  8 16:46:24 2026 GMT |
| Web Archive copy matches rel_20261108T164613Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261108T171612Z.json | PASS | Nov  8 17:16:23 2026 GMT |
| Web Archive copy matches rel_20261108T171612Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261108T174613Z.json | PASS | Nov  8 17:46:25 2026 GMT |
| Web Archive copy matches rel_20261108T174613Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261108T201612Z.json | PASS | Nov  8 20:16:23 2026 GMT |
| Web Archive copy matches rel_20261108T201612Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261108T204614Z.json | PASS | Nov  8 20:46:25 2026 GMT |
| Web Archive copy matches rel_20261108T204614Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261109T004716Z.json | PASS | Nov  9 00:47:28 2026 GMT |
| Web Archive copy matches rel_20261109T004716Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261109T090517Z.json | PASS | Nov  9 09:05:39 2026 GMT |
| Web Archive copy matches rel_20261109T090517Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261109T094617Z.json | PASS | Nov  9 09:46:28 2026 GMT |
| Web Archive copy matches rel_20261109T094617Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261109T134617Z.json | PASS | Nov  9 13:46:28 2026 GMT |
| Web Archive copy matches rel_20261109T134617Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261109T151630Z.json | PASS | Nov  9 15:16:41 2026 GMT |
| Web Archive copy matches rel_20261109T151630Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261109T211718Z.json | PASS | Nov  9 21:17:28 2026 GMT |
| Web Archive copy matches rel_20261109T211718Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261109T234730Z.json | PASS | Nov  9 23:47:42 2026 GMT |
| Web Archive copy matches rel_20261109T234730Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261110T001732Z.json | PASS | Nov 10 00:17:43 2026 GMT |
| Web Archive copy matches rel_20261110T001732Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261110T181619Z.json | PASS | Nov 10 18:16:32 2026 GMT |
| Web Archive copy matches rel_20261110T181619Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261110T191616Z.json | PASS | Nov 10 19:16:27 2026 GMT |
| Web Archive copy matches rel_20261110T191616Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261110T234728Z.json | PASS | Nov 10 23:47:41 2026 GMT |
| Web Archive copy matches rel_20261110T234728Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261111T093342Z.json | PASS | Nov 11 09:33:55 2026 GMT |
| Web Archive copy matches rel_20261111T093342Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261111T154628Z.json | PASS | Nov 11 15:46:40 2026 GMT |
| Web Archive copy matches rel_20261111T154628Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261111T214741Z.json | PASS | Nov 11 21:47:55 2026 GMT |
| Web Archive copy matches rel_20261111T214741Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261112T061845Z.json | PASS | Nov 12 06:19:04 2026 GMT |
| Web Archive copy matches rel_20261112T061845Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261112T071720Z.json | PASS | Nov 12 07:17:33 2026 GMT |
| Web Archive copy matches rel_20261112T071720Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261112T124807Z.json | PASS | Nov 12 12:48:27 2026 GMT |
| Web Archive copy matches rel_20261112T124807Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261112T144618Z.json | PASS | Nov 12 14:46:31 2026 GMT |
| Web Archive copy matches rel_20261112T144618Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261112T161629Z.json | PASS | Nov 12 16:16:39 2026 GMT |
| Web Archive copy matches rel_20261112T161629Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261112T181649Z.json | PASS | Nov 12 18:17:00 2026 GMT |
| Web Archive copy matches rel_20261112T181649Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261113T080435Z.json | PASS | Nov 13 08:04:48 2026 GMT |
| Web Archive copy matches rel_20261113T080435Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261113T131709Z.json | PASS | Nov 13 13:17:19 2026 GMT |
| Web Archive copy matches rel_20261113T131709Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261113T141619Z.json | PASS | Nov 13 14:16:31 2026 GMT |
| Web Archive copy matches rel_20261113T141619Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261113T154705Z.json | PASS | Nov 13 15:47:16 2026 GMT |
| Web Archive copy matches rel_20261113T154705Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261113T201741Z.json | PASS | Nov 13 20:17:55 2026 GMT |
| Web Archive copy matches rel_20261113T201741Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261114T100214Z.json | PASS | Nov 14 10:02:26 2026 GMT |
| Web Archive copy matches rel_20261114T100214Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261115T095847Z.json | PASS | Nov 15 09:59:00 2026 GMT |
| Web Archive copy matches rel_20261115T095847Z.json | FAIL | not re-downloaded: archive.org stopped serving earlier in this run (ConnectionError); retry later |
| RFC 3161 token verifies against rel_20261115T131808Z.json | PASS | Nov 15 13:18:21 2026 GMT |
| Web Archive copy present for rel_20261115T131808Z.json | FAIL | not captured yet (retried each cycle) |