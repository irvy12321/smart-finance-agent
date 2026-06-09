import { useTranslation } from 'react-i18next'
import { useCallback } from 'react'

export function useAppTranslation() {
  const { t, i18n } = useTranslation()

  const changeLanguage = useCallback((lng: string) => {
    i18n.changeLanguage(lng)
  }, [i18n])

  const isChinese = i18n.language === 'zh-CN'
  const isEnglish = i18n.language === 'en'

  return {
    t,
    i18n,
    changeLanguage,
    currentLanguage: i18n.language,
    isChinese,
    isEnglish,
  }
}

export default useAppTranslation
