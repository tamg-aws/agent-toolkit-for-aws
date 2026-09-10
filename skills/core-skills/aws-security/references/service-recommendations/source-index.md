# Pinned source coverage index

Source: AWS Security Services Best Practices guide, English navigation, commit
`f2b28d7c31c490ad676273307cbdb900c16daed8` (44 pages). This is a recommendation-topic
index, not evidence that a customer's controls work or that every guide claim is current.
The 133 topic contracts below consolidate repeated sections. Navigation, introductory
headings and bibliography are context; comments inside fenced examples are not extra
recommendations. Source placeholders/TODOs convey no verified capability. Sample rule
families map to assessment questions in T086–T101; their executable recipes are not copied.
Suppression/severity-changing examples are disposed under T025/T034/T041/T060 and the
parent prohibition, not passed to an implementer as a workaround.

Use [domain routing](domain-routing.md) to load only selected topics. Each link below
opens a pinned source page; topic links provide trigger, focused evidence, decision and
specific handoff. Source line anchors for individual topics follow the page index.

| Source | Pinned English page | Topic IDs |
|---|---|---|
| P01 | [certificate-services/index.md][P01] | T004–T016 |
| P02 | [detective/index.md][P02] | T001, T003, T042–T046 |
| P03 | [guardduty/index.md][P03] | T001, T003, T017–T026 |
| P04 | [inspector/index.md][P04] | T001, T003, T027–T034 |
| P05 | [macie/index.md][P05] | T001–T003, T035–T041 |
| P06 | [security-agent/index.md][P06] | T002, T125–T133 |
| P07 | [security-hub/index.md][P07] | T001–T003, T047–T054 |
| P08 | [security-hub-cspm/index.md][P08] | T001–T003, T055–T060 |
| P09 | [security-lake/index.md][P09] | T001–T003, T061–T066 |
| P10 | [firewall-overview/index.md][P10] | T067 |
| P11 | [firewall-overview/fundamentals/docs/index.md][P11] | T067, T069, T076–T077 |
| P12 | [firewall-overview/ingress-patterns/docs/index.md][P12] | T067, T072, T076 |
| P13 | [firewall-overview/egress-patterns/docs/index.md][P13] | T067–T068, T070–T071, T073, T083 |
| P14 | [firewall-overview/segmentation/docs/index.md][P14] | T068, T070, T074–T075 |
| P15 | [firewall-overview/cost-and-reference/docs/index.md][P15] | T067, T073, T076 |
| P16 | [waf/index.md][P16] | T115 |
| P17 | [waf/prerequisites/docs/index.md][P17] | T116–T117, T123–T124 |
| P18 | [waf/recommended-http-architecture/docs/index.md][P18] | T115 |
| P19 | [waf/operationalizing/docs/index.md][P19] | T112–T113, T124 |
| P20 | [waf/aws-managed-rules/docs/index.md][P20] | T104–T106, T108 |
| P21 | [waf/custom-rules/docs/index.md][P21] | T110–T112 |
| P22 | [waf/bot-management/docs/index.md][P22] | T106–T107 |
| P23 | [waf/fraud-prevention/docs/index.md][P23] | T108 |
| P24 | [waf/recommended-waf-rule-order/docs/index.md][P24] | T110, T114 |
| P25 | [waf/captcha-and-challenge/docs/index.md][P25] | T109 |
| P26 | [waf/waf-cost/docs/index.md][P26] | T118, T123 |
| P27 | [waf/waf-logging/docs/index.md][P27] | T117–T119 |
| P28 | [waf/monitoring-waf-rules/docs/index.md][P28] | T110, T120 |
| P29 | [waf/using-waf-with-other-services/docs/index.md][P29] | T112, T121–T122 |
| P30 | [waf/additional-references/docs/index.md][P30] |  |
| P31 | [network-firewall/index.md][P31] | T067, T081 |
| P32 | [network-firewall/prerequisites/docs/index.md][P32] | T067–T069, T071, T080, T085, T089 |
| P33 | [network-firewall/deployment-architecture/docs/index.md][P33] | T081–T084 |
| P34 | [network-firewall/firewall-policy-configuration/docs/index.md][P34] | T080, T085–T087, T095 |
| P35 | [network-firewall/customer-managed-rules/docs/index.md][P35] | T088–T090, T100–T101 |
| P36 | [network-firewall/sample-suricata-rules/docs/index.md][P36] | T085–T088, T090–T091, T094 |
| P37 | [network-firewall/aws-managed-rules/docs/index.md][P37] | T092–T093 |
| P38 | [network-firewall/tls-inspection/docs/index.md][P38] | T096–T098 |
| P39 | [network-firewall/logging-and-monitoring/docs/index.md][P39] | T085, T099–T101, T103 |
| P40 | [network-firewall/getting-started-policy/docs/index.md][P40] | T080, T087, T094 |
| P41 | [network-firewall/cost-considerations/docs/index.md][P41] | T102–T103 |
| P42 | [network-firewall/additional-references/docs/index.md][P42] |  |
| P43 | [network-firewall/quick-reference/docs/index.md][P43] | T080–T081, T088, T092, T100 |
| P44 | [dns-firewall/index.md][P44] | T078–T079 |

