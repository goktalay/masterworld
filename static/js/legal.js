// Gizlilik sayfası: "çerez tercihleri" bağlantısı rıza bandını açar (GA kimliği yoksa bant gösterilmez)
import { initAnalytics } from './analytics.js';
import { setLang, t } from './i18n.js';

setLang(document.documentElement.lang).then(() => initAnalytics({ t, privacyHref: '/gizlilik' }));
