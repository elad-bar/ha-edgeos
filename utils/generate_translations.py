import asyncio
import json
import logging
import os
from pathlib import Path
import sys

from flatten_json import flatten, unflatten
import translators as ts

from custom_components.edgeos.common.consts import DOMAIN

DEBUG = str(os.environ.get("DEBUG", False)).lower() == str(True).lower()

log_level = logging.DEBUG if DEBUG else logging.INFO

root = logging.getLogger()
root.setLevel(log_level)

logging.getLogger("urllib3").setLevel(logging.WARNING)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(log_level)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
stream_handler.setFormatter(formatter)
root.addHandler(stream_handler)

_LOGGER = logging.getLogger(__name__)

SOURCE_LANGUAGE = "en"
DESTINATION_LANGUAGES = {
    "en": "en",
    "nb": "no",
    "pt-BR": "pt"
}

TRANSLATION_PROVIDER = "google"
FLAT_SEPARATOR = "."


class TranslationGenerator:
    def __init__(self):
        self._source_translations = self._get_source_translations()

        self._destinations = DESTINATION_LANGUAGES

    async def initialize(self):
        values = flatten(self._source_translations, FLAT_SEPARATOR)
        value_keys = list(values.keys())
        last_key = value_keys[len(value_keys) - 1]

        _LOGGER.info(
            f"Process will translate {len(values)} sentences "
            f"to {len(list(self._destinations.keys()))} languages"
        )

        for lang in self._destinations:
            original_values = values.copy()
            translated_data = self._get_translations(lang)
            translated_values = flatten(translated_data, FLAT_SEPARATOR)

            provider_lang = self._destinations[lang]
            lang_cache = {}

            lang_title = provider_lang.upper()

            for key in original_values:
                english_value = original_values[key]

                if not isinstance(english_value, str):
                    continue

                if key in translated_values:
                    translated_value = translated_values[key]

                    _LOGGER.debug(
                        f"Skip translation to '{lang_title}', "
                        f"translation of '{english_value}' already exists - '{translated_value}'"
                    )

                    continue

                if english_value in lang_cache:
                    translated_value = lang_cache[english_value]

                    _LOGGER.debug(
                        f"Skip translation to '{lang_title}', "
                        f"translation of '{english_value}' available in cache - {translated_value}"
                    )

                elif lang == SOURCE_LANGUAGE:
                    translated_value = english_value

                    _LOGGER.debug(
                        f"Skip translation to '{lang_title}', "
                        f"source and destination languages are the same - {translated_value}"
                    )

                else:
                    original_english_value = english_value

                    sleep_seconds = 10 if last_key == key else 0

                    translated_value = ts.translate_text(
                        english_value,
                        translator=TRANSLATION_PROVIDER,
                        to_language=provider_lang,
                        sleep_seconds=sleep_seconds
                    )

                    lang_cache[english_value] = translated_value

                    _LOGGER.debug(f"Translating '{original_english_value}' to {lang_title}: {translated_value}")

                translated_values[key] = translated_value

            translated_data = unflatten(translated_values, FLAT_SEPARATOR)

            self._save_translations(lang, translated_data)

    @staticmethod
    def _get_source_translations() -> dict:
        current_path = Path(__file__)
        parent_directory = current_path.parents[1]
        file_path = os.path.join(parent_directory, "custom_components", DOMAIN, "strings.json")

        with open(file_path) as f:
            data = json.load(f)

            return data

    @staticmethod
    def _get_translations(lang: str):
        current_path = Path(__file__)
        parent_directory = current_path.parents[1]
        file_path = os.path.join(parent_directory, "custom_components", DOMAIN, "translations", f"{lang}.json")

        if os.path.exists(file_path):
            with open(file_path) as file:
                data = json.load(file)
        else:
            data = {}

        return data

    @staticmethod
    def _save_translations(lang: str, data: dict):
        current_path = Path(__file__)
        parent_directory = current_path.parents[1]
        file_path = os.path.join(parent_directory, "custom_components", DOMAIN, "translations", f"{lang}.json")

        with open(file_path, "w+") as file:
            file.write(json.dumps(data, indent=4))

        _LOGGER.info(f"Translation for {lang.upper()} stored")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()

    instance = TranslationGenerator()

    try:
        loop.create_task(instance.initialize())
        loop.run_forever()

    except KeyboardInterrupt:
        _LOGGER.info("Aborted")

    except Exception as rex:
        _LOGGER.error(f"Error: {rex}")