## Topic source locations

`Pxx:Lnn` identifies the pinned page above and exact source line. Topic links open
trigger/evidence/decision/handoff contracts; repeated sections remain mapped here by line.
Detailed section/example dispositions are external review evidence, not runtime instructions.

| Topic contract | Pinned page and lines |
|---|---|
| [T001](operations.md#t001) | P02:L74,L80; P03:L64,L95,L99,L114,L132,L145; P04:L89,L93; P05:L56,L98; P07:L108,L122; P08:L57,L65; P09:L61,L71,L165 |
| [T002](operations.md#t002) | P05:L52; P07:L88; P08:L49; P09:L58; P06:L167,L184 |
| [T003](operations.md#t003) | P02:L274; P03:L560; P04:L298; P05:L182; P07:L620,L624,L640,L653,L661; P08:L189; P09:L67,L214,L218 |
| [T004](certificates.md#t004) | P01:L56,L67,L77,L112,L222,L272,L276 |
| [T005](certificates.md#t005) | P01:L222,L253 |
| [T006](certificates.md#t006) | P01:L116,L131 |
| [T007](certificates.md#t007) | P01:L179 |
| [T008](certificates.md#t008) | P01:L96 |
| [T009](certificates.md#t009) | P01:L83,L141,L168 |
| [T010](certificates.md#t010) | P01:L104,L264,L268 |
| [T011](certificates.md#t011) | P01:L308,L346,L350,L361,L496 |
| [T012](certificates.md#t012) | P01:L308,L331,L342,L369,L373 |
| [T013](certificates.md#t013) | P01:L327,L346,L384,L394,L464 |
| [T014](certificates.md#t014) | P01:L400,L496 |
| [T015](certificates.md#t015) | P01:L390,L429,L440,L453,L481 |
| [T016](certificates.md#t016) | P01:L282,L288,L292,L296,L302,L490 |
| [T017](detection.md#t017) | P03:L42,L72,L88,L151,L175,L183 |
| [T018](detection.md#t018) | P03:L155 |
| [T019](detection.md#t019) | P03:L198,L206,L216,L231,L242,L253,L279 |
| [T020](detection.md#t020) | P03:L703,L714,L719,L745 |
| [T021](detection.md#t021) | P03:L300,L310,L322,L346 |
| [T022](detection.md#t022) | P03:L332 |
| [T023](detection.md#t023) | P03:L373 |
| [T024](detection.md#t024) | P03:L379,L412,L461 |
| [T025](detection.md#t025) | P03:L361 |
| [T026](detection.md#t026) | P03:L560,L572,L593,L621,L690 |
| [T027](vulnerability-data.md#t027) | P04:L37,L41,L51,L55,L76,L89,L104,L110,L124,L161,L165,L188 |
| [T028](vulnerability-data.md#t028) | P04:L196 |
| [T029](vulnerability-data.md#t029) | P04:L207 |
| [T030](vulnerability-data.md#t030) | P04:L214,L222 |
| [T031](vulnerability-data.md#t031) | P04:L232 |
| [T032](vulnerability-data.md#t032) | P04:L247 |
| [T033](vulnerability-data.md#t033) | P04:L276,L291 |
| [T034](vulnerability-data.md#t034) | P04:L285,L298,L315 |
| [T035](vulnerability-data.md#t035) | P05:L31,L39,L56,L66,L70,L84,L98,L122 |
| [T036](vulnerability-data.md#t036) | P05:L60 |
| [T037](vulnerability-data.md#t037) | P05:L105,L109 |
| [T038](vulnerability-data.md#t038) | P05:L135 |
| [T039](vulnerability-data.md#t039) | P05:L163 |
| [T040](vulnerability-data.md#t040) | P05:L146 |
| [T041](vulnerability-data.md#t041) | P05:L178 |
| [T042](posture-investigation.md#t042) | P02:L34,L38,L42,L52 |
| [T043](posture-investigation.md#t043) | P02:L66,L74,L92,L108,L122 |
| [T044](posture-investigation.md#t044) | P02:L80,L141 |
| [T045](posture-investigation.md#t045) | P02:L132 |
| [T046](posture-investigation.md#t046) | P02:L157,L168,L204,L233,L262 |
| [T047](posture-investigation.md#t047) | P07:L42,L88,L108,L122,L126,L130,L488,L493 |
| [T048](posture-investigation.md#t048) | P07:L497 |
| [T049](posture-investigation.md#t049) | P07:L513 |
| [T050](posture-investigation.md#t050) | P07:L50,L522,L538,L544,L550,L580 |
| [T051](posture-investigation.md#t051) | P07:L558 |
| [T052](posture-investigation.md#t052) | P07:L570,L587,L606 |
| [T053](posture-investigation.md#t053) | P07:L612 |
| [T054](posture-investigation.md#t054) | P07:L624,L640,L653,L661 |
| [T055](posture-investigation.md#t055) | P08:L37,L41,L81,L201 |
| [T056](posture-investigation.md#t056) | P08:L53,L57,L61,L65,L74,L210,L216 |
| [T057](posture-investigation.md#t057) | P08:L98,L117 |
| [T058](posture-investigation.md#t058) | P08:L108,L124 |
| [T059](posture-investigation.md#t059) | P08:L136 |
| [T060](posture-investigation.md#t060) | P08:L146,L175,L182 |
| [T061](security-lake.md#t061) | P09:L7,L11,L54,L58,L61,L64,L71,L77,L103,L136,L140,L148,L157,L165 |
| [T062](security-lake.md#t062) | P09:L74,L226,L229,L232 |
| [T063](security-lake.md#t063) | P09:L95,L100,L172,L176,L179,L182 |
| [T064](security-lake.md#t064) | P09:L187,L191,L200 |
| [T065](security-lake.md#t065) | P09:L211 |
| [T066](security-lake.md#t066) | P09:L168,L218,L223,L235 |
| [T067](network.md#t067) | P15:L1,L8; P13:L1,L8,L30; P11:L3,L17,L24,L34; P12:L1,L8,L15; P10:L1,L3; P31:L30,L36,L40; P32:L45 |
| [T068](network.md#t068) | P13:L38; P14:L18; P32:L55 |
| [T069](network.md#t069) | P11:L24; P32:L59 |
| [T070](network.md#t070) | P13:L16,L20,L34; P14:L59 |
| [T071](network.md#t071) | P13:L42,L49; P32:L49 |
| [T072](network.md#t072) | P12:L15,L32,L50,L58,L70 |
| [T073](network.md#t073) | P15:L26; P13:L62 |
| [T074](network.md#t074) | P14:L1,L8,L26,L41,L51 |
| [T075](network.md#t075) | P14:L65 |
| [T076](network.md#t076) | P15:L51; P11:L46; P12:L82 |
| [T077](network.md#t077) | P11:L55 |
| [T078](network.md#t078) | P44:L3,L8,L26,L34,L53 |
| [T079](network.md#t079) | P44:L43,L64,L73,L84,L92 |
| [T080](network-firewall.md#t080) | P34:L1,L8,L18,L107; P40:L30,L34; P32:L7,L19,L69,L88; P43:L17 |
| [T081](network-firewall.md#t081) | P33:L1,L10,L14,L30,L58; P31:L5; P43:L5 |
| [T082](network-firewall.md#t082) | P33:L71,L75,L93,L117 |
| [T083](network-firewall.md#t083) | P13:L91; P33:L132,L139,L154,L166,L172 |
| [T084](network-firewall.md#t084) | P33:L178,L195,L199,L203,L207 |
| [T085](network-firewall.md#t085) | P34:L123; P39:L123,L127,L473,L488; P32:L29; P36:L262 |
| [T086](network-firewall.md#t086) | P34:L18,L30,L41,L49; P36:L274,L278,L289,L293,L309 |
| [T087](network-firewall.md#t087) | P34:L55,L61,L74,L85,L94,L100; P40:L43; P36:L178 |
| [T088](network-firewall.md#t088) | P35:L1,L10,L22,L39,L44,L52,L66,L96,L183; P43:L27; P36:L1,L12,L23,L135 |
| [T089](network-firewall.md#t089) | P35:L107,L114,L141,L177,L231; P32:L79,L98 |
| [T090](network-firewall.md#t090) | P35:L193,L209; P36:L194,L198,L207,L217,L229 |
| [T091](network-firewall.md#t091) | P36:L27,L52,L66,L87,L99,L116,L139,L153,L165,L249,L325 |
| [T092](network-firewall.md#t092) | P37:L1,L8,L15,L27,L45,L59,L63,L75,L98,L142,L151; P43:L37 |
| [T093](network-firewall.md#t093) | P37:L133,L160,L168,L175,L186,L190 |
| [T094](network-firewall.md#t094) | P40:L1,L10,L19,L47,L54,L58,L69,L86,L103,L116,L130,L134,L138,L151,L155,L159; P36:L342 |
| [T095](network-firewall.md#t095) | P34:L107,L130,L142,L155,L179 |
| [T096](network-firewall.md#t096) | P38:L1,L8,L25,L107 |
| [T097](network-firewall.md#t097) | P38:L34,L42,L48,L54,L66,L74,L78 |
| [T098](network-firewall.md#t098) | P38:L82,L90,L99,L107 |
| [T099](network-firewall.md#t099) | P39:L1,L10,L26,L42,L46,L61,L67,L78,L127,L139,L146,L154,L164,L207,L250 |
| [T100](network-firewall.md#t100) | P35:L215; P39:L290,L297,L319,L332,L341,L347,L364,L376,L382,L394,L407,L411,L429,L444,L459,L473,L488,L503; P43:L46 |
| [T101](network-firewall.md#t101) | P35:L254,L260,L271; P39:L532,L546 |
| [T102](network-firewall.md#t102) | P41:L1,L8,L20,L27,L34,L40,L46,L51,L57,L61,L68,L75,L80,L91,L101,L175,L189,L203 |
| [T103](network-firewall.md#t103) | P41:L87,L110,L114,L130,L139,L145,L159,L166; P39:L515,L517,L526 |
| [T104](waf.md#t104) | P20:L1,L7,L32,L36,L52,L65,L83,L106,L120,L128,L143,L155,L167,L181,L193,L231 |
| [T105](waf.md#t105) | P20:L245,L252,L266,L277,L281,L295,L300 |
| [T106](waf.md#t106) | P20:L206; P22:L1,L20,L24,L81,L103 |
| [T107](waf.md#t107) | P22:L5,L218 |
| [T108](waf.md#t108) | P20:L212; P23:L1,L7,L39 |
| [T109](waf.md#t109) | P25:L1,L5,L7,L15,L25,L47,L58,L68,L80,L88 |
| [T110](waf.md#t110) | P21:L1,L7,L11,L15,L23,L362; P28:L264,L275,L420,L492,L542; P24:L95 |
| [T111](waf.md#t111) | P21:L167,L226,L278,L396,L403 |
| [T112](waf.md#t112) | P21:L377,L390; P19:L189; P29:L29 |
| [T113](waf.md#t113) | P19:L7,L33,L72 |
| [T114](waf.md#t114) | P24:L1,L5,L16,L66,L80,L86,L90 |
| [T115](waf.md#t115) | P18:L1,L5,L16,L23,L28,L32,L39,L45,L50,L55,L68,L75,L79,L84,L88,L100,L111; P16:L1,L30,L34 |
| [T116](waf.md#t116) | P17:L4,L6,L16,L29,L43,L53,L64,L70,L88,L105 |
| [T117](waf.md#t117) | P17:L171; P27:L1,L8,L26,L47,L56,L77,L79,L88,L97 |
| [T118](waf.md#t118) | P26:L565; P27:L64 |
| [T119](waf.md#t119) | P27:L111,L112,L132 |
| [T120](waf.md#t120) | P28:L1,L14,L19,L160,L258,L613,L619,L693,L757 |
| [T121](waf.md#t121) | P29:L1,L6,L10,L16,L29 |
| [T122](waf.md#t122) | P29:L38,L44,L52 |
| [T123](waf.md#t123) | P17:L175; P26:L1,L15,L17,L26,L36,L43,L71,L118,L260,L263,L307,L342,L366,L390,L416,L437,L446,L459,L570,L587,L589,L601,L611,L614 |
| [T124](waf.md#t124) | P19:L176,L879; P17:L114,L118,L144,L150 |
| [T125](application-security.md#t125) | P06:L3,L48,L62,L75,L87 |
| [T126](application-security.md#t126) | P06:L131,L205 |
| [T127](application-security.md#t127) | P06:L91,L101,L111,L167,L184 |
| [T128](application-security.md#t128) | P06:L115,L209,L220,L306,L359 |
| [T129](application-security.md#t129) | P06:L158,L238 |
| [T130](application-security.md#t130) | P06:L188,L258,L266,L270 |
| [T131](application-security.md#t131) | P06:L230 |
| [T132](application-security.md#t132) | P06:L154,L315,L322 |
| [T133](application-security.md#t133) | P06:L279,L283,L298,L302 |

[P01]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/certificate-services/index.md
[P02]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/detective/index.md
[P03]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/guardduty/index.md
[P04]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/inspector/index.md
[P05]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/macie/index.md
[P06]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/security-agent/index.md
[P07]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/security-hub/index.md
[P08]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/security-hub-cspm/index.md
[P09]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/security-lake/index.md
[P10]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/firewall-overview/index.md
[P11]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/firewall-overview/fundamentals/docs/index.md
[P12]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/firewall-overview/ingress-patterns/docs/index.md
[P13]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/firewall-overview/egress-patterns/docs/index.md
[P14]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/firewall-overview/segmentation/docs/index.md
[P15]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/firewall-overview/cost-and-reference/docs/index.md
[P16]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/index.md
[P17]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/prerequisites/docs/index.md
[P18]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/recommended-http-architecture/docs/index.md
[P19]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/operationalizing/docs/index.md
[P20]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/aws-managed-rules/docs/index.md
[P21]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/custom-rules/docs/index.md
[P22]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/bot-management/docs/index.md
[P23]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/fraud-prevention/docs/index.md
[P24]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/recommended-waf-rule-order/docs/index.md
[P25]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/captcha-and-challenge/docs/index.md
[P26]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/waf-cost/docs/index.md
[P27]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/waf-logging/docs/index.md
[P28]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/monitoring-waf-rules/docs/index.md
[P29]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/using-waf-with-other-services/docs/index.md
[P30]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/waf/additional-references/docs/index.md
[P31]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/network-firewall/index.md
[P32]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/network-firewall/prerequisites/docs/index.md
[P33]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/network-firewall/deployment-architecture/docs/index.md
[P34]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/network-firewall/firewall-policy-configuration/docs/index.md
[P35]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/network-firewall/customer-managed-rules/docs/index.md
[P36]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/network-firewall/sample-suricata-rules/docs/index.md
[P37]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/network-firewall/aws-managed-rules/docs/index.md
[P38]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/network-firewall/tls-inspection/docs/index.md
[P39]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/network-firewall/logging-and-monitoring/docs/index.md
[P40]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/network-firewall/getting-started-policy/docs/index.md
[P41]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/network-firewall/cost-considerations/docs/index.md
[P42]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/network-firewall/additional-references/docs/index.md
[P43]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/network-firewall/quick-reference/docs/index.md
[P44]: https://github.com/aws/aws-security-services-best-practices/blob/f2b28d7c31c490ad676273307cbdb900c16daed8/docs/en/guides/dns-firewall/index.md
