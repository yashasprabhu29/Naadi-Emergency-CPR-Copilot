// Facts shown on the public pages. Edit them here in one place.
export const SITE = {
  name: "Naadi",
  nameKannada: "ನಾಡಿ",
  operator: "the Naadi project team",
  // Public contact point: issues on the project's GitHub repository.
  repoUrl: "https://github.com/yashasprabhu29/Naadi-Emergency-CPR-Copilot",
  contactUrl: "https://github.com/yashasprabhu29/Naadi-Emergency-CPR-Copilot/issues",
  legalUpdated: "9 November 2026",
  emergencyNumbers: "108 or 112",
};

export const LANGUAGE_NAMES = {
  "bn-IN": "Bengali",
  "en-IN": "English",
  "gu-IN": "Gujarati",
  "hi-IN": "Hindi",
  "kn-IN": "Kannada",
  "ml-IN": "Malayalam",
  "mr-IN": "Marathi",
  "pa-IN": "Punjabi",
  "ta-IN": "Tamil",
  "te-IN": "Telugu",
};

export function languageName(code) {
  if (!code) return null;
  return LANGUAGE_NAMES[code] || code;
}
