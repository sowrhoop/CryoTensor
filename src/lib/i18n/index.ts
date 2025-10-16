import { writable } from 'svelte/store';

const DEFAULT_LANGUAGE = 'en-US';

type MessageVars = Record<string, string | number | boolean>;

export type Translator = {
	language: string;
	languages: string[];
	t: (key: string, vars?: MessageVars) => string;
};

const formatMessage = (template: string, vars?: MessageVars): string => {
	if (!vars) {
		return template;
	}

	return template.replace(/\{\{\s*(\w+)\s*\}\}/g, (_match, key) =>
		vars[key] !== undefined ? String(vars[key]) : ''
	);
};

const createTranslator = (language: string): Translator => ({
	language,
	languages: [language],
	t: (key: string, vars?: MessageVars) => formatMessage(key, vars)
});

const i18n = writable<Translator>(createTranslator(DEFAULT_LANGUAGE));

export const initI18n = (defaultLocale?: string) => {
	const lang = defaultLocale || DEFAULT_LANGUAGE;
	document.documentElement.setAttribute('lang', lang);
	i18n.set(createTranslator(lang));
};

export const changeLanguage = (lang: string) => {
	document.documentElement.setAttribute('lang', lang);
	i18n.set(createTranslator(lang));
};

export const getLanguages = async () => [
	{
		code: DEFAULT_LANGUAGE,
		title: 'English (US)'
	}
];

export const isLoading = writable(false);

export default i18n;
