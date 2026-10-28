# App Store badges

Apple's official "Download on the App Store" badges, downloaded unmodified on 2026-10-28 from Apple's
App Store marketing tools (https://tools.applemediaservices.com/app-store-badges, the black badge):

| File | Apple's file | Language |
| --- | --- | --- |
| `app-store-badge-en.svg` | Download_on_the_App_Store_Badge_US-UK_RGB_blk_4SVG_092917 | English (US) |
| `app-store-badge-es.svg` | Download_on_the_App_Store_Badge_ESMX_RGB_blk_100217 ("Descárgalo en el App Store") | Spanish (Mexico) |

They are Apple's artwork, used under Apple's App Store marketing guidelines
(https://developer.apple.com/app-store/marketing/guidelines/): don't edit, recolor, animate or
crop them; show them at least 40 px tall with clear space of at least a quarter of the badge's
height all around; and only link them to the app's App Store page. The site shows them only once
`appStoreURL` is set in `_src/config.json` (see the README). `_tools/tests` checks the files are
byte-for-byte unchanged.
