import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en.json'
import th from './locales/th.json'

const initialLanguage = localStorage.getItem('superx-language') === 'en' ? 'en' : 'th'

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    th: { translation: th },
  },
  lng: initialLanguage,
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

function syncDocumentLanguage(language) {
  document.documentElement.lang = language
  document.title = i18n.t('document.title')
  localStorage.setItem('superx-language', language)
}

i18n.on('languageChanged', syncDocumentLanguage)
syncDocumentLanguage(initialLanguage)

export default i18n