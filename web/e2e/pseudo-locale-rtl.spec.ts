/**
 * Long texts right to left: every page in the pseudo-locale `ar-XB`
 * (support/long-texts.ts), laid out as for Hebrew, fits a desktop and a
 * phone.
 */

import { test } from "./support/fixtures";
import { checkLongTexts, LONG_TEXTS_TIMEOUT_MS } from "./support/long-texts";

test.describe.configure({ timeout: LONG_TEXTS_TIMEOUT_MS });

checkLongTexts("rtl");
