/**
 * Long texts left to right: every page in the pseudo-locale `en-XA`
 * (support/long-texts.ts) fits a desktop and a phone.
 */

import { test } from "./support/fixtures";
import { checkLongTexts, LONG_TEXTS_TIMEOUT_MS } from "./support/long-texts";

test.describe.configure({ timeout: LONG_TEXTS_TIMEOUT_MS });

checkLongTexts("ltr");
